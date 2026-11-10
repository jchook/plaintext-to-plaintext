'use strict';

const SamplerDemo = (() => {
  // These invented token strings and dyadic weights illustrate interval coding.
  // They are not probabilities or token boundaries from the production model.
  const profiles = {
    field: {
      opening: 'We reached the ridge just before sunrise.', prefix: 'The', order: [2, 0, 3, 1],
      tokens: [
        [' cool', ' crisp', ' still', ' fresh'], [' air', ' wind', ' breeze', ' morning'],
        [' felt', ' seemed', ' was', ' stayed'], [' pleasant', ' calm', ' mild', ' quiet'],
        [' as', ' while', ' when', ' before'], [' we', ' I', ' they', ' everyone'],
        [' watched', ' saw', ' noticed', ' followed'], [' the sunrise.', ' the clouds.', ' the horizon.', ' the light.']
      ]
    },
    letter: {
      opening: 'Thanks for the conversation at yesterday’s workshop.', prefix: 'I', order: [1, 3, 0, 2],
      tokens: [
        [' enjoyed', ' appreciated', ' liked', ' valued'], [' the', ' your', ' our', ' that'],
        [' session', ' discussion', ' exchange', ' conversation'], [' and', ' because', ' as', ' since'],
        [' it', ' this', ' that', ' everything'], [' felt', ' seemed', ' was', ' stayed'],
        [' quite', ' especially', ' very', ' fairly'], [' useful.', ' clear.', ' helpful.', ' relevant.']
      ]
    }
  };

  function candidates(profile, history) {
    const step = history.length;
    const counts = step % 2 ? [3, 2, 2, 1] : [4, 2, 1, 1];
    const rotation = history.reduce((sum, index) => sum + index + 1, 0) % 4;
    const order = profile.order.slice(rotation).concat(profile.order.slice(0, rotation));
    let start = 0;
    return order.map((index) => {
      const sentenceStart = step > 0 && step % 8 === 0 ? ` ${profile.prefix}` : '';
      const row = {index, token: sentenceStart + profile.tokens[step % 8][index], count: counts[index], start};
      start += row.count;
      return row;
    });
  }

  function narrow(interval, row) {
    const width = interval.high - interval.low;
    return {low: interval.low * 8n + width * BigInt(row.start),
      high: interval.low * 8n + width * BigInt(row.start + row.count), den: interval.den * 8n};
  }

  function recovered(interval, bitLength = 8) {
    const scale = 1n << BigInt(bitLength);
    const first = (interval.low * scale / interval.den).toString(2).padStart(bitLength, '0');
    const last = ((interval.high * scale - 1n) / interval.den).toString(2).padStart(bitLength, '0');
    let count = 0;
    while (count < bitLength && first[count] === last[count]) count += 1;
    return first.slice(0, count);
  }

  function hexToBits(hex) {
    const compact = hex.replace(/\s/g, '');
    if (!/^(?:[0-9a-f]{2}){1,16}$/i.test(compact)) throw new Error('Enter 1–16 bytes as hexadecimal pairs.');
    return compact.match(/../g).map((byte) => parseInt(byte, 16).toString(2).padStart(8, '0')).join('');
  }

  function trace(bits, context) {
    if (!/^[01]{8,128}$/.test(bits) || bits.length % 8 || !profiles[context]) {
      throw new Error('Choose a context and enter 1–16 bytes of binary data.');
    }
    const pointNum = 2n * BigInt(`0b${bits}`) + 1n;
    const pointDen = 1n << BigInt(bits.length + 1);
    const profile = profiles[context];
    let interval = {low: 0n, high: 1n, den: 1n};
    const history = [], steps = [];
    while (recovered(interval, bits.length).length < bits.length) {
      const rows = candidates(profile, history);
      const positionNum = pointNum * interval.den - interval.low * pointDen;
      const positionDen = (interval.high - interval.low) * pointDen;
      const offset = Number(positionNum * 8n / positionDen);
      const chosen = rows.find((row) => row.start <= offset && offset < row.start + row.count);
      const next = narrow(interval, chosen);
      steps.push({before: interval, after: next, rows, chosen,
        position: Number(positionNum * 1000000n / positionDen) / 1000000});
      history.push(chosen.index);
      interval = next;
    }
    return steps;
  }

  function decode(tokens, context, bitLength = 8) {
    const history = [];
    let interval = {low: 0n, high: 1n, den: 1n};
    for (const token of tokens) {
      const row = candidates(profiles[context], history).find((item) => item.token === token);
      if (!row) throw new Error('Token does not match this context.');
      interval = narrow(interval, row);
      history.push(row.index);
    }
    return recovered(interval, bitLength);
  }
  return {profiles, trace, decode, recovered, hexToBits};
})();

if (typeof module !== 'undefined' && module.exports) module.exports = SamplerDemo;

if (typeof document !== 'undefined') {
  const el = (id) => document.getElementById(id);
  let steps, payloadBits, cursor = 0, timer;

  function pause() {
    clearInterval(timer); timer = undefined;
    el('sampler-play').textContent = 'Play';
    el('sampler-play').setAttribute('aria-pressed', 'false');
  }

  function render() {
    const profile = SamplerDemo.profiles[el('sampler-context').value];
    const complete = cursor === steps.length;
    const step = steps[Math.min(cursor, steps.length - 1)];
    const emitted = steps.slice(0, cursor).map((item) => item.chosen.token);
    const interval = cursor ? steps[cursor - 1].after : {low: 0n, high: 1n, den: 1n};
    el('sampler-opening').textContent = profile.opening;
    el('sampler-output').textContent = profile.prefix + emitted.join('');
    el('sampler-step').textContent = complete ? `Complete · ${cursor} tokens` : `Next token · step ${cursor + 1}`;
    el('sampler-next').textContent = complete ? 'Ciphertext recovered' : `Emit “${step.chosen.token.trim()}”`;
    el('sampler-next').disabled = complete;
    el('sampler-back').disabled = cursor === 0;
    el('sampler-play').disabled = complete;
    if (complete) pause();
    el('sampler-rows').replaceChildren();
    step.rows.slice().sort((a, b) => b.count - a.count || a.index - b.index).forEach((row) => {
      const tr = document.createElement('tr');
      const active = row === step.chosen;
      if (active) tr.className = 'chosen';
      const token = document.createElement('td');
      const code = document.createElement('code'); code.textContent = JSON.stringify(row.token); token.append(code);
      const probability = document.createElement('td');
      const bar = document.createElement('span'); bar.className = 'token-probability';
      bar.style.setProperty('--probability', `${row.count / 8 * 100}%`);
      bar.textContent = `${row.count / 8 * 100}%`; probability.append(bar);
      const range = document.createElement('td'); range.textContent = `[${row.start / 8}, ${(row.start + row.count) / 8})`;
      const selection = document.createElement('td'); selection.textContent = active ? 'Selected' : '';
      tr.append(token, probability, range, selection); el('sampler-rows').append(tr);
    });
    el('sampler-strip').replaceChildren();
    step.rows.forEach((row) => {
      const segment = document.createElement('span'); segment.style.flex = row.count;
      segment.className = row === step.chosen ? 'selected-segment' : '';
      segment.textContent = row.token.trim(); el('sampler-strip').append(segment);
    });
    el('sampler-point').style.left = `${step.position * 100}%`;
    el('sampler-point').setAttribute('aria-label', `Payload position within this interval: ${step.position.toFixed(6)}`);
    const bits = SamplerDemo.decode(emitted, el('sampler-context').value, payloadBits.length);
    el('sampler-recovered').textContent = bits.padEnd(payloadBits.length, '·').match(/.{8}/g).join(' ');
    el('sampler-interval').textContent = (Number(interval.high - interval.low) / Number(interval.den)).toExponential(3);
    el('sampler-result').textContent = complete ? `Recovered all ${payloadBits.length} bits from ${cursor} emitted tokens.` : `Recovered ${bits.length} of ${payloadBits.length} bits from ${cursor} emitted tokens.`;
  }

  function reset() {
    pause();
    let valid = true;
    try {payloadBits = SamplerDemo.hexToBits(el('sampler-bits').value);} catch {valid = false;}
    el('sampler-error').hidden = valid;
    el('sampler-bits').setAttribute('aria-invalid', String(!valid));
    if (!valid) {
      ['sampler-next', 'sampler-back', 'sampler-play'].forEach((id) => {el(id).disabled = true;});
      return;
    }
    steps = SamplerDemo.trace(payloadBits, el('sampler-context').value);
    cursor = 0; render();
  }
  el('sampler-next').addEventListener('click', () => {pause(); if (cursor < steps.length) {cursor += 1; render();}});
  el('sampler-back').addEventListener('click', () => {pause(); if (cursor > 0) {cursor -= 1; render();}});
  el('sampler-play').addEventListener('click', () => {
    if (timer) {pause(); return;}
    el('sampler-play').textContent = 'Pause';
    el('sampler-play').setAttribute('aria-pressed', 'true');
    timer = setInterval(() => {if (cursor < steps.length) {cursor += 1; render();} else pause();}, 450);
  });
  el('sampler-reset').addEventListener('click', reset);
  el('sampler-bits').addEventListener('input', reset);
  el('sampler-context').addEventListener('change', reset);
  document.addEventListener('visibilitychange', () => {if (document.hidden) pause();});
  reset();
}
