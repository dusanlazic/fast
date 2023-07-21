// Countdowns

let tickNumber, tickDuration, submitterDelay, tickRemaining, submitterRemaining;

const tickCountdownElement = document.getElementById('tick-countdown');
const submitCountdownElement = document.getElementById('submit-countdown');
const tickClockElement = document.getElementById('tick-clock');

const fetchSyncData = async () => {
  const response = await fetch('/sync');
  const sync = await response.json();

  tickNumber = sync.tick.current;
  tickDuration = sync.tick.duration;
  submitterDelay = sync.submitter.delay;
  tickRemaining = sync.tick.remaining;
  submitterRemaining = sync.submitter.remaining;

  const offset = (tickRemaining % 1) * 1000;  // sync countdowns to whole seconds

  setTimeout(() => {
    tickRemaining = Math.floor(tickRemaining);
    submitterRemaining = Math.floor(submitterRemaining);

    updateCountdown();
    setInterval(updateCountdown, 1000);
  }, offset);
};


const updateCountdown = () => {
  tickCountdownElement.textContent = tickRemaining.toFixed(0);
  submitCountdownElement.textContent = submitterRemaining.toFixed(0);
  tickClockElement.setAttribute('value', (tickDuration - tickRemaining) / tickDuration)

  tickRemaining -= 1;
  submitterRemaining -= 1;

  if (tickRemaining > 0 && tickRemaining <= 1) {
    // Reset values before tick starts
    received = duplicates = queued = 0;
  }

  if (tickRemaining < 0) {
    tickRemaining += tickDuration;
    tickNumber += 1;
    addNotification(`Started tick ${tickNumber}.`);

    for (const key in exploits) {
      exploits[key] = {
        received: 0,
        duplicates: 0,
        targets: new Set()
      }

      if (document.getElementById(`exploit-${key}-received`)) {
        document.getElementById(`exploit-${key}-received`).textContent = exploits[key].received;
        document.getElementById(`exploit-${key}-duplicates`).textContent = exploits[key].duplicates;
        document.getElementById(`exploit-${key}-targets`).textContent = exploits[key].targets.size;
        document.getElementById(`exploit-${key}-icon`).setAttribute('data-icon', 'svg-spinners:ring-resize');
        exploitsReportElement.querySelector(`#exploit-${key}`).style.opacity = 0.7;
      }
    }
  }

  if (submitterRemaining < 0) {
    submitterRemaining += tickDuration;
  }
};

fetchSyncData();

// Live stats

const socket = io.connect('http://' + document.domain + ':' + location.port);

let exploits = {};
let received = duplicates = queued = inQueue = accepted = rejected = 0;

const receivedElement = document.getElementById('received');
const duplicatesElement = document.getElementById('duplicates');
const queuedElement = document.getElementById('queued');
const exploitsElement = document.getElementById('exploits');
const inQueueElement = document.getElementById('in-queue');
const acceptedElement = document.getElementById('accepted');
const rejectedElement = document.getElementById('rejected');
const acceptedDeltaElement = document.getElementById('accepted-delta');
const rejectedDeltaElement = document.getElementById('rejected-delta');

let reports = {}
let charts = {}

const exploitsReportElement = document.getElementById('exploits-report');

socket.on('enqueue_event', function (msg) {
  key = `${msg.player}-${msg.exploit}`;

  received += msg.new + msg.dup;
  duplicates += msg.dup;
  queued += msg.new;
  inQueue += msg.new;
  
  if (key in exploits) {
    exploits[key].received += msg.new + msg.dup;
    exploits[key].duplicates += msg.dup;
    exploits[key].targets.add(msg.target);
  } else {
    exploits[key] = {
      received: msg.new + msg.dup,
      duplicates: msg.dup,
      targets: new Set([msg.target])
    }
  }
  
  receivedElement.textContent = received;
  duplicatesElement.textContent = duplicates;
  queuedElement.textContent = queued;
  inQueueElement.textContent = inQueue;
  exploitsElement.textContent = Object.keys(exploits).length;

  if (document.getElementById(`exploit-${key}-received`)) {
    document.getElementById(`exploit-${key}-received`).textContent = exploits[key].received;
    document.getElementById(`exploit-${key}-duplicates`).textContent = exploits[key].duplicates;
    document.getElementById(`exploit-${key}-targets`).textContent = exploits[key].targets.size;
    document.getElementById(`exploit-${key}-icon`).setAttribute('data-icon', 'ri:checkbox-circle-line');
    exploitsReportElement.querySelector(`#exploit-${key}`).style.opacity = 1;
  }
});

socket.on('submit_complete_event', function (msg) {
  data = msg.data;

  inQueue = data.queued;
  accepted = data.accepted;
  rejected = data.rejected;
  acceptedDelta = data.acceptedDelta;
  rejectedDelta = data.rejectedDelta;

  inQueueElement.textContent = inQueue;
  acceptedElement.textContent = accepted;
  rejectedElement.textContent = rejected;
  acceptedDeltaElement.textContent = signPrefix(acceptedDelta);
  rejectedDeltaElement.textContent = signPrefix(rejectedDelta);

  addNotification(msg.message);
})

socket.on('report_event', function (msg) {
  reports = msg.report;

  let keys = Object.keys(reports);
  keys.sort();

  for (let i = 0; i < keys.length; i++) {
    let key = keys[i];
    let report = reports[key];

    let exploitCardElement = exploitsReportElement.querySelector(`#exploit-${key}`);
    if (exploitCardElement) {
      if (report.data.accepted.slice(1).reduce((x, y) => x + y, 0) === 0) {
        exploitCardElement.remove();
        delete charts[key];
      } else {
        exploitCardElement.style.opacity = 1;
        renderChart(key, report.data);
      }
    } else {
      let reportElement = document.createElement('div');
      reportElement.id = `exploit-${key}`
      reportElement.classList.add('column');
      reportElement.classList.add('is-2');
      reportElement.innerHTML = `
        <div class="card">
          <div class="card-content pl-0 pr-0 pt-4 pb-4">
            <p class="is-size-6 ml-4">
              <span class="has-text-grey">${report.player}/</span><span>${report.exploit}</span>
              <span class="iconify-inline" id="exploit-${key}-icon" data-icon="ri:checkbox-circle-fill">
            </p>
            <div style="height: 70px;">
              <canvas id="canvas-${key}"></canvas>
            </div>
            <div class="pl-4 pr-4 pt-1 is-flex is-justify-content-space-between">            
              <p class="has-text-grey is-size-6">
                <span class="iconify-inline mr-2" data-icon="ri:flag-fill"></span><span id="exploit-${key}-received">0</span>
              </p>
              <p class="has-text-grey is-size-6">
                <span class="iconify-inline mr-2" data-icon="ri:delete-bin-6-fill"></span><span id="exploit-${key}-duplicates">0</span>
              </p>
              <p class="has-text-grey is-size-6">
                <span class="iconify-inline mr-2" data-icon="ri:crosshair-2-line"></span><span id="exploit-${key}-targets">0</span>
              </p>
            </div>
          </div>
        </div>
      `
      exploitsReportElement.appendChild(reportElement);
      renderChart(key, report.data);
    }
  }
})


const renderChart = (exploitKey, data) => {
  let labels = data.ticks.map(num => `Tick ${num}`);

  if (charts.hasOwnProperty(exploitKey)) {
    let chart = charts[exploitKey];
    chart.config.data.datasets[0].data = data.accepted;
    chart.config.data.labels = labels;
    chart.config.options.scales.y.min = Math.floor(Math.min(...data.accepted) * 0.8)
    chart.config.options.scales.y.max = Math.floor(Math.max(...data.accepted) * 1.2)
    chart.update();

    let iconElement = document.getElementById(`exploit-${exploitKey}-icon`);
    if (data.accepted[data.accepted.length - 1] === 0) {
      iconElement.setAttribute('data-icon', 'ri:alert-fill');
    } else {
      iconElement.setAttribute('data-icon', 'ri:checkbox-circle-fill');
    }
  } else {
    const ctx = document.getElementById(`canvas-${exploitKey}`);

    let chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Accepted',
          data: data.accepted,
          borderColor: '#EF233C',
          pointBackgroundColor: '#EF233C',
          pointHoverBackgroundColor: '#EF233C',
          pointHoverRadius: 5,
          pointBorderColor: 'transparent',
        }]
      },
      options: {
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
    });
    
    charts[exploitKey] = chart;
  }
};



function signPrefix(num) {
  return (num >= 0 ? '+' : '') + num;
}


// Notifications

let notificationQueue = [];

const notificationsElement = document.getElementById('notifications');

socket.on('log_event', function (msg) {
  addNotification(msg.message);
});

function addNotification(notification) {
  notificationQueue.unshift(notification);

  if (notificationQueue.length > 3) {
    notificationQueue.pop();
  }

  let newNotif = document.createElement('p');
  newNotif.style.transition = 'opacity 1s';
  notificationsElement.append(newNotif);
  typingEntrance(newNotif, notification)

  setTimeout(() => newNotif.style.opacity = 0, 4000);
  setTimeout(() => newNotif.remove(), 5000);
}

function typingEntrance(dest, text) {
  let i = 0;
  let animated = '';
  let interval = setInterval(function () {
    if (i < text.length) {
      animated += text.charAt(i++);
      dest.innerText = animated;
    } else {
      clearInterval(interval);
    }
  }, 20);
}