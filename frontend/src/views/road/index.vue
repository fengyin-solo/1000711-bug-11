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
      <article v-for="item in statCards" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="store.filters[field]" :placeholder="`按${field}检索`" />
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
        <tr v-for="row in store.items" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td class="row-actions">
            <button class="link" type="button" @click="openDetail(row)">详情</button>
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
        <tr v-if="!store.items.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无道路设施数据，可先登记道路设施</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ store.total }} 条道路设施记录</span>
      <span v-if="store.errorMessage" class="error-text">{{ store.errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { useRoadStore, type RoadRow } from '@/stores/road'

const ENDPOINT = '/api/road'
const columns = ["设施编码", "道路名称", "道路等级", "起止桩号", "路面结构", "管养单位", "建成年份", "设施状态"]
const actions = ["办理移交", "标记观测", "封闭设施"]
const filterFields = columns.slice(0, 3)

const store = useRoadStore()
const router = useRouter()

// 合计面板直接渲染后端随列表一起返回的统计，和列表是同一次过滤的结果
const statCards = computed(() =>
  Object.entries(store.stats).map(([label, value]) => ({ label, value })),
)

function reload() {
  void store.fetchList()
}

function resetFilters() {
  store.resetFilters()
  void store.fetchList()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  store.errorMessage = '道路设施登记入口尚未接入审批流'
}

function openDetail(row: RoadRow) {
  void router.push(`/road/${row.id}`)
}

async function runAction(action: string, row: RoadRow) {
  await store.runAction(Number(row.id), action)
}

onMounted(() => {
  void store.fetchList()
})
</script>
