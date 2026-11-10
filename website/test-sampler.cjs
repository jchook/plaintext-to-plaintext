'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const demo = require('./dist/sampler.js');
const data = require('./dist/sampler-recordings.json');
assert.equal(data.format, 'plaintext-sampler-recordings-v1');
let count = 0;
for (const record of data.records) {
  const prepared = demo.prepare(record, data.total);
  assert.ok(prepared.steps.length > 100);
  assert.equal(crypto.createHash('sha256').update(record.cover).digest('hex'), record.cover_sha256);
  assert.equal(fs.readFileSync(path.join(__dirname, '..', record.artifact_path + '.cover.txt'), 'utf8'), record.cover);
  for (const step of prepared.steps) {
    assert.ok(prepared.bits.startsWith(step.decoded));
    assert.ok(step.position >= step.chosen.start / data.total);
    assert.ok(step.position < (step.chosen.start + step.chosen.count) / data.total);
    assert.ok(Number.isFinite(demo.log2Integer(step.after.den)));
    count += 1;
  }
  assert.equal(prepared.steps.at(-1).decoded, prepared.bits);
  const altered = structuredClone(record);
  altered.steps[0].rows[0].count += 1;
  assert.throws(() => demo.prepare(altered, data.total));
  const changedToken = structuredClone(record);
  changedToken.steps[0].rows[changedToken.steps[0].chosen].token += 'changed';
  assert.throws(() => demo.prepare(changedToken, data.total));
  const changedCiphertext = structuredClone(record);
  changedCiphertext.ciphertext = '00' + record.ciphertext.slice(2);
  assert.throws(() => demo.prepare(changedCiphertext, data.total));
}
console.log(`Verified ${count} actual sampler steps, exact ciphertext recovery, archived text, and altered-recording rejection.`);
