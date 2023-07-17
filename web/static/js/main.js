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

    tickNumber--;  // cancel initial increment
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

  if (tickRemaining < 0) {
    tickRemaining += tickDuration;
    tickNumber += 1;
  }

  if (tickRemaining > 0 && tickRemaining <= 1) {
    received = duplicates = queued = 0;
    exploits.clear()

    receivedElement.textContent = received;
    duplicatesElement.textContent = duplicates;
    queuedElement.textContent = queued;
    exploitsElement.textContent = exploits.size;
  }

  if (submitterRemaining < 0) {
    submitterRemaining += tickDuration;
  }
};

fetchSyncData();

// Live stats

const socket = io.connect('http://' + document.domain + ':' + location.port);

let exploits = new Set();
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


socket.on('enqueue_event', function (msg) {
  received += msg.new + msg.dup;
  duplicates += msg.dup;
  queued += msg.new;
  inQueue += msg.new;
  exploits.add(`${msg.player}/${msg.exploit}`)

  receivedElement.textContent = received;
  duplicatesElement.textContent = duplicates;
  queuedElement.textContent = queued;
  inQueueElement.textContent = inQueue;
  exploitsElement.textContent = exploits.size;
});

socket.on('submit_start_event', function (msg) {
  console.log(msg);
});

socket.on('submit_skip_event', function (msg) {
  console.log(msg);
});

socket.on('submit_complete_event', function (msg) {
  data = msg.data;

  oldAccepted = accepted;
  oldRejected = rejected;

  inQueue = data.queued;
  accepted = data.accepted;
  rejected = data.rejected;
  acceptedDelta = accepted - oldAccepted;
  rejectedDelta = rejected - oldRejected;

  inQueueElement.textContent = inQueue;
  acceptedElement.textContent = accepted;
  rejectedElement.textContent = rejected;
  acceptedDeltaElement.textContent = signPrefix(acceptedDelta);
  rejectedDeltaElement.textContent = signPrefix(rejectedDelta);
})


function signPrefix(num) {
  return (num >= 0 ? '+' : '-') + num;
}
