/** 道路设施共享数据源：列表、详情与合计都从这一个 store 读写，
 *  任何修改（编辑管养单位、状态流转）先写回这里，各页面自然同步，
 *  不会再出现详情一个值、列表残留旧值的情况。
 */
import { defineStore } from 'pinia'

import { request } from '@/api/client'

export type RoadRow = Record<string, string | number | null | undefined>

type ListPayload = {
  items?: RoadRow[]
  total?: number
  stats?: Record<string, number>
}

type ActionPayload = {
  ok: boolean
  message: string
  entry?: RoadRow | null
}

const ENDPOINT = '/api/road'

export const useRoadStore = defineStore('road', {
  state: () => ({
    items: [] as RoadRow[],
    total: 0,
    stats: {} as Record<string, number>,
    filters: {} as Record<string, string>,
    errorMessage: '',
  }),
  actions: {
    queryString(): string {
      const params = new URLSearchParams()
      for (const [field, value] of Object.entries(this.filters)) {
        const keyword = String(value ?? '').trim()
        // 空条件不下发：后端只对非空条件过滤，缺字段的记录才能全部回来
        if (keyword) {
          params.set(field, keyword)
        }
      }
      return params.toString()
    },
    upsert(entry: RoadRow) {
      const index = this.items.findIndex((row) => Number(row.id) === Number(entry.id))
      if (index >= 0) {
        this.items.splice(index, 1, entry)
      } else {
        this.items.push(entry)
      }
    },
    findById(id: number | string): RoadRow | undefined {
      return this.items.find((row) => Number(row.id) === Number(id))
    },
    async fetchList() {
      this.errorMessage = ''
      const query = this.queryString()
      try {
        const response = await request(`${ENDPOINT}${query ? `?${query}` : ''}`)
        if (!response.ok) {
          throw new Error('道路设施列表读取失败')
        }
        const payload = (await response.json()) as ListPayload
        this.items = payload.items ?? []
        this.total = payload.total ?? this.items.length
        // 合计与列表来自后端同一次过滤结果
        this.stats = payload.stats ?? {}
      } catch (error) {
        this.errorMessage = error instanceof Error ? error.message : '道路设施列表读取失败'
      }
    },
    async fetchDetail(id: number | string): Promise<RoadRow | undefined> {
      this.errorMessage = ''
      try {
        const response = await request(`${ENDPOINT}/${id}`)
        if (!response.ok) {
          throw new Error(`道路设施 ${id} 不存在或已归档`)
        }
        const entry = (await response.json()) as RoadRow
        this.upsert(entry)
        return entry
      } catch (error) {
        this.errorMessage = error instanceof Error ? error.message : '道路设施明细读取失败'
        return undefined
      }
    },
    async updateEntry(id: number | string, values: Record<string, string>): Promise<boolean> {
      this.errorMessage = ''
      try {
        const response = await request(`${ENDPOINT}/${id}`, {
          method: 'PUT',
          body: JSON.stringify({ values }),
        })
        const payload = (await response.json()) as ActionPayload
        if (!response.ok || !payload.ok || !payload.entry) {
          throw new Error(payload.message || '道路设施保存失败')
        }
        // 保存结果直接写回共享数据，回到列表无需刷新即是新值
        this.upsert(payload.entry)
        return true
      } catch (error) {
        this.errorMessage = error instanceof Error ? error.message : '道路设施保存失败'
        return false
      }
    },
    async runAction(id: number | string, action: string): Promise<boolean> {
      this.errorMessage = ''
      try {
        const response = await request(`${ENDPOINT}/${id}/actions`, {
          method: 'POST',
          body: JSON.stringify({ action }),
        })
        const payload = (await response.json()) as ActionPayload
        if (!response.ok || !payload.ok) {
          throw new Error(payload.message || '道路设施动作未生效，请稍后重试')
        }
        // 状态流转会影响合计口径，流转后整体重取一次，保证列表与合计同步
        await this.fetchList()
        return true
      } catch (error) {
        this.errorMessage = error instanceof Error ? error.message : '道路设施操作失败'
        return false
      }
    },
    resetFilters() {
      this.filters = {}
    },
  },
})
