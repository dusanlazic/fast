import api from '@/api.js'
import { socket } from "@/socket";
import { reactive, computed } from 'vue'

socket.on('tickStart', function(msg) {
  timers.tick.number = msg.current
})

export const timers = reactive({
  tick: {
    number: 0,
    start: 0,
    duration: 0,
    elapsed: 0
  },
  submitter: {
    start: 0,
    delay: 0,
    elapsed: 0
  },
  async initialize() {
    const syncData = await api.getTimersData();

    this.tick.duration = syncData.tick.duration * 1000
    this.tick.elapsed = syncData.tick.elapsed * 1000
    this.submitter.delay = syncData.submitter.delay * 1000

    this.tick.start = performance.now() - this.tick.elapsed
    this.submitter.start = this.tick.start + this.submitter.delay

    if (this.tick.elapsed < this.submitter.delay) {
      this.submitter.start -= this.tick.duration
    }

    this.updateTimers()
  },
  async updateTimers() {
    this.tick.elapsed = (performance.now() - this.tick.start) % this.tick.duration
    this.submitter.elapsed = (performance.now() - this.submitter.start) % this.tick.duration
    
    requestAnimationFrame(() => this.updateTimers())
  },
  tickSecondsRemaining: computed(() =>
    Math.ceil((timers.tick.duration - timers.tick.elapsed) / 1000)
  ),
  submitSecondsRemaining: computed(() =>
    Math.ceil((timers.tick.duration - timers.submitter.elapsed) / 1000)
  )
})