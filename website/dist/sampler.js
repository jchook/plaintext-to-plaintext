'use strict';

const SamplerDemo = (() => {
  function recovered(interval, bitLength) {
    const scale = 1n << BigInt(bitLength);
    const first = (interval.low * scale / interval.den).toString(2).padStart(bitLength, '0');
    const last = ((interval.high * scale - 1n) / interval.den).toString(2).padStart(bitLength, '0');
    let count = 0;
    while (count < bitLength && first[count] === last[count]) count += 1;
    return first.slice(0, count);
  }

  function hexToBits(hex) {
    if (!/^(?:[0-9a-f]{2})+$/i.test(hex)) throw new Error('Invalid recorded ciphertext.');
    return hex.match(/../g).map((byte) => parseInt(byte, 16).toString(2).padStart(8, '0')).join('');
  }

  function prepare(record, total) {
    if (total !== 65536 || !Array.isArray(record.steps) || !record.steps.length) throw new Error('Invalid sampler recording.');
    const bits = hexToBits(record.ciphertext);
    let interval = {low: 0n, high: 1n, den: 1n};
    const steps = record.steps.map((source) => {
      let start = 0;
      const rows = source.rows.map((row) => {
        if (!Number.isInteger(row.count) || row.count < 1 || typeof row.token !== 'string') throw new Error('Invalid candidate.');
        const result = {...row, start}; start += row.count; return result;
      });
      if (start !== total || !rows[source.chosen]) throw new Error('Invalid probability table.');
      const chosen = rows[source.chosen];
      const before = interval;
      const width = before.high - before.low;
      interval = {low: before.low * BigInt(total) + width * BigInt(chosen.start),
        high: before.low * BigInt(total) + width * BigInt(chosen.start + chosen.count),
        den: before.den * BigInt(total)};
      return {rows, chosen, before, after: interval, decoded: recovered(interval, bits.length)};
    });
    if (recovered(interval, bits.length) !== bits) throw new Error('Ciphertext recovery differs from recording.');
    if (steps.map((step) => step.chosen.token).join('') + record.suffix !== record.continuation ||
        record.cover !== record.opening + '\n\n' + record.continuation) throw new Error('Cover differs from recording.');
    // Any point inside the final interval reproduces the recorded token path.
    const pointNum = interval.low + interval.high, pointDen = 2n * interval.den;
    steps.forEach((step) => {
      const numerator = pointNum * step.before.den - step.before.low * pointDen;
      const denominator = (step.before.high - step.before.low) * pointDen;
      step.position = Number(numerator * (1n << 53n) / denominator) / 2 ** 53;
    });
    return {record, bits, steps};
  }

  function log2Integer(value) {
    const shift = Math.max(0, value.toString(2).length - 53);
    return Math.log2(Number(value >> BigInt(shift))) + shift;
  }
  return {prepare, recovered, hexToBits, log2Integer};
})();

if (typeof module !== 'undefined' && module.exports) module.exports = SamplerDemo;

if (typeof document !== 'undefined') {
  const el = (id) => document.getElementById(id);
  let recordings, selected, cursor = 0, timer;
  const percent = (count) => `${(count / 655.36).toFixed(count < 7 ? 4 : 2)}%`;

  function pause() {
    clearInterval(timer); timer = undefined;
    el('sampler-play').textContent = 'Play';
    el('sampler-play').setAttribute('aria-pressed', 'false');
  }

  function render() {
    const {record, bits, steps} = selected;
    const complete = cursor === steps.length;
    const step = steps[Math.min(cursor, steps.length - 1)];
    const decoded = cursor ? steps[cursor - 1].decoded : '';
    const interval = cursor ? steps[cursor - 1].after : {low: 0n, high: 1n, den: 1n};
    el('sampler-opening').textContent = record.opening;
    el('sampler-output').textContent = steps.slice(0, cursor).map((item) => item.chosen.token).join('') + (complete ? record.suffix : '');
    el('sampler-output').scrollTop = el('sampler-output').scrollHeight;
    el('sampler-step').textContent = complete ? `Complete · ${cursor} payload tokens` : `Next token · step ${cursor + 1} of ${steps.length}`;
    el('sampler-next').textContent = complete ? 'Ciphertext recovered' : `Next: ${JSON.stringify(step.chosen.token)}`;
    el('sampler-next').disabled = complete;
    el('sampler-back').disabled = cursor === 0;
    el('sampler-play').disabled = complete;
    if (complete) pause();
    el('sampler-rows').replaceChildren();
    const top = step.rows.slice().sort((a, b) => b.count - a.count).slice(0, 4);
    if (!top.includes(step.chosen)) top.push(step.chosen);
    top.forEach((row) => {
      const tr = document.createElement('tr');
      if (row === step.chosen) tr.className = 'chosen';
      const token = document.createElement('td');
      const code = document.createElement('code'); code.textContent = JSON.stringify(row.token); token.append(code);
      const probability = document.createElement('td');
      const bar = document.createElement('span'); bar.className = 'token-probability';
      bar.style.setProperty('--probability', `${row.count / 655.36}%`);
      bar.textContent = percent(row.count); probability.append(bar);
      const range = document.createElement('td');
      range.textContent = `[${(row.start / 65536).toFixed(5)}, ${((row.start + row.count) / 65536).toFixed(5)})`;
      const choice = document.createElement('td'); choice.textContent = row === step.chosen ? 'Selected' : '';
      tr.append(token, probability, range, choice); el('sampler-rows').append(tr);
    });
    el('sampler-strip').replaceChildren();
    step.rows.forEach((row) => {
      const segment = document.createElement('span'); segment.style.flex = row.count;
      segment.className = row === step.chosen ? 'selected-segment' : '';
      segment.setAttribute('aria-label', `${JSON.stringify(row.token)}: ${percent(row.count)}`);
      el('sampler-strip').append(segment);
    });
    el('sampler-point').style.left = `${step.position * 100}%`;
    el('sampler-point').setAttribute('aria-label', `Payload position: ${step.position.toFixed(6)}`);
    el('sampler-recovered').textContent = decoded.padEnd(bits.length, '·').match(/.{8}/g).join(' ');
    const logWidth = SamplerDemo.log2Integer(interval.high - interval.low) - SamplerDemo.log2Integer(interval.den);
    el('sampler-interval').textContent = (2 ** logWidth).toExponential(3);
    el('sampler-result').textContent = complete ? `Recovered all ${bits.length} ciphertext bits. The final sentence is completed without encoding more data.` :
      `Recovered ${decoded.length} of ${bits.length} ciphertext bits from ${cursor} tokens.`;
  }

  function reset() {
    pause();
    selected = recordings[Number(el('sampler-context').value)];
    el('sampler-bits').value = selected.record.ciphertext;
    el('sampler-source').href = 'https://github.com/jchook/plaintext-to-plaintext/blob/main/' + selected.record.artifact_path + '.encode.json';
    cursor = 0; render();
  }
  el('sampler-next').addEventListener('click', () => {pause(); if (selected && cursor < selected.steps.length) {cursor += 1; render();}});
  el('sampler-back').addEventListener('click', () => {pause(); if (cursor > 0) {cursor -= 1; render();}});
  el('sampler-play').addEventListener('click', () => {
    if (timer) {pause(); return;}
    el('sampler-play').textContent = 'Pause';
    el('sampler-play').setAttribute('aria-pressed', 'true');
    timer = setInterval(() => {if (cursor < selected.steps.length) {cursor += 1; render();} else pause();}, 110);
  });
  el('sampler-reset').addEventListener('click', reset);
  el('sampler-context').addEventListener('change', reset);
  document.addEventListener('visibilitychange', () => {if (document.hidden) pause();});
  ['sampler-next', 'sampler-back', 'sampler-play', 'sampler-reset', 'sampler-context'].forEach((id) => {el(id).disabled = true;});
  fetch('./sampler-recordings.json').then((response) => {
    if (!response.ok) throw new Error('Could not load sampler recordings.');
    return response.json();
  }).then((data) => {
    if (data.format !== 'plaintext-sampler-recordings-v1') throw new Error('Invalid recording format.');
    recordings = data.records.map((record) => SamplerDemo.prepare(record, data.total));
    el('sampler-context').replaceChildren();
    recordings.forEach((item, index) => {
      const option = document.createElement('option'); option.value = index; option.textContent = item.record.label;
      el('sampler-context').append(option);
    });
    el('sampler-context').value = '0';
    el('sampler-context').disabled = false; el('sampler-reset').disabled = false;
    reset();
  }).catch(() => {el('sampler-error').hidden = false; el('sampler-error').textContent = 'The sampler recording could not load. Reload the page to try again.';});
}
