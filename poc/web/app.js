'use strict';
const $ = (id) => document.getElementById(id);
const bytes = (text) => new TextEncoder().encode(text).length;
let mode = 'encode';
let running = false;
let config;
let generated;
let decoded;
let currentJob;

function randomKey() {
  return Array.from(crypto.getRandomValues(new Uint8Array(32)), (byte) => byte.toString(16).padStart(2, '0')).join('');
}

async function api(path, options = {}) {
  const response = await fetch(path, {cache: 'no-store', ...options});
  const result = await response.json();
  if (!response.ok) {
    const error = new Error(result.error || 'The demo could not complete this request.');
    error.status = response.status;
    throw error;
  }
  return result;
}

function showError(message) {
  $('error').textContent = message;
  $('error').hidden = false;
}

function countInput() {
  const text = mode === 'encode' ? $('message').value : $('cover-input').value;
  const length = bytes(text);
  const limit = mode === 'encode' ? (config?.max_message_bytes || 512) : (config?.max_cover_bytes || 32768);
  $('input-count').textContent = `${length.toLocaleString()} / ${limit.toLocaleString()} bytes`;
  $('input-count').classList.toggle('over-limit', length > limit);
  $('submit').disabled = running || !config || !length || length > limit;
}

function renderResult() {
  const result = mode === 'encode' ? generated?.result : decoded;
  $('output').hidden = !result;
  $('empty-state').hidden = !!result;
  $('result-meta').hidden = !result;
  $('copy').disabled = !result || running;
  $('success').hidden = !result;
  $('recover-generated').hidden = mode !== 'encode';
  $('output').value = result?.text || '';
  $('result-meta').replaceChildren();
  if (!result) return;
  for (const text of [`${result.output_bytes.toLocaleString()} bytes`, `${result.seconds}s including verification`, `${result.compression === 'zlib' ? 'DEFLATE' : result.compression} compression`]) {
    const span = document.createElement('span');
    span.textContent = mode === 'decode' ? text.replace(' including verification', '') : text;
    $('result-meta').append(span);
  }
  $('success-title').textContent = mode === 'encode' ? 'Exact recovery verified' : 'Message authenticated and recovered';
  $('success-detail').textContent = mode === 'encode' ? `Recovered message: ${result.recovered}` : 'The complete message passed authentication.';
}

function setMode(next) {
  if (running) return;
  mode = next;
  const encode = mode === 'encode';
  for (const name of ['encode', 'decode']) {
    $(`${name}-tab`).setAttribute('aria-selected', String(name === mode));
    $(`${name}-tab`).tabIndex = name === mode ? 0 : -1;
  }
  $('demo-panel').setAttribute('aria-labelledby', `${mode}-tab`);
  $('message').hidden = !encode;
  $('cover-input').hidden = encode;
  $('input-label').htmlFor = encode ? 'message' : 'cover-input';
  $('input-label').textContent = encode ? 'Your message' : 'The complete cover text';
  $('input-hint').textContent = encode ? 'A little something you want to keep between the lines.' : 'Keep the opening paragraph, whitespace, and ending unchanged.';
  $('input-note').textContent = encode ? 'Short messages work best.' : 'Use the original key and temperature.';
  $('sample').hidden = !encode;
  $('opening-control').hidden = !encode;
  $('compression-control').hidden = !encode;
  $('output-label').textContent = encode ? 'The cover text' : 'The recovered message';
  $('output').setAttribute('aria-label', encode ? 'Generated cover text' : 'Recovered message');
  $('empty-title').textContent = encode ? 'A message beneath the words.' : 'Back to the original.';
  $('empty-hint').textContent = encode ? 'Your generated prose will appear here.' : 'Your authenticated message will appear here.';
  $('action-note').textContent = encode ? '✓ Every generated cover is checked for exact recovery.' : '✓ Recovered text appears only after authentication.';
  $('submit').textContent = encode ? 'Hide message ↗' : 'Recover message ↗';
  $('advanced').querySelector('.advanced-summary').textContent = encode ? 'Opening paragraph, temperature & key' : 'Temperature & key';
  $('error').hidden = true;
  renderResult();
  countInput();
}

function setRunning(value) {
  running = value;
  document.querySelectorAll('#demo-form input, #demo-form select, #demo-form textarea:not([readonly]), #demo-form button, .tabs button').forEach((element) => {element.disabled = value;});
  $('progress').hidden = !value;
  $('recover-generated').disabled = value;
  countInput();
}

async function checkStatus() {
  try {
    const status = await api('/api/status');
    $('runtime-status').textContent = status.message;
    $('status-dot').classList.toggle('ready', status.ready);
  } catch {
    $('runtime-status').textContent = 'Demo server unavailable';
    $('status-dot').classList.remove('ready');
  }
}

function describeProgress(job) {
  const queued = job.state === 'queued';
  $('progress-icon').classList.toggle('queued', queued);
  $('progress-icon').textContent = queued ? job.queue_position : '';
  $('queue-note').hidden = !queued;
  $('cancel-job').hidden = !queued;
  if (queued) {
    $('progress-phase').textContent = `You're #${job.queue_position} in line`;
    const ahead = `${job.jobs_ahead} ${job.jobs_ahead === 1 ? 'request' : 'requests'} ahead`;
    let wait = 'Estimating the wait after the first completed run.';
    if (job.estimated_wait_seconds !== null) {
      const seconds = job.estimated_wait_seconds;
      wait = seconds < 10 ? 'Estimated start: shortly.' : seconds < 60 ? 'Estimated start: less than a minute.' :
        `Estimated start: about ${Math.ceil(seconds / 60)} ${seconds <= 60 ? 'minute' : 'minutes'}.`;
    }
    $('progress-detail').textContent = `${ahead} · ${wait}`;
    return;
  }
  $('progress-phase').textContent = job.phase;
  const progress = job.progress || {};
  if (progress.source_tokens) {
    $('progress-detail').textContent = `Source tokens: ${progress.source_tokens} of ${progress.total_source_tokens}.`;
  } else if (progress.tokens) {
    $('progress-detail').textContent = `${progress.tokens.toLocaleString()} tokens processed${progress.target_bits ? ` · ${Math.min(100, Math.floor(100 * progress.bits / progress.target_bits))}% of payload carried` : ''}.`;
  } else {
    $('progress-detail').textContent = job.taking_longer ? 'This run is taking longer than usual. Your place is safe; keep this tab open.' :
      'Local inference can take a few minutes. Keep this tab open.';
  }
}

$('demo-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (running || !config) return;
  $('error').hidden = true;
  $('success').hidden = true;
  // A new attempt must never display an older result as its output.
  if (mode === 'encode') generated = undefined;
  else decoded = undefined;
  renderResult();
  const request = {action: mode, text: mode === 'encode' ? $('message').value : $('cover-input').value,
    opening: $('opening').value, temperature: $('temperature').value,
    compression: $('compression').value, key: $('key').value};
  setRunning(true);
  describeProgress({phase: 'Preparing model'});
  const started = Date.now();
  $('elapsed').textContent = '0:00';
  const timer = setInterval(() => {
    const seconds = Math.floor((Date.now() - started) / 1000);
    $('elapsed').textContent = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
  }, 1000);
  try {
    const {id} = await api('/api/jobs', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(request)});
    currentJob = id;
    let connectionFailures = 0;
    while (true) {
      let job;
      try {
        job = await api(`/api/jobs/${encodeURIComponent(id)}`);
        connectionFailures = 0;
      } catch (error) {
        if (error.status && error.status < 500) throw error;
        connectionFailures += 1;
        $('progress-phase').textContent = 'Reconnecting to your request';
        $('progress-detail').textContent = 'Your request has not been resubmitted. We’ll keep checking for its result.';
        await new Promise((resolve) => setTimeout(resolve, Math.min(15000, 2000 * connectionFailures)));
        continue;
      }
      if (job.state === 'cancelled') break;
      if (job.state === 'failed') throw new Error(job.error);
      if (job.state === 'complete') {
        if (mode === 'encode') generated = {result: job.result, request};
        else decoded = job.result;
        break;
      }
      describeProgress(job);
      await new Promise((resolve) => setTimeout(resolve, job.state === 'queued' ? 3000 : 1000));
    }
  } catch (error) {
    showError(error.message);
  } finally {
    clearInterval(timer);
    currentJob = undefined;
    $('cancel-job').hidden = true;
    setRunning(false);
    renderResult();
    checkStatus();
  }
});

$('cancel-job').addEventListener('click', async () => {
  if (!currentJob) return;
  $('cancel-job').disabled = true;
  try {
    await api(`/api/jobs/${encodeURIComponent(currentJob)}/cancel`, {method: 'POST',
      headers: {'Content-Type': 'application/json'}, body: '{}'});
    $('progress-phase').textContent = 'Removed from the queue';
    $('cancel-job').hidden = true;
  } catch (error) {showError(error.message);}
  finally {$('cancel-job').disabled = false;}
});

$('encode-tab').addEventListener('click', () => setMode('encode'));
$('decode-tab').addEventListener('click', () => setMode('decode'));
document.querySelector('.tabs').addEventListener('keydown', (event) => {
  if (running || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  setMode(event.key === 'Home' ? 'encode' : event.key === 'End' ? 'decode' : mode === 'encode' ? 'decode' : 'encode');
  $(`${mode}-tab`).focus();
});
$('message').addEventListener('input', countInput);
$('cover-input').addEventListener('input', countInput);
$('sample').addEventListener('click', () => {$('message').value = 'The key is 12345'; countInput();});
$('new-key').addEventListener('click', () => {$('key').value = randomKey();});
$('reset-opening').addEventListener('click', () => {if (config) $('opening').value = config.opening;});
$('compression').addEventListener('change', () => {
  $('compression-note').textContent = {standard: 'Chooses the smaller of raw bytes and DEFLATE.', raw: 'Skips compression before encryption.', llm: 'Uses the local model on the original message. Recovery also needs this model.'}[$('compression').value];
});
$('recover-generated').addEventListener('click', () => {
  if (!generated || running) return;
  $('cover-input').value = generated.result.text;
  $('key').value = generated.request.key;
  $('temperature').value = generated.request.temperature;
  setMode('decode');
  $('cover-input').focus();
});
$('copy').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText($('output').value);
    $('copy').textContent = 'Copied';
    setTimeout(() => {$('copy').textContent = 'Copy text';}, 1800);
  } catch {
    $('output').focus();
    $('output').select();
    showError('Copy was unavailable. The text is selected so you can copy it manually.');
  }
});

async function initialize() {
  $('key').value = randomKey();
  try {
    config = await api('/api/config');
    $('opening').value = config.opening;
    $('temperature').value = config.temperature;
    countInput();
    checkStatus();
  } catch (error) {showError(error.message);}
}
initialize();
