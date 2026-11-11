// Countdown timer.
// Shows the days, hours, minutes and seconds left until the date in the
// #countdown element's data-target attribute, updating once a second.
// When the date has passed, the countdown is replaced by a message.

const SECOND = 1000;
const MINUTE = 60 * SECOND;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

const countdown = document.querySelector('#countdown');
const finishedMessage = document.querySelector('#countdown-finished');
const targetTime = new Date(countdown.dataset.target).getTime();

let timerId;

/** Splits a duration in milliseconds into whole days, hours, minutes and seconds. */
function splitDuration(ms) {
  return {
    days: Math.floor(ms / DAY),
    hours: Math.floor((ms % DAY) / HOUR),
    minutes: Math.floor((ms % HOUR) / MINUTE),
    seconds: Math.floor((ms % MINUTE) / SECOND),
  };
}

/** Writes each value into the element marked with the matching data-unit. */
function renderRemaining(parts) {
  for (const [unit, value] of Object.entries(parts)) {
    countdown.querySelector(`[data-unit="${unit}"]`).textContent = value;
  }
}

function showFinished() {
  clearInterval(timerId);
  countdown.hidden = true;
  finishedMessage.hidden = false;
}

function tick() {
  const remaining = targetTime - Date.now();
  if (remaining <= 0) {
    showFinished();
  } else {
    renderRemaining(splitDuration(remaining));
  }
}

function start() {
  if (Number.isNaN(targetTime)) {
    console.error(`Invalid countdown date: "${countdown.dataset.target}"`);
    return;
  }
  // Start the timer first so that tick() can cancel it if the date has already passed.
  timerId = setInterval(tick, SECOND);
  tick();
}

start();
