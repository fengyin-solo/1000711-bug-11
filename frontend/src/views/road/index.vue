<template>
  <section class="page" data-module="road">
    <header class="page-head">
      <div>
        <h2>道路设施管理</h2>
        <p class="page-desc">维护道路设施，围绕设施编码、道路名称、道路等级、起止桩号做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记道路设施</button>
        <button class="btn" type="button" @click="exportRows">导出道路设施清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="key in statKeys" :key="key" class="stat-card">
        <span class="stat-label">{{ key }}</span>
        <strong class="stat-value">
          {{ roadStore.stats[key] ?? 0 }}<small v-if="statUnits[key]">{{ statUnits[key] }}</small>
        </strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field.key" class="filter-item">
        <span>{{ field.key }}</span>
        <input
          v-model="roadStore.filters[field.key]"
          :placeholder="field.placeholder ?? `按${field.key}检索`"
        />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in roadStore.rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">
            <RouterLink
              v-if="column === codeColumn"
              class="link"
              :to="`/road/${row.id}`"
            >
              {{ displayText(row[column]) }}
            </RouterLink>
            <template v-else>{{ displayText(row[column]) }}</template>
          </td>
          <td class="row-actions">
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!roadStore.rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无道路设施数据，可先登记道路设施</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ roadStore.total }} 条道路设施记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { STAT_KEYS, STAT_UNITS, useRoadStore, type RoadRow } from '@/stores/road'

const ENDPOINT = '/api/road'
const columns = ["设施编码", "道路名称", "道路等级", "起止桩号", "路面结构", "管养单位", "建成年份", "设施状态"]
const codeColumn = '设施编码'
// 可筛字段沿用前三个既有检索框，并补上路面结构，便于把缺路面结构的记录用“空”筛出来
const filterFields: Array<{ key: string; placeholder?: string }> = [
  { key: '设施编码' },
  { key: '道路名称' },
  { key: '道路等级', placeholder: '按道路等级检索，填“空”筛未填写' },
  { key: '路面结构', placeholder: '按路面结构检索，填“空”筛缺失记录' },
]
const actions = ["办理移交", "标记观测", "封闭设施"]
const statKeys = STAT_KEYS
const statUnits = STAT_UNITS

const roadStore = useRoadStore()
const errorMessage = ref('')

function displayText(value: unknown): string {
  // null、undefined 或纯空白统一显示占位线，缺字段记录因此仍占一行而不是消失
  if (value === null || value === undefined || String(value).trim() === '') {
    return '—'
  }
  return String(value)
}

async function reload() {
  errorMessage.value = ''
  try {
    await roadStore.loadList()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '道路设施列表读取失败'
  }
}

async function resetFilters() {
  errorMessage.value = ''
  try {
    // 清空条件后无条件拉全量，缺路面结构的记录同样返回
    await roadStore.resetFilters()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '道路设施列表读取失败'
  }
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '道路设施登记入口尚未接入审批流'
}

async function runAction(action: string, row: RoadRow) {
  errorMessage.value = ''
  try {
    await roadStore.applyAction(Number(row.id), action)
    // 动作生效后用同一份后端数据刷新列表与合计，旧状态不会残留
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '道路设施操作失败'
  }
}

onMounted(reload)
</script>
