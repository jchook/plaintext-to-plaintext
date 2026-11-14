"""Deterministic OD-Stega KL shaping on an already filtered distribution.

Maximize H(Q) subject to D_KL(Q || P) <= coefficient * H(P), in bits.
P is the current fixed-temperature, prefix-free candidate distribution.
See https://aclanthology.org/2026.eacl-long.36.pdf, sections 3.2–3.3.
"""
from decimal import Decimal, DecimalException, localcontext

import p2p

PRECISION = 40
BISECTION_STEPS = 48


def validate_budget(value):
    """Canonical shared configuration; equivalent decimal spellings agree."""
    try:
        if isinstance(value, bool) or len(str(value)) > 64:
            raise ValueError
        with localcontext() as ctx:
            ctx.prec = PRECISION
            budget = Decimal(str(value))
            if not budget.is_finite() or budget < 0:
                raise ValueError
            return '0' if not budget else str(budget.normalize())
    except (DecimalException, ValueError):
        raise p2p.CodecError('KL budget must be a finite, nonnegative decimal number.') from None


def shape(candidates, coefficient):
    """Return candidates with shaped weights and pre-integer-table diagnostics.

Search the inverse temperature in [0, 1]; zero is uniform. The feasible
endpoint is retained, so bisection never deliberately exceeds the budget.
Arithmetic-table quantization is a subsequent, separate operation.
"""
    coefficient = Decimal(validate_budget(coefficient))
    with localcontext() as ctx:
        ctx.prec = PRECISION
        weights = [item.weight for item in candidates]
        if not weights or any(not w.is_finite() or w <= 0 for w in weights):
            raise p2p.CodecError('KL shaping requires positive finite candidate weights.')
        mass = sum(weights)
        probabilities = [w / mass for w in weights]
        logs = [p.ln() for p in probabilities]
        ln2 = Decimal(2).ln()
        reference_entropy = -sum(p * logp for p, logp in zip(probabilities, logs)) / ln2
        budget = coefficient * reference_entropy

        def evaluate(exponent):
            # Centering avoids underflow when the original weights are tiny.
            peak = max(logs)
            scaled = [(exponent * (logp - peak)).exp() for logp in logs]
            total = sum(scaled)
            log_total = total.ln()
            q = [w / total for w in scaled]
            logq = [exponent * (logp - peak) - log_total for logp in logs]
            entropy = -sum(a * b for a, b in zip(q, logq)) / ln2
            divergence = max(Decimal(0), sum(
                a * (b - c) for a, b, c in zip(q, logq, logs)) / ln2)
            return q, entropy, divergence

        exponent = Decimal(1)
        q, entropy, divergence = probabilities, reference_entropy, Decimal(0)
        if coefficient:
            uniform = evaluate(Decimal(0))
            if uniform[2] <= budget:
                exponent = Decimal(0)
                q, entropy, divergence = uniform
            else:
                low, high = Decimal(0), Decimal(1)
                for _ in range(BISECTION_STEPS):
                    middle = (low + high) / 2
                    trial = evaluate(middle)
                    if trial[2] <= budget:
                        high = exponent = middle
                        q, entropy, divergence = trial
                    else:
                        low = middle
        shaped = ([p2p.Candidate(item.token_id, item.raw, weight)
                   for item, weight in zip(candidates, q)] if coefficient else candidates)
        return shaped, {
            'reference_entropy_bits': float(reference_entropy),
            'shaped_entropy_bits': float(entropy),
            'kl_divergence_bits': float(divergence),
            'kl_budget_bits': float(budget),
            'uniform': exponent == 0,
        }
