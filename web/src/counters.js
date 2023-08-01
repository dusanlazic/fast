import api from '@/api.js'
import { socket } from "@/socket";
import { reactive, computed } from 'vue'


socket.on('enqueue', function (msg) {
  counters.increment(msg)
})

socket.on('submitStart', function () {
  counters.store.submitting = true
})

socket.on('submitComplete', function (msg) {
  counters.store.submitting = false
  counters.updateStoreStats(msg)
})

socket.on('tickStart', function() {
  counters.resetTickCounters()
})

export const counters = reactive({
  tick: {
    received: 0,
    duplicates: 0,
    queued: 0,
  },
  store: {
    queued: 0,
    accepted: 0,
    rejected: 0,
    delta: {
      accepted: 0,
      rejected: 0
    },
    submitting: false
  },
  async initialize() {
    const data = await api.getFlagStoreStats()
    this.store = data
  },
  increment(data) {
    this.tick.received += data.new + data.dup
    this.tick.duplicates += data.dup
    this.tick.queued += data.new
    this.store.queued += data.new
  },
  updateStoreStats(data) {
    this.store = data.data
  },
  resetTickCounters() {
    this.tick.received = 0
    this.tick.duplicates = 0
    this.tick.queued = 0
  }
})