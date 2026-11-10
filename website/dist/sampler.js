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
      const row = {index, token: profile.tokens[step][index], count: counts[index], start};
      start += row.count;
      return row;
    });
  }

  function narrow(interval, row) {
    const width = interval.high - interval.low;
    return {low: interval.low * 8 + width * row.start,
      high: interval.low * 8 + width * (row.start + row.count), den: interval.den * 8};
  }

  function recovered(interval) {
    const first = Math.floor(interval.low * 256 / interval.den).toString(2).padStart(8, '0');
    const last = Math.floor((interval.high * 256 - 1) / interval.den).toString(2).padStart(8, '0');
    let count = 0;
    while (count < 8 && first[count] === last[count]) count += 1;
    return first.slice(0, count);
  }

  function trace(bits, context) {
    if (!/^[01]{8}$/.test(bits) || !profiles[context]) throw new Error('Choose a context and enter eight binary digits.');
    const value = parseInt(bits, 2);
    const pointNum = 2 * value + 1;
    const profile = profiles[context];
    let interval = {low: 0, high: 1, den: 1};
    const history = [], steps = [];
    while (recovered(interval).length < 8) {
      const rows = candidates(profile, history);
      const offset = Math.floor((pointNum * interval.den - interval.low * 512) * 8 /
        ((interval.high - interval.low) * 512));
      const chosen = rows.find((row) => row.start <= offset && offset < row.start + row.count);
      const next = narrow(interval, chosen);
      steps.push({before: interval, after: next, rows, chosen,
        position: (pointNum * interval.den / 512 - interval.low) / (interval.high - interval.low)});
      history.push(chosen.index);
      interval = next;
    }
    return steps;
  }

  function decode(tokens, context) {
    const history = [];
    let interval = {low: 0, high: 1, den: 1};
    for (const token of tokens) {
      const row = candidates(profiles[context], history).find((item) => item.token === token);
      if (!row) throw new Error('Token does not match this context.');
      interval = narrow(interval, row);
      history.push(row.index);
    }
    return recovered(interval);
  }
  return {profiles, trace, decode, recovered};
})();

if (typeof module !== 'undefined' && module.exports) module.exports = SamplerDemo;

if (typeof document !== 'undefined') {
  const el = (id) => document.getElementById(id);
  let steps, cursor = 0;

  function render() {
    const profile = SamplerDemo.profiles[el('sampler-context').value];
    const complete = cursor === steps.length;
    const step = steps[Math.min(cursor, steps.length - 1)];
    const emitted = steps.slice(0, cursor).map((item) => item.chosen.token);
    const interval = cursor ? steps[cursor - 1].after : {low: 0, high: 1, den: 1};
    el('sampler-opening').textContent = profile.opening;
    el('sampler-output').textContent = profile.prefix + emitted.join('');
    el('sampler-step').textContent = complete ? `Complete · ${cursor} tokens` : `Next token · step ${cursor + 1}`;
    el('sampler-next').textContent = complete ? 'Byte recovered' : `Emit “${step.chosen.token.trim()}”`;
    el('sampler-next').disabled = complete;
    el('sampler-back').disabled = cursor === 0;
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
    const bits = SamplerDemo.decode(emitted, el('sampler-context').value);
    el('sampler-recovered').textContent = bits.padEnd(8, '·');
    el('sampler-interval').textContent = `[${(interval.low / interval.den).toFixed(6)}, ${(interval.high / interval.den).toFixed(6)})`;
    el('sampler-result').textContent = complete ? 'Recovered all 8 bits from the emitted tokens.' : `${bits.length} of 8 bits recovered from ${cursor} emitted tokens.`;
  }

  function reset() {
    const bits = el('sampler-bits').value;
    const valid = /^[01]{8}$/.test(bits);
    el('sampler-error').hidden = valid;
    el('sampler-bits').setAttribute('aria-invalid', String(!valid));
    if (!valid) {el('sampler-next').disabled = true; el('sampler-back').disabled = true; return;}
    steps = SamplerDemo.trace(bits, el('sampler-context').value);
    cursor = 0; render();
  }
  el('sampler-next').addEventListener('click', () => {if (cursor < steps.length) {cursor += 1; render();}});
  el('sampler-back').addEventListener('click', () => {if (cursor > 0) {cursor -= 1; render();}});
  el('sampler-reset').addEventListener('click', reset);
  el('sampler-bits').addEventListener('input', reset);
  el('sampler-context').addEventListener('change', reset);
  reset();
}
