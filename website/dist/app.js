'use strict';
const $ = (id) => document.getElementById(id);
const github = 'https://github.com/jchook/plaintext-to-plaintext/blob/main/';
let records = [];
let selected;
let message = 'key-message';
let trial = 1;
let replayId = 0;

function chooseExample() {
  replayId += 1;
  selected = records.find((row) => row.message_id === message && row.topic === $('topic').value &&
    row.temperature === $('temperature').value && row.trial === trial);
  $('replay').disabled = !selected;
  $('copy-cover').disabled = true;
  $('recovery').hidden = true;
  $('recovered').hidden = true;
  $('reveal').hidden = false;
  if (!selected) return;
  $('message').textContent = selected.message;
  $('message-bytes').textContent = `${selected.message_bytes} bytes`;
  $('original-size').textContent = `${selected.message_bytes} B`;
  $('packed-size').textContent = `${selected.packed_bytes} B`;
  $('frame-size').textContent = `${selected.frame_bytes} B`;
  $('cover').replaceChildren();
  const placeholder = document.createElement('div');
  placeholder.className = 'cover-placeholder';
  const glyph = document.createElement('span'); glyph.textContent = '¶'; glyph.setAttribute('aria-hidden', 'true');
  const heading = document.createElement('p'); heading.textContent = 'A different way to say the same thing.';
  const hint = document.createElement('small'); hint.textContent = 'Replay an example to reveal its saved cover text.';
  placeholder.append(glyph, heading, hint); $('cover').append(placeholder);
  $('cover-size').textContent = '—';
  $('recording-time').textContent = 'Recorded on a local CPU';
  $('demo-status').textContent = `Recording ${trial} · ${selected.topic_label.toLowerCase()}`;
  $('demo-note').textContent = 'The output and recovery were recorded in our experiments. This page reveals saved results.';
  $('source-link').href = github + selected.artifact_path + '.encode.json';
}

async function replay() {
  if (!selected) return;
  const row = selected;
  const run = ++replayId;
  $('replay').disabled = true;
  $('copy-cover').disabled = true;
  $('recovery').hidden = true;
  $('cover').textContent = '';
  $('demo-status').textContent = 'Replaying the recorded cover…';
  $('demo-note').textContent = 'This is a playback animation. No model is running in your browser or on a server.';
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const step = reduced ? row.cover.length : Math.ceil(row.cover.length / 24);
  for (let end = step; end < row.cover.length; end += step) {
    if (run !== replayId) return;
    $('cover').textContent = row.cover.slice(0, end);
    await new Promise((resolve) => setTimeout(resolve, 22));
  }
  if (run !== replayId) return;
  $('cover').textContent = row.cover;
  $('cover').scrollTop = 0;
  $('cover-size').textContent = `${row.cover_bytes.toLocaleString()} UTF-8 bytes`;
  $('recording-time').textContent = `Original round trip: ${row.seconds}s`;
  $('demo-status').textContent = 'Recorded cover revealed. Now recover the secret.';
  $('demo-note').textContent = `${row.message_bytes} source bytes carried in ${row.cover_bytes.toLocaleString()} cover bytes · Llama 3.2 3B · temperature ${row.temperature}`;
  $('replay').disabled = false;
  $('copy-cover').disabled = false;
  $('recovery').hidden = false;
}

function hardware() {
  const ram = Number($('ram').value);
  const vram = Number($('vram').value);
  const system = $('system').value;
  const unified = system === 'mac';
  $('ram-output').textContent = `${ram} GB`;
  $('vram').disabled = unified;
  $('vram-output').textContent = unified ? 'Shared system memory' : vram ? `${vram} GB` : '0 GB · CPU only';
  const ready = ram >= 8;
  $('recommendation-badge').textContent = ready ? 'VERIFIED MODEL PROFILE' : 'BELOW SUGGESTED MEMORY BUDGET';
  $('model-name').textContent = ready ? 'Llama 3.2 · 3B' : 'No verified low-memory profile yet';
  $('hardware-note').textContent = ready ? 'Start with the verified CPU profile. The suggested 8 GB system RAM budget includes headroom for the app and runtime.' :
    'The verified 3B profile has a suggested 8 GB system RAM budget. Smaller models need codec validation before we can recommend them for this app.';
  $('copy-model').disabled = !ready;
  $('model-command').textContent = ready ? 'ollama pull llama3.2:3b-instruct-q4_K_M' : 'See smaller-model candidates below';
  $('gpu-note').textContent = unified ? 'Apple Silicon uses shared memory; RAM and VRAM are not added together. This runtime has not been validated on macOS.' :
    vram ? `Your ${vram} GB GPU could help a future GPU profile. The current verified profile uses CPU, so VRAM does not change this recommendation.` :
    'GPU memory is optional. The verified profile currently runs on CPU.';
  $('system-note').textContent = {linux: 'The current profile has been tested on Linux. Both servers stop when you exit the launcher.',
    windows: 'Run these commands inside WSL2. Native Windows is not supported by the current Unix-only launcher and file locking.',
    mac: 'These shell commands require Python and Git on macOS. Exact runtime replay on macOS has not yet been validated; check the setup guide first.'}[system];
}

let noticeTimer;
async function copy(text, button) {
  try {
    await navigator.clipboard.writeText(text);
    const original = button.textContent; button.textContent = 'Copied';
    setTimeout(() => {button.textContent = original;}, 1500);
  } catch {
    $('notice').textContent = 'Clipboard access is unavailable. Select the displayed text and copy it manually.';
    $('notice').hidden = false;
    clearTimeout(noticeTimer); noticeTimer = setTimeout(() => {$('notice').hidden = true;}, 6000);
  }
}

document.querySelectorAll('[data-message]').forEach((button) => {
  button.addEventListener('click', () => {
    message = button.dataset.message;
    document.querySelectorAll('[data-message]').forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
    chooseExample();
  });
});
$('topic').addEventListener('change', chooseExample);
$('temperature').addEventListener('change', chooseExample);
$('another').addEventListener('click', () => {trial = trial === 1 ? 2 : 1; chooseExample(); replay();});
$('replay').addEventListener('click', replay);
$('reveal').addEventListener('click', () => {
  if (!selected) return;
  $('recovered').textContent = selected.recovered;
  $('recovered').hidden = false;
  $('reveal').hidden = true;
  $('demo-status').textContent = 'Original message revealed from the saved recovery.';
});
$('copy-cover').addEventListener('click', () => {if (selected) copy(selected.cover, $('copy-cover'));});
['ram', 'vram'].forEach((id) => $(id).addEventListener('input', hardware));
$('system').addEventListener('change', hardware);
$('copy-model').addEventListener('click', () => copy($('model-command').textContent, $('copy-model')));
$('copy-setup').addEventListener('click', () => copy($('setup-commands').textContent, $('copy-setup')));
$('replay').disabled = true;
$('another').disabled = true;
hardware();
fetch('./examples.json').then((response) => {
  if (!response.ok) throw new Error('Examples could not be loaded.');
  return response.json();
}).then((data) => {
  if (data.format !== 'plaintext-recorded-examples-v1' || !Array.isArray(data.examples) || !data.examples.length) throw new Error('Example data is invalid.');
  records = data.examples;
  $('another').disabled = false;
  chooseExample();
}).catch(() => {
  $('demo-status').textContent = 'The recorded examples could not load.';
  $('demo-note').textContent = 'Reload this page, or follow the experiment links on GitHub. The local setup guide is still available below.';
});
