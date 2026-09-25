<template>
  <section class="page" data-module="road-detail">
    <header class="page-head">
      <div>
        <h2>道路设施详情</h2>
        <p class="page-desc">与列表、合计读取同一份道路设施数据，保存修改后立即同步，无需刷新。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="goBack">返回列表</button>
      </div>
    </header>

    <template v-if="row">
      <table class="data-table">
        <tbody>
          <tr v-for="column in columns" :key="column">
            <th>{{ column }}</th>
            <td>{{ row[column] ?? '—' }}</td>
          </tr>
        </tbody>
      </table>

      <form class="filter-bar detail-edit" @submit.prevent="save">
        <label v-for="field in editableFields" :key="field" class="filter-item">
          <span>{{ field }}</span>
          <input v-model="draft[field]" :placeholder="`填写${field}`" />
        </label>
        <button class="btn primary" type="submit">保存修改</button>
      </form>
    </template>
    <p v-else class="empty-state">正在读取道路设施明细…</p>

    <footer class="page-foot">
      <span v-if="message" class="ok-text">{{ message }}</span>
      <span v-if="store.errorMessage" class="error-text">{{ store.errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useRoadStore, type RoadRow } from '@/stores/road'

const columns = ["设施编码", "道路名称", "道路等级", "起止桩号", "路面结构", "管养单位", "建成年份", "设施状态"]
const editableFields = ["道路名称", "道路等级", "起止桩号", "路面结构", "管养单位", "建成年份"]

const route = useRoute()
const router = useRouter()
const store = useRoadStore()

const id = String(route.params.id)
const row = computed(() => store.findById(id))
const draft = reactive<Record<string, string>>({})
const message = ref('')

function syncDraft(entry: RoadRow) {
  for (const field of editableFields) {
    draft[field] = String(entry[field] ?? '')
  }
}

async function save() {
  message.value = ''
  const ok = await store.updateEntry(id, { ...draft })
  if (ok) {
    message.value = '已保存，列表与合计已同步'
  }
}

function goBack() {
  void router.push('/road')
}

onMounted(async () => {
  const entry = await store.fetchDetail(id)
  if (entry) {
    syncDraft(entry)
  }
})
</script>
