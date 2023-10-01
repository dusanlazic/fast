import api from '@/api.js'
import { socket } from "@/socket";
import { reactive } from 'vue'


socket.on('enqueue', function (msg) {
  counters.increment(msg)
})

socket.on('enqueue_fallback', function (msg) {
  counters.increment_fallback(msg)
})

socket.on('submitStart', function (msg) {
  counters.store.submitting = msg.data.count
})

socket.on('submitComplete', function (msg) {
  counters.store.submitting = 0
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
    exploits: new Set()
  },
  store: {
    queued: 0,
    accepted: 0,
    rejected: 0,
    delta: {
      accepted: 0,
      rejected: 0
    },
    submitting: 0
  },
  async initialize() {
    const data = await api.getFlagStoreStats()
    this.store = data
  },
  increment(data) {
    this.tick.exploits.add(`${data.player}/${data.exploit}`)
    this.tick.received += data.new + data.dup
    this.tick.duplicates += data.dup
    this.tick.queued += data.new
    this.store.queued += data.new
  },
  increment_fallback(data) {
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
    this.tick.exploits.clear()
  }
})