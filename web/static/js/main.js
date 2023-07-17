let tickDuration, submitterDelay, tickRemaining, submitterRemaining;

const tickCountdownElement = document.getElementById('tick-countdown')
const submitCountdownElement = document.getElementById('submit-countdown')
const tickClockElement = document.getElementById('tick-clock')

const fetchSyncData = async () => {
  const response = await fetch('/sync');
  const sync = await response.json();

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

  if (tickRemaining < 0) {
    tickRemaining += tickDuration;
  }

  if (submitterRemaining < 0) {
    submitterRemaining += tickDuration;
  }
};

fetchSyncData();

