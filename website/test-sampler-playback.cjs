'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const data = require('./dist/sampler-recordings.json');
const demo = require('./dist/sampler.js');

// Exercise the real event handlers with a controlled clock. This does not
// emulate browser layout or scroll anchoring.
class Element {
  constructor() {
    this.children = []; this.attributes = {}; this.listeners = {};
    this.style = {setProperty() {}}; this.hidden = false; this.disabled = false;
    this.value = ''; this._text = ''; this.scrollTop = 0;
  }
  set textContent(value) {this._text = value; this.children = [];}
  get textContent() {return this._text + this.children.map((child) => child.textContent).join('');}
  get scrollHeight() {return this.textContent.length;}
  append(...children) {this.children.push(...children);}
  replaceChildren(...children) {this._text = ''; this.children = children;}
  setAttribute(name, value) {this.attributes[name] = value;}
  getAttribute(name) {return this.attributes[name];}
  addEventListener(name, callback) {this.listeners[name] = callback;}
  click() {if (!this.disabled && !this.hidden) this.listeners.click?.();}
}
const textNode = (text) => ({data: text, get textContent() {return this.data;}});
const elements = new Map([...fs.readFileSync(path.join(__dirname, 'dist/index.html'), 'utf8').matchAll(/id="([^"]+)"/g)].map((match) => [match[1], new Element()]));
const el = (id) => {assert.ok(elements.has(id), `Missing element ${id}`); return elements.get(id);};
let clockId = 0;
const timers = new Map();
const document = {getElementById: el, createElement: () => new Element(), createTextNode: textNode,
  hidden: false, addEventListener() {}};
const context = vm.createContext({document,
  fetch: async () => ({ok: true, json: async () => data}),
  setInterval: (callback) => {timers.set(++clockId, callback); return clockId;},
  clearInterval: (id) => timers.delete(id)});
vm.runInContext(fs.readFileSync(path.join(__dirname, 'dist/sampler.js'), 'utf8'), context);
const tick = () => {for (const [id, callback] of [...timers]) if (timers.has(id)) callback();};
const drain = () => {let guard = 0; while (timers.size && guard++ < 300) tick(); assert.equal(timers.size, 0);};
const position = () => Number(el('sampler-step').textContent.split(' / ')[0]);

(async () => {
  await new Promise(setImmediate);
  assert.equal(position(), 0);
  el('sampler-next').click(); el('sampler-next').click(); el('sampler-next').click();
  assert.equal(position(), 3);
  const outputNodes = [...el('sampler-output').children];
  el('sampler-play').click(); tick();
  assert.equal(position(), 4);
  drain();
  const excerpt = demo.excerptLength(data.records[0]);
  assert.equal(position(), excerpt);
  tick(); assert.equal(position(), excerpt, 'Completion must retain the final position');
  assert.equal(el('sampler-next').hidden, false, 'Completion must keep the focused control in place');
  assert.equal(el('sampler-play').disabled, false, 'Completion must not discard native button focus');
  assert.equal(el('sampler-play').getAttribute('aria-disabled'), 'true');
  outputNodes.forEach((node, index) => assert.equal(el('sampler-output').children[index], node, 'Output nodes must survive playback'));
  const expectedExcerpt = data.records[0].steps.slice(0, excerpt).map((step) => step.rows[step.chosen].token).join('');
  assert.equal(el('sampler-output').textContent, expectedExcerpt);
  el('sampler-play').click(); tick(); assert.equal(position(), excerpt);

  // The same Next button extends the excerpt without moving backward.
  el('sampler-next').click(); assert.equal(position(), excerpt);
  el('sampler-play').click(); drain();
  assert.equal(position(), data.records[0].steps.length);
  assert.equal(el('sampler-output').textContent, data.records[0].continuation);
  el('sampler-back').click();
  assert.equal(position(), data.records[0].steps.length - 1);
  el('sampler-play').click(); drain();
  assert.equal(position(), data.records[0].steps.length);

  // Pause/resume, reset, and switching recordings must cancel old playback.
  el('sampler-reset').click();
  el('sampler-play').click(); tick(); tick();
  el('sampler-play').click(); tick(); assert.equal(position(), 2);
  el('sampler-play').click(); tick(); assert.equal(position(), 3);
  el('sampler-reset').click(); tick(); assert.equal(position(), 0);
  el('sampler-play').click(); tick();
  el('sampler-context').value = '1'; el('sampler-context').listeners.change();
  tick(); assert.equal(position(), 0);
  el('sampler-next').click(); el('sampler-play').click(); drain();
  assert.equal(position(), demo.excerptLength(data.records[1]));
  console.log('Playback event tests passed: Next → Play → finish, stable controls and output, continuation, pause/resume, reset, and recording changes.');
})().catch((error) => {console.error(error); process.exitCode = 1;});
