/**
 * 道路设施统一数据源：列表、合计、详情、修改都经此 store 访问后端同一份数据。
 * 关键约定：任何写操作（动作、修改）成功后都让相关缓存失效并重载，
 * 因此列表上不会残留旧值，关掉页面重开也是从同一份后端数据重新拉取。
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

import { request } from '@/api/client'

const ENDPOINT = '/api/road'

export type RoadRow = Record<string, string | number | null>
export type RoadStats = Record<string, number>
export type RoadFilters = Record<string, string>

interface ListPayload {
  items: RoadRow[]
  total: number
  stats: RoadStats | null
}

interface ActionPayload {
  ok: boolean
  message: string
  entry: RoadRow | null
}

/** 合计卡片的展示顺序与后端统计键一一对应。 */
export const STAT_KEYS = ['在养道路', '重点观测道路', '管养里程']
export const STAT_UNITS: Record<string, string> = { 管养里程: 'km' }

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error('道路设施列表读取失败')
  }
  return (await response.json()) as T
}

export const useRoadStore = defineStore('road', () => {
  const rows = ref<RoadRow[]>([])
  const total = ref(0)
  const stats = ref<RoadStats>({})
  const filters = ref<RoadFilters>({})
  const detailCache = ref<Map<number, RoadRow>>(new Map())

  function buildQuery(next: RoadFilters): string {
    // 只提交非空条件，清空后就是无条件查询，缺字段记录也会被带出来
    const params = new URLSearchParams()
    for (const [key, value] of Object.entries(next)) {
      const text = value?.trim() ?? ''
      if (text) {
        params.set(key, text)
      }
    }
    const query = params.toString()
    return query ? `?${query}` : ''
  }

  async function loadList(next?: RoadFilters): Promise<void> {
    if (next !== undefined) {
      filters.value = { ...next }
    }
    const response = await request(`${ENDPOINT}${buildQuery(filters.value)}`)
    const payload = await readJson<ListPayload>(response)
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    stats.value = payload.stats ?? {}
    // 列表里的最新值回写详情缓存，保证点进详情时看到的是同一份数据
    for (const row of rows.value) {
      detailCache.value.set(Number(row.id), row)
    }
  }

  async function loadDetail(id: number, force = false): Promise<RoadRow> {
    if (!force && detailCache.value.has(id)) {
      return detailCache.value.get(id) as RoadRow
    }
    const response = await request(`${ENDPOINT}/${id}`)
    if (!response.ok) {
      throw new Error('道路设施详情读取失败')
    }
    const entry = (await response.json()) as RoadRow
    detailCache.value.set(id, entry)
    return entry
  }

  function invalidateDetail(id: number): void {
    detailCache.value.delete(id)
  }

  /** 修改字段（如管养单位）：成功后更新详情缓存，列表由页面重新拉取。 */
  async function saveDetail(id: number, values: RoadRow): Promise<RoadRow> {
    const response = await request(`${ENDPOINT}/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ values }),
    })
    if (!response.ok) {
      throw new Error('道路设施信息未保存，请稍后重试')
    }
    const result = (await response.json()) as ActionPayload
    if (!result.ok || !result.entry) {
      throw new Error(result.message || '道路设施信息未保存')
    }
    detailCache.value.set(id, result.entry)
    return result.entry
  }

  /** 状态动作：成功后以返回的最新记录回写缓存，列表随之重载。 */
  async function applyAction(id: number, action: string): Promise<RoadRow> {
    const response = await request(`${ENDPOINT}/${id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    if (!response.ok) {
      throw new Error('道路设施动作未生效，请稍后重试')
    }
    const result = (await response.json()) as ActionPayload
    if (!result.ok || !result.entry) {
      throw new Error(result.message || '道路设施操作失败')
    }
    detailCache.value.set(id, result.entry)
    return result.entry
  }

  function resetFilters(): Promise<void> {
    filters.value = {}
    return loadList()
  }

  return {
    rows,
    total,
    stats,
    filters,
    loadList,
    loadDetail,
    invalidateDetail,
    saveDetail,
    applyAction,
    resetFilters,
  }
})
