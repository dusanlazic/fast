<script setup>
import { Icon } from '@iconify/vue'
import { reactive, ref } from 'vue';
import api from '@/api.js'

const query = ref("")
const page = ref(1)
const show = ref(25)
const sort = ref([])

const loading = ref(false)
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
  loading.value = true
  const data = await api.searchFlags(
    parseInt(page.value),
    parseInt(show.value),
    sort.value,
    query.value === '' ? 'tick > 0' : query.value
  )
  Object.assign(results, data)
  loading.value = false
}

const nextPage = () => {
  page.value = parseInt(page.value) + 1
  searchFlags()
}

const prevPage = () => {
  page.value = parseInt(page.value) - 1
  searchFlags()
}

const toggleSort = (event) => {
  const field = event.target.innerText

  const index = sort.value.findIndex(s => s.field === field);
  if (index === -1) {
    sort.value.push({ field, direction: 'desc' })
  } else {
    if (sort.value[index].direction === 'desc') {
      sort.value[index].direction = 'asc'
    } else {
      sort.value.splice(index, 1);
    }
  }

  searchFlags()
}

const clearSort = () => {
  sort.value = []
  searchFlags()
}

const truncateEnd = (text, stop, clamp) => {
  if (!text) return '';
  return text.slice(0, stop) + (stop < text.length ? clamp || '...' : '');
}

const truncateStart = (text, stop, clamp) => {
  if (!text) return '';
  return (text.length > stop ? (clamp || '...') : '') + text.slice(-stop);
}


const getSortIcon = (field) => {
  const index = sort.value.findIndex(s => s.field === field);
  if (index === -1) {
    return ''
  } else if (sort.value[index].direction === 'desc') {
    return 'ri:arrow-down-line'
  } else if (sort.value[index].direction === 'asc') {
    return 'ri:arrow-up-line'
  }
}

</script>

<template>
  <div class="search-controls">
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
            <option>25</option>
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
          <button class="button is-small is-outlined pl-1" aria-label="Prev" :disabled="!results.metadata.paging.hasPrev"
            @click="prevPage">
            <Icon icon="ri:arrow-left-s-fill" class="is-size-4" inline="true" />
            Prev
          </button>
        </p>
        <p class="level-item">
          <input class="input is-small has-text-centered" type="text" v-model="page" size="2"
            v-on:keyup.enter="searchFlags">
        </p>
        <p class="level-item is-size-7">
          <span>out of <strong>{{ results.metadata.paging.last }}</strong> pages</span>
        </p>
        <p class="level-item">
          <button class="button is-small is-outlined pr-1" aria-label="Next" :disabled="!results.metadata.paging.hasNext"
            @click="nextPage">
            Next
            <Icon icon="ri:arrow-right-s-fill" class="is-size-4" inline="true" />
          </button>
        </p>
      </div>
    </nav>

    <progress v-if="loading" class="progress is-loader"></progress>
    <table class="table is-fullwidth is-size-6">
      <thead>
        <th style="width: 7%;">
          <span @click="toggleSort($event)">tick</span>
          <Icon :icon="getSortIcon('tick')" inline="true" />
        </th>
        <th style="width: 11%;">
          <span @click="toggleSort($event)">timestamp</span>
          <Icon :icon="getSortIcon('timestamp')" inline="true" />
        </th>
        <th style="width: 10%;">
          <span @click="toggleSort($event)">player</span>
          <Icon :icon="getSortIcon('player')" inline="true" />
        </th>
        <th style="width: 13%;">
          <span @click="toggleSort($event)">exploit</span>
          <Icon :icon="getSortIcon('exploit')" inline="true" />
        </th>
        <th style="width: 13%;">
          <span @click="toggleSort($event)">target</span>
          <Icon :icon="getSortIcon('target')" inline="true" />
        </th>
        <th style="width: 10%;">
          <span @click="toggleSort($event)">status</span>
          <Icon :icon="getSortIcon('status')" inline="true" />
        </th>
        <th style="width: 20%;">
          <span @click="toggleSort($event)">value</span>
          <Icon :icon="getSortIcon('value')" inline="true" />
        </th>
        <th style="width: 20%;">
          <span @click="toggleSort($event)">response</span>
          <Icon :icon="getSortIcon('response')" inline="true" />
          <span @click="clearSort">
            <Icon icon="ri:delete-back-2-line" class="is-pulled-right mt-1" inline="true" />
          </span>
        </th>
      </thead>
    </table>
  </div>

  <table class="table is-fullwidth is-hoverable is-size-6">
    <col width="7%" />
    <col width="11%" />
    <col width="10%" />
    <col width="13%" />
    <col width="13%" />
    <col width="10%" />
    <col width="20%" />
    <col width="20%" />
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

.table th>span {
  cursor: pointer;
}

.search-controls {
  margin-top: -2rem !important;
  padding-top: 2rem !important;
  position: sticky;
  top: 0px;
  z-index: 1;
  background-color: #f5f5f5;
}
</style>