'use strict';
const assert = require('node:assert/strict');
const demo = require('./dist/sampler.js');

let cases = 0;
for (const context of Object.keys(demo.profiles)) {
  for (let value = 0; value < 256; value += 1) {
    const bits = value.toString(2).padStart(8, '0');
    const steps = demo.trace(bits, context);
    assert.ok(steps.length > 0 && steps.length <= 8);
    for (let count = 0; count <= steps.length; count += 1) {
      const tokens = steps.slice(0, count).map((step) => step.chosen.token);
      const recovered = demo.decode(tokens, context);
      assert.ok(bits.startsWith(recovered), `${context}: incorrect recovery after ${count} tokens`);
      if (count === steps.length) assert.equal(recovered, bits);
    }
    for (const step of steps) {
      assert.equal(step.rows.reduce((sum, row) => sum + row.count, 0), 8);
      assert.ok(step.position >= step.chosen.start / 8);
      assert.ok(step.position < (step.chosen.start + step.chosen.count) / 8);
      assert.ok(step.after.high - step.after.low < (step.before.high - step.before.low) * 8n);
    }
    const other = context === 'field' ? 'letter' : 'field';
    assert.throws(() => demo.decode(steps.map((step) => step.chosen.token), other));
    cases += 1;
  }
}
for (const invalid of ['', '010', '111111111', '010x0101', 'abcdefgh', ' 0101010', '0'.repeat(136)]) {
  assert.throws(() => demo.trace(invalid, 'field'));
}
assert.throws(() => demo.trace('10110110', 'unknown'));
for (const context of Object.keys(demo.profiles)) {
  for (let bytes = 2; bytes <= 16; bytes += 1) {
    const values = ['0'.repeat(bytes * 8), '1'.repeat(bytes * 8), '01'.repeat(bytes * 4),
      Array.from({length: bytes}, (_, index) => ((index * 71 + bytes * 29) % 256).toString(2).padStart(8, '0')).join('')];
    for (const bits of values) {
      const steps = demo.trace(bits, context);
      for (let count = 0; count <= steps.length; count += 1) {
        const recovered = demo.decode(steps.slice(0, count).map((step) => step.chosen.token), context, bits.length);
        assert.ok(bits.startsWith(recovered));
        if (count === steps.length) assert.equal(recovered, bits);
      }
      cases += 1;
    }
  }
}
const defaultBits = demo.hexToBits('b6a09f3c72e1458d');
assert.equal(defaultBits.length, 64);
for (const context of Object.keys(demo.profiles)) {
  const steps = demo.trace(defaultBits, context);
  assert.ok(steps.length >= 24, 'Default should produce a substantially longer example');
  console.log(`${context}: default generates ${steps.length} tokens for 64 ciphertext bits.`);
}
assert.equal(demo.hexToBits(' B6 a0 '), '1011011010100000');
for (const invalid of ['', 'b', 'xyz', 'a'.repeat(34)]) assert.throws(() => demo.hexToBits(invalid));
console.log(`${cases} round trips passed, including long payloads, partial recovery, and context mismatch.`);
