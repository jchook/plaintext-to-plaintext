"""KL optimizer checks using independently calculated float probabilities."""
from decimal import Decimal, localcontext
import math
import unittest

import p2p
import shaping


def candidates(weights):
    return [p2p.Candidate(i, f' choice{i}'.encode(), Decimal(str(w)))
            for i, w in enumerate(weights)]


def probabilities(items):
    mass = sum(item.weight for item in items)
    return [float(item.weight / mass) for item in items]


def entropy(p):
    return -sum(a * math.log2(a) for a in p if a)


class ShapingTests(unittest.TestCase):
    def test_zero_is_exact_identity_and_budget_is_canonical(self):
        items = candidates([97, 1, 2])
        self.assertIs(shaping.shape(items, '0')[0], items)
        for value in ('0.0500', '.05', '5e-2', 0.05):
            self.assertEqual(shaping.validate_budget(value), '0.05')
        self.assertEqual(shaping.validate_budget('-0.0'), '0')
        for value in ('NaN', 'Infinity', '-0.1', '', None, True, [], '9' * 100):
            with self.subTest(value=value), self.assertRaises(p2p.CodecError):
                shaping.validate_budget(value)

    def test_entropy_maximization_respects_budget_and_preserves_support(self):
        items = candidates([.5] + [1 / 30] * 15)
        original = probabilities(items)
        previous_entropy = entropy(original)
        for coefficient in ('0.001', '0.01', '0.05', '0.2', '1'):
            shaped, diagnostics = shaping.shape(items, coefficient)
            p = probabilities(shaped)
            divergence = sum(a * math.log2(a / b) for a, b in zip(p, original))
            self.assertLessEqual(divergence, float(coefficient) * entropy(original) + 1e-12)
            self.assertGreaterEqual(entropy(p) + 1e-12, previous_entropy)
            self.assertEqual([(c.token_id, c.raw) for c in items],
                             [(c.token_id, c.raw) for c in shaped])
            self.assertTrue(all(a > 0 for a in p))
            self.assertAlmostEqual(diagnostics['kl_divergence_bits'], divergence)
            previous_entropy = entropy(p)
        shaped, _ = shaping.shape(items, '0.05')
        self.assertAlmostEqual(entropy(probabilities(shaped)), 3.674190396, places=6)

    def test_unequal_probabilities_use_a_single_temperature(self):
        items = candidates([.6, .25, .1, .05])
        p = probabilities(items)
        q = probabilities(shaping.shape(items, '.05')[0])
        exponents = [math.log(q[i] / q[-1]) / math.log(p[i] / p[-1]) for i in range(3)]
        self.assertTrue(0 < exponents[0] < 1)
        for exponent in exponents[1:]:
            self.assertAlmostEqual(exponent, exponents[0])
        divergence = sum(a * math.log2(a / b) for a, b in zip(q, p))
        self.assertAlmostEqual(divergence, .05 * entropy(p), places=12)

    def test_nearly_forced_and_uniform_endpoints(self):
        items = candidates([.999] + [.001 / 15] * 15)
        shaped, _ = shaping.shape(items, '.05')
        self.assertGreater(probabilities(shaped)[0], .997)
        shaped, diagnostics = shaping.shape(items, '1000')
        self.assertTrue(diagnostics['uniform'])
        self.assertEqual(probabilities(shaped), [1 / 16] * 16)
        equal, diagnostics = shaping.shape(candidates([1, 1, 1]), '.05')
        self.assertTrue(diagnostics['uniform'])
        self.assertAlmostEqual(diagnostics['kl_divergence_bits'], 0)

    def test_deterministic_across_decimal_precision_and_weight_scale(self):
        items = candidates([600, 250, 100, 50])
        expected = shaping.shape(items, '.05')
        with localcontext() as ctx:
            ctx.prec = 12
            self.assertEqual(shaping.shape(items, '0.0500'), expected)
        tiny = [p2p.Candidate(c.token_id, c.raw, c.weight * Decimal('1e-1000')) for c in items]
        self.assertEqual(shaping.shape(tiny, '.05'), expected)


if __name__ == '__main__':
    unittest.main()
