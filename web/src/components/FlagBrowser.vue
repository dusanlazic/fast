<script setup>
import { Icon } from '@iconify/vue'
import { reactive, ref } from 'vue';
import api from '@/api.js'

const query = ref("")
const page = ref(1)
const show = ref(10)
const sort = []
const results = reactive({
  metadata: {
    paging: {
      current: 0,
      hasNext: false,
      hasPrev: false,
      last: 0
    },
    results: {
      executionTime: 0,
      fetched: 0,
      total: 0
    }
  },
  results: []
})

const searchFlags = async () => {
  const data = await api.searchFlags(
    parseInt(page.value), 
    parseInt(show.value), 
    sort, 
    query.value
  )
  Object.assign(results, data)
}

const nextPage = () => {
  page.value = parseInt(page.value) + 1
  searchFlags()
}

const prevPage = () => {
  page.value = parseInt(page.value) - 1
  searchFlags()
}

const truncateEnd = (text, stop, clamp) => {
  return text.slice(0, stop) + (stop < text.length ? clamp || '...' : '')
}

const truncateStart = (text, stop, clamp) => {
  return (text.length > stop ? (clamp || '...') : '') + text.slice(-stop);
}
</script>

<template>
  <div class="field">
    <div class="control is-expanded">
      <input class="input" type="text" placeholder="target == 10.10.4.3 and tick > 94" v-model="query"
        v-on:keyup.enter="searchFlags">
    </div>
  </div>

  <nav class="level">
    <div class="level-left">
      <p class="level-item is-size-7 mr-2 has-text-grey">
        Flags per page
      </p>
      <p class="level-item">
      <div class="select is-small">
        <select v-model="show" @change="searchFlags">
          <option>10</option>
          <option>20</option>
          <option>50</option>
          <option>100</option>
        </select>
      </div>
      </p>
      <p class="level-item is-size-7 ml-5 has-text-grey">
        Showing {{ results.metadata.results.fetched }} out of&nbsp;<strong>{{ results.metadata.results.total
        }}</strong>&nbsp;results ({{ results.metadata.results.executionTime.toFixed(3) }}s)
      </p>
    </div>

    <div class="level-right">
      <p class="level-item mr-1">
        <button class="button is-small is-outlined pl-1" aria-label="Prev" :disabled="!results.metadata.paging.hasPrev" @click="prevPage">
          <Icon icon="ri:arrow-left-s-fill" class="is-size-4" inline="true" />
          Prev
        </button>
      </p>
      <p class="level-item">
        <input class="input is-small has-text-centered" type="text" v-model="page" size="2" v-on:keyup.enter="searchFlags">
      </p>
      <p class="level-item is-size-7">
        <span>out of <strong>{{ results.metadata.paging.last }}</strong> pages</span>
      </p>
      <p class="level-item">
        <button class="button is-small is-outlined pr-1" aria-label="Next" :disabled="!results.metadata.paging.hasNext" @click="nextPage">
          Next
          <Icon icon="ri:arrow-right-s-fill" class="is-size-4" inline="true" />
        </button>
      </p>
    </div>
  </nav>

  <table class="table is-fullwidth is-hoverable is-scrollable is-size-6">
    <thead>
      <tr>
        <th style="width: 5%;">tick</th>
        <th style="width: 10%;">timestamp</th>
        <th style="width: 12%;">player</th>
        <th style="width: 14%;">exploit</th>
        <th style="width: 13%;">target</th>
        <th style="width: 10%;">status</th>
        <th style="width: 20%;">value</th>
        <th style="width: 20%;">response</th>
      </tr>
    </thead>
    <tbody class="has-text-grey-dark">
      <tr v-for="result in results.results">
        <td>{{ result.tick }}</td>
        <td>{{ result.timestamp.split(" ")[1].split(".")[0] }}</td>
        <td>{{ result.player }}</td>
        <td>{{ result.exploit }}</td>
        <td>{{ result.target }}</td>
        <td>{{ result.status }}</td>
        <td class="has-tooltip-arrow" :data-tooltip="result.value">{{ truncateEnd(result.value, 18, '...') }}</td>
        <td class="has-tooltip-arrow" :data-tooltip="result.response">{{ truncateStart(result.response, 18, '...') }}</td>
      </tr>
    </tbody>
  </table>
</template>

<style>
.input {
  box-shadow: none !important;
  border: 1px solid #dbdbdb;
  border-radius: 0px !important;
}

.table {
  table-layout: fixed;
  width: 100%;
}
</style>