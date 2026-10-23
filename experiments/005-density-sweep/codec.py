#!/usr/bin/env python3
"""Experimental CLI adapter; historical opening-v1 implementation is unchanged.

Only the allowed temperature whitelist is widened. Probabilities, arithmetic
coding, prompts, framing and protocol configuration remain opening-v1. At 1.0
and 1.2 this adapter has identical codec behavior to the historical CLI.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'poc'))
import opening

opening.TEMPERATURES = ('0.8', '1.0', '1.2', '1.4', '1.6')

if __name__ == '__main__':
    raise SystemExit(opening.main())
