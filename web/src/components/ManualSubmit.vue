<script setup>
import { onMounted, ref } from 'vue'
import { Icon } from '@iconify/vue'
import { game } from '@/game.js'
import api from '@/api.js'

let regex
const player = ref('')
const flagsInput = ref('')
const matches = ref([])

const loading = ref(false)
const submissionResponse = ref({})

const updateMatches = () => {
  matches.value = flagsInput.value.match(regex) || []
}

const submitFlags = async (action) => {
  loading.value = true
  const data = await api.submitFlags(
    matches.value,
    action,
    player.value || 'anon',
  )
  submissionResponse.value = data
  loading.value = false
}

onMounted(async () => {
  await game.initialize()
  regex = new RegExp(game.flagFormat, "g")
})
</script>

<template>
  <textarea class="textarea is-small" rows="10" placeholder="Paste text containing one or more flags" v-model="flagsInput"
    @input="flagsInput = $event.target.value; updateMatches()"></textarea>

  <div class="mt-4 mb-5">
    <span class="subtitle has-text-grey is-size-6 has-tooltip-right has-tooltip-arrow has-text-weight-bold"
    :data-tooltip="matches.join('\n') || 'No flags matched'">
      Matched flags:
      <span class="has-tooltip-arrow">
        {{ matches.length }}
      </span>
    </span>
    <span class="is-pulled-right">
      <input class="input is-inline" size="15" placeholder="Player name" v-model="player"/>
      <button class="button ml-2" :disabled="matches.length === 0" @click="submitFlags('enqueue')" :class="{ 'is-loading': loading }">
        Push to queue
      </button>
      <button class="button ml-2" :disabled="matches.length === 0" @click="submitFlags('submit')" :class="{ 'is-loading': loading }">
        Submit {{ matches.length }} flags
        <Icon icon="ri:send-plane-2-fill" class="is-size-5 ml-2" inline="true" />
      </button>
    </span>
  </div>

  <table class="table is-fullwidth is-size-6">
    <progress v-if="loading" class="progress is-loader"></progress>
    <thead>
      <th style="width: 12%">status</th>
      <th style="width: 34%">value</th>
      <th style="width: 54%">response</th>
    </thead>
    <tbody class="has-text-grey-dark">
      <tr v-for="result in submissionResponse">
        <td>
          {{ result.status }}
          <Icon v-if="result.persisted === true" icon="ri:database-2-line" class="is-size-6" inline="true" />
          <Icon v-else icon="ri:delete-bin-6-fill" class="is-size-6" inline="true" />
        </td>
        <td class="has-tooltip-arrow">{{ result.value }}</td>
        <td class="has-tooltip-arrow">{{ result.response }}</td>
      </tr>
    </tbody>
  </table>
</template>
