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
      assert.ok(step.after.high - step.after.low < (step.before.high - step.before.low) * 8);
    }
    const other = context === 'field' ? 'letter' : 'field';
    assert.throws(() => demo.decode(steps.map((step) => step.chosen.token), other));
    cases += 1;
  }
}
for (const invalid of ['', '010', '111111111', '010x0101', 'abcdefgh', ' 0101010']) {
  assert.throws(() => demo.trace(invalid, 'field'));
}
assert.throws(() => demo.trace('10110110', 'unknown'));
console.log(`${cases} sampler round trips passed, including partial recovery, interval selection, and context mismatch.`);
