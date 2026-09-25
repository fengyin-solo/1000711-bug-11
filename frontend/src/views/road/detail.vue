<template>
  <section class="page" data-module="road-detail">
    <header class="page-head">
      <div>
        <h2>道路设施详情</h2>
        <p class="page-desc">
          此处与列表、合计取同一份道路设施数据；修改管养单位等字段保存后，列表上的旧值会同步替换。
        </p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn ghost" to="/road">返回列表</RouterLink>
      </div>
    </header>

    <div v-if="loading" class="stat-row">
      <article class="stat-card"><span class="stat-label">正在读取道路设施明细…</span></article>
    </div>

    <div v-else-if="!entry" class="stat-row">
      <article class="stat-card">
        <span class="stat-label">道路设施不存在或已归档</span>
      </article>
    </div>

    <template v-else>
      <form class="filter-bar" @submit.prevent="save">
        <label v-for="field in editableFields" :key="field" class="filter-item">
          <span>{{ field }}{{ requiredFields.includes(field) ? ' *' : '' }}</span>
          <input v-model="form[field]" :placeholder="field === '路面结构' ? '可留空，留空表示尚未登记' : `请输入${field}`" />
        </label>
        <button class="btn primary" type="submit" :disabled="saving">保存修改</button>
        <span class="stat-label">设施状态：{{ entry['设施状态'] ?? '—' }}</span>
      </form>

      <table class="data-table">
        <tbody>
          <tr v-for="field in detailFields" :key="field">
            <th>{{ field }}</th>
            <td>{{ displayText(entry[field]) }}</td>
          </tr>
        </tbody>
      </table>

      <div class="page-actions">
        <button
          v-for="action in actions"
          :key="action"
          class="btn"
          type="button"
          :disabled="saving"
          @click="runAction(action)"
        >
          {{ action }}
        </button>
      </div>

      <footer class="page-foot">
        <span>设施编码 {{ entry['设施编码'] }}</span>
        <span v-if="message" :class="saveOk ? 'stat-label' : 'error-text'">{{ message }}</span>
      </footer>
    </template>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import { useRoadStore, type RoadRow } from '@/stores/road'

// 与列表共用同一份字段口径，保证详情看到的道路等级等就是列表上那条
const editableFields = ["设施编码", "道路名称", "道路等级", "起止桩号", "路面结构", "管养单位", "建成年份"]
const requiredFields = ["设施编码", "道路名称", "道路等级"]
const detailFields = [...editableFields, '设施状态']
const actions = ["办理移交", "标记观测", "封闭设施"]

const route = useRoute()
const roadStore = useRoadStore()

const entry = ref<RoadRow | null>(null)
const form = reactive<Record<string, string>>({})
const loading = ref(true)
const saving = ref(false)
const message = ref('')
const saveOk = ref(false)

function displayText(value: unknown): string {
  if (value === null || value === undefined || String(value).trim() === '') {
    return '—'
  }
  return String(value)
}

function fillForm(row: RoadRow) {
  for (const field of editableFields) {
    const value = row[field]
    form[field] = value === null || value === undefined ? '' : String(value)
  }
}

async function refresh(force = true) {
  const id = Number(route.params.id)
  if (!Number.isFinite(id)) {
    entry.value = null
    loading.value = false
    return
  }
  loading.value = true
  try {
    // 详情直接向后端取当前这条；写操作后强制重取，避免看到任何旧值
    entry.value = await roadStore.loadDetail(id, force)
    fillForm(entry.value)
  } catch {
    entry.value = null
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!entry.value) {
    return
  }
  saving.value = true
  message.value = ''
  try {
    const values: RoadRow = {}
    for (const field of editableFields) {
      values[field] = form[field]?.trim() ?? ''
    }
    const updated = await roadStore.saveDetail(Number(entry.value.id), values)
    entry.value = updated
    fillForm(updated)
    saveOk.value = true
    message.value = '道路设施信息已更新，列表中的同一条记录已同步'
    // 返回列表时会重新请求，确保管养单位等字段不再残留旧值
    void roadStore.loadList()
  } catch (error) {
    saveOk.value = false
    message.value = error instanceof Error ? error.message : '道路设施信息未保存'
  } finally {
    saving.value = false
  }
}

async function runAction(action: string) {
  if (!entry.value) {
    return
  }
  saving.value = true
  message.value = ''
  try {
    const updated = await roadStore.applyAction(Number(entry.value.id), action)
    entry.value = updated
    fillForm(updated)
    saveOk.value = true
    message.value = `道路设施已${action}`
    void roadStore.loadList()
  } catch (error) {
    saveOk.value = false
    message.value = error instanceof Error ? error.message : '道路设施操作失败'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  void refresh(false)
})
</script>
