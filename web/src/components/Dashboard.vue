<script setup>
import { Icon } from '@iconify/vue'
import { timers } from '@/timers.js'
import { counters } from '@/counters.js'
import Analytics from './Analytics.vue'

timers.initialize()
counters.initialize()

function getExploitsList() {
  return Array.from(counters.tick.exploits).sort().join('\n') || 'No exploits pinged yet';
}

</script>

<template>
  <p class="subtitle is-size-4">
    Current tick
    <Icon icon="ri:timer-line" inline="true" />
    <span class="subtitle has-text-grey-light is-pulled-right">
      <Icon icon="ri:timer-fill" inline="true" class="is-size-4" />
      Next tick in {{ timers.tickSecondsRemaining }}s
    </span>
  </p>
  <div class="columns">
    <div class="column">
      <div class="card">
        <div class="card-content">
          <p class="subtitle">
            <Icon icon="ri:flag-fill" inline="true" />
            Flags received
          </p>
          <p class="title">
            {{ counters.tick.received }}
          </p>
        </div>
      </div>
    </div>
    <div class="column">
      <div class="card">
        <div class="card-content">
          <p class="subtitle">
            <Icon icon="ri:delete-bin-6-fill" inline="true" />
            Duplicates
          </p>
          <p class="title">
            {{ counters.tick.duplicates }}
          </p>
        </div>
      </div>
    </div>
    <div class="column">
      <div class="card">
        <div class="card-content">
          <p class="subtitle">
            <Icon icon="ri:database-2-fill" inline="true" />
            Added to queue
          </p>
          <p class="title">
            {{ counters.tick.queued }}
          </p>
        </div>
      </div>
    </div>
    <div class="column">
      <div class="card">
        <div class="card-content">
          <p class="subtitle">
            <Icon icon="ri:sword-fill" inline="true" />
            <span class="has-tooltip-arrow" :data-tooltip="getExploitsList()"> Exploits</span>
          </p>
          <p class="title">
            {{ counters.tick.exploits.size }}
          </p>
        </div>
      </div>
    </div>
  </div>

  <p class="subtitle is-size-4 mt-4">
    Flag store
    <Icon icon="ri:flag-line" inline="true" />
    <span class="subtitle has-text-grey-light is-pulled-right">
      <Icon icon="ri:send-plane-fill" inline="true" class="is-size-4" />
      Next submit in {{ timers.submitSecondsRemaining }}s
    </span>
  </p>
  <div class="columns">
    <div class="column">
      <div class="card">
        <progress v-show="counters.store.submitting" class="progress is-loader"></progress>
        <div class="card-content">
          <p v-if="counters.store.submitting" class="subtitle">
            <Icon icon="ri:send-plane-fill" inline="true" />
            <span> Submitting <span class="has-text-grey-light">{{ counters.store.submitting }}</span></span>
          </p>
          <p v-else class="subtitle">
            <Icon icon="ri:check-line" inline="true" />
            <span> In queue</span>
          </p>
          <p class="title">
            {{ counters.store.queued }}
          </p>
        </div>
      </div>
    </div>
    <div class="column">
      <div class="card">
        <progress v-show="counters.store.submitting" class="progress is-loader"></progress>
        <div class="card-content">
          <p class="subtitle">
            <Icon icon="ri:check-double-line" inline="true" />
            Accepted <span class="has-text-success" v-if="counters.store.delta.accepted > 0">+{{
              counters.store.delta.accepted }}</span>
          </p>
          <p class="title">
            {{ counters.store.accepted }}
          </p>
        </div>
      </div>
    </div>
    <div class="column">
      <div class="card">
        <progress v-show="counters.store.submitting" class="progress is-loader"></progress>
        <div class="card-content">
          <p class="subtitle">
            <Icon icon="ri:close-line" inline="true" />
            Rejected <span class="has-text-grey-light" v-if="counters.store.delta.rejected > 0">+{{
              counters.store.delta.rejected }}</span>
          </p>
          <p class="title">
            {{ counters.store.rejected }}
          </p>
        </div>
      </div>
    </div>
  </div>

  <p class="subtitle is-size-4 mt-4">
    Exploits
    <Icon icon="ri:sword-line" inline="true" />
  </p>

  <Analytics />
</template>

<style>
.card {
  box-shadow: none !important;
  border: 1px solid #dbdbdb;
  border-radius: 0px !important;
}

.card:hover {
  background-color: #eeeeee;
}

.progress.is-loader {
  height: 5px;
  position: absolute;
  margin: 0px !important;
}

.progress.is-loader:indeterminate {
  background-image: linear-gradient(to right, #dbdbdb 30%, transparent 30%);
}

</style>