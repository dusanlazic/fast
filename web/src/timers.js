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
    interval: 0,
    elapsed: 0
  },
  async initialize() {
    const syncData = await api.getTimersData();
    let now = performance.now()

    this.tick.duration = syncData.tick.duration * 1000
    this.tick.elapsed = syncData.tick.elapsed * 1000
    this.tick.start = now - this.tick.elapsed

    this.submitter.interval = syncData.submitter.interval * 1000
    this.submitter.start = now - syncData.submitter.elapsed * 1000

    if (syncData.tick.remaining > syncData.tick.duration) {
      this.updateTimersBeforeStart()
    } else {
      this.updateTimers()
    }
  },
  async updateTimers() {
    let now = performance.now()
    this.tick.elapsed = (now - this.tick.start) % this.tick.duration
    this.submitter.elapsed = (now - this.submitter.start) % this.submitter.interval
    
    requestAnimationFrame(() => this.updateTimers())
  },
  async updateTimersBeforeStart() {
    let now = performance.now()
    this.tick.elapsed = (now - this.tick.start)
    this.submitter.elapsed = (now - this.submitter.start) % this.submitter.interval

    if (this.tick.elapsed < 0) {
      requestAnimationFrame(() => this.updateTimersBeforeStart())
    } else {
      requestAnimationFrame(() => this.updateTimers())
    }
  },
  tickSecondsRemaining: computed(() =>
    Math.ceil((timers.tick.duration - timers.tick.elapsed) / 1000)
  ),
  submitSecondsRemaining: computed(() =>
    Math.ceil((timers.submitter.interval - timers.submitter.elapsed) / 1000)
  )
})