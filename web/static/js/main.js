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
    addNotification(`Started tick ${tickNumber}.`);
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

socket.on('log_event', function (msg) {
  addNotification(msg.message);
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


function signPrefix(num) {
  return (num >= 0 ? '+' : '') + num;
}


// Notifications

let notificationQueue = [];

const notificationsElement = document.getElementById('notifications');

function addNotification(notification) {
  notificationQueue.unshift(notification);

  if (notificationQueue.length > 10) {
    notificationQueue.pop();
  }

  let newNotif = document.createElement('p');
  newNotif.style.transition = 'opacity 1s';
  notificationsElement.prepend(newNotif);
  typingEntrance(newNotif, notification)

  setTimeout(() => newNotif.style.opacity = 0, 4000);
}

function typingEntrance(dest, text) {
  let i = 0;
  let animated = '';
  let interval = setInterval(function() {
    if (i < text.length) {
      animated += text.charAt(i++);
      dest.innerText = animated;
    } else {
      clearInterval(interval);
    }
  }, 20);
}