<script setup>
import api from '@/api.js'
import { socket } from "@/socket";
import { Icon } from '@iconify/vue';
import { reactive, computed } from 'vue';
import { Line } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip } from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip)

socket.on('analyticsUpdate', function (data) {
  state.update(data)
})

socket.on('vulnerabilityReported', function (data) {
  const exploitId = `${data.player}-${data.exploit}`
  if (!(exploitId in state.exploits)) {
    return
  }

  const exploit = state.exploits[exploitId]
  exploit.currentTick.vuln = true
})

socket.on('enqueue', function (data) {
  const exploitId = `${data.player}-${data.exploit}`
  if (!(exploitId in state.exploits)) {
    return
  }

  const exploit = state.exploits[exploitId]
  exploit.currentTick.new += data.new
  exploit.currentTick.dup += data.dup
  exploit.currentTick.hits.add(data.target)
  exploit.currentTick.pinged = true
})

socket.on('tickStart', function () {
  state.resetCurrentTick()
})

const state = reactive({
  exploits: {},
  ticks: [],
  initialize: async function () {
    const data = await api.getExploitAnalytics()
    this.exploits = mapExploits(data.exploits)
    this.ticks = mapTicks(data.ticks)
    
    for (const exploitId in this.exploits) {
      const isAccepted = this.exploits[exploitId].pastTicks.accepted[this.exploits[exploitId].pastTicks.accepted.length - 1] > 0

      this.exploits[exploitId].currentTick = {
        'new': 0,
        'dup': 0,
        'hits': new Set(),
        'vuln': false,
        'pinged': null,
        'accepted': isAccepted
      }
    }
  },
  update: async function (data) {
    const updatedExploits = mapExploits(data.exploits, this.exploits);

    for (const exploitId in this.exploits) {
      if (!(exploitId in data.exploits)) {
        delete this.exploits[exploitId];
      }
    }

    this.exploits = { ...this.exploits, ...updatedExploits };
    this.ticks = mapTicks(data.ticks);
  },
  resetCurrentTick: function () {
    for (const exploitId in this.exploits) {
      this.exploits[exploitId].currentTick = {
        'new': 0,
        'dup': 0,
        'hits': new Set(),
        'vuln': false,
        'pinged': false,
        'accepted': null
      }
    }
  }
})

const mapExploits = (newExploits, existingExploits = {}) => Object.fromEntries(
  Object.entries(newExploits).map(([exploitId, exploit]) => {
    const isAccepted = exploit.data.accepted[exploit.data.accepted.length - 1] > 0;

    return [
      exploitId,
      {
        'player': exploit.player,
        'name': exploit.exploit,
        'pastTicks': exploit.data,
        'currentTick': exploitId in existingExploits
          ? {
            ...existingExploits[exploitId].currentTick,
            'accepted': isAccepted
          }
          : {
            'new': 0,
            'dup': 0,
            'hits': [],
            'vuln': false,
            'pinged': true,
            'accepted': isAccepted
          }
      }
    ]
  })
)

const mapTicks = ticks => ticks.map(num => `Tick ${num}`)


function computeDatasets(data) {
  return {
    labels: state.ticks,
    datasets: [{
      label: 'Accepted',
      data: data.accepted,
      borderColor: '#EF233C',
      pointBackgroundColor: '#EF233C',
      pointHoverBackgroundColor: '#EF233C',
      pointHoverRadius: 5,
      pointBorderColor: 'transparent',
    }]
  }
}

function computeOptions(data) {
  return {
    scales: {
      x: {
        display: false,
        grid: {
          display: false
        },
        title: {
          display: false
        }
      },
      y: {
        display: false,
        min: Math.floor(Math.min(...data.accepted) * 0.8),
        max: Math.ceil(Math.max(...data.accepted) * 1.2)
      }
    },
    plugins: {
      legend: {
        display: false
      }
    },
    layout: {
      padding: {
        top: 5,
        bottom: 5,
      }
    },
    elements: {
      point: {
        radius: 0,
        hitRadius: 15
      },
      line: {
        cubicInterpolationMode: 'monotone'
      }
    },
    interaction: {
      mode: 'index'
    },
    maintainAspectRatio: false
  }
}

function getStatusElements(exploit) {
  if (exploit.currentTick.pinged === null) {
    if (exploit.currentTick.accepted === true) {
      return ["ri:check-double-fill", 'Flags accepted']
    }
    if (exploit.currentTick.accepted === false) {
      return ["ri:close-circle-line", 'Exploit seems down']
    }
  }

  if (exploit.currentTick.pinged === false) {
    if (exploit.currentTick.accepted === null) {
      return ["svg-spinners:ring-resize", 'Waiting for flags...']
    }
    if (exploit.currentTick.accepted === false) {
      return ["ri:close-circle-line", 'Exploit seems down']
    }
  }

  if (exploit.currentTick.pinged === true) {
    if (exploit.currentTick.accepted === null) {
      return ["ri:check-line", 'Exploit is up']
    }
    if (exploit.currentTick.accepted === true) {
      return ["ri:check-double-fill", 'Flags accepted']
    }
    if (exploit.currentTick.accepted === false) {
      return ["ri:error-warning-line", 'No flags accepted']
    }
  }
}

function getHitsList(exploit) {
  return Array.from(exploit.currentTick.hits).sort().join('\n');
}

state.initialize()

</script>

<template>
  <div class="columns is-flex is-flex-wrap-wrap">
    <div v-for="(exploit, exploitId) in state.exploits" :key="exploitId" class="column is-2">
      <div class="card">
        <div class="card-content pl-0 pr-0 pt-4 pb-4">
          <p class="is-size-6 ml-4">
            <span class="has-tooltip-arrow" :data-tooltip="getStatusElements(exploit)[1]">
              {{ exploit.name }}
              <Icon :icon="getStatusElements(exploit)[0]" :inline="true" />
            </span>
            <span class="ml-2 has-tooltip-arrow" data-tooltip="Service requires patching">
              <Icon v-if="exploit.currentTick.vuln" icon="ri:bug-fill" :inline="true"/>
            </span>
          </p>
          <div style="height: 70px;">
            <Line :id="exploit.player + '-' + exploit.exploit" :data="computeDatasets(exploit.pastTicks)"
              :options="computeOptions(exploit.pastTicks)" />
          </div>
          <div class="pl-4 pr-4 pt-1 is-flex is-justify-content-space-between">
            <p class="has-text-grey is-size-6">
              <Icon class="mr-2" icon="ri:flag-fill" :inline="true" />{{ exploit.currentTick.new }}
            </p>
            <p class="has-text-grey is-size-6">
              <Icon class="mr-2" icon="ri:delete-bin-6-fill" :inline="true" />{{ exploit.currentTick.dup }}
            </p>
            <p class="has-text-grey is-size-6 has-tooltip-arrow" :data-tooltip="getHitsList(exploit)">
              <Icon class="mr-2" icon="ri:crosshair-2-line" :inline="true" />{{ exploit.currentTick.hits.size }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>