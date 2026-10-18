#!/usr/bin/env python3
"""Experimental lossless, keyed language codec using a local Llama model.

The decoder receives only the cover text, key file, and shared protocol/model.
No token trace or per-message probability table is saved or transmitted.
"""
from __future__ import annotations

import argparse
import bisect
import contextlib
import decimal
import fcntl
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

MODEL = "llama3.2:3b-instruct-q4_K_M"
MODEL_SHA = "dde5aa3fc5ffc17176b5e8bdc82f587b24b2678c6c66101bf7da77af9f7ccdff"
PROTOCOL = b"plaintext-to-plaintext-poc-v1/" + MODEL_SHA.encode()
TOTAL = 65536
BLOCK = 32
MAX_FRAME = 65536
CONTEXT_TOKENS = 1024
N_PROBS = 64
DEFAULT_URL = "http://127.0.0.1:11535"
PROMPT = (
    "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
    "You write clear, natural, relaxed prose about ordinary daily life. "
    "Output only the requested prose, without a title, introduction, or list."
    "<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n"
    "Write a long first-person journal entry about a pleasant day: breakfast, "
    "a walk through town, errands, meeting a friend, cooking, and a quiet evening. "
    "Include plenty of specific everyday details. Use natural paragraphs and "
    "varied sentences. Aim for about 1500 words."
    "<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
)
SENTENCE_END = re.compile(rb"[.!?][\"')\]]*\s*$")


class CodecError(Exception):
    pass


def derive_keys(material: bytes) -> tuple[bytes, bytes]:
    if not material:
        raise CodecError("The key file is empty.")
    derived = HKDF(algorithm=hashes.SHA256(), length=64,
                   salt=PROTOCOL, info=b"encryption-and-interval-order").derive(material)
    return derived[:32], derived[32:]


def seal(data: bytes, key: bytes) -> bytes:
    size = ((len(data) + 32 + BLOCK - 1) // BLOCK) * BLOCK
    if size > MAX_FRAME:
        raise CodecError(f"Payload exceeds the prototype limit ({MAX_FRAME - 32} bytes).")
    inner = struct.pack(">I", len(data)) + data
    inner += secrets.token_bytes(size - 28 - len(inner))
    nonce = secrets.token_bytes(12)
    return nonce + ChaCha20Poly1305(key).encrypt(nonce, inner, PROTOCOL)


def unseal(frame: bytes, key: bytes) -> bytes:
    if len(frame) < BLOCK or len(frame) % BLOCK:
        raise InvalidTag
    inner = ChaCha20Poly1305(key).decrypt(frame[:12], frame[12:], PROTOCOL)
    size = struct.unpack(">I", inner[:4])[0]
    if size > len(inner) - 4:
        raise InvalidTag
    return inner[4:4 + size]


@dataclass(frozen=True)
class Candidate:
    token_id: int
    raw: bytes
    weight: decimal.Decimal


def prefix_free(candidates: list[Candidate]) -> list[Candidate]:
    """Maximum-weight antichain in the byte trie, with at least two leaves."""
    def solve(items):
        root = {}
        for item in items:
            node = root
            for char in item.raw:
                node = node.setdefault(char, {})
            node[None] = item

        def visit(node):
            children = []
            for char in sorted(k for k in node if k is not None):
                children.extend(visit(node[char]))
            own = node.get(None)
            if own is not None and own.weight >= sum((c.weight for c in children), decimal.Decimal(0)):
                return [own]
            return children

        return visit(root)

    selected = solve(candidates)
    if len(selected) == 1:
        selected = solve([c for c in candidates if c != selected[0]])
    if len(selected) < 2:
        raise CodecError("Model did not expose two unambiguous printable continuations.")
    return sorted(selected, key=lambda c: c.raw)


def candidates_from_response(rows: list[dict]) -> list[Candidate]:
    unique = {}
    with decimal.localcontext() as ctx:
        ctx.prec = 40
        for row in rows:
            raw = bytes(row.get("bytes") or [])
            if not raw or b"<|" in raw:
                continue
            try:
                text = raw.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                continue
            if any(not (ch.isprintable() or ch in "\n\t") for ch in text):
                continue
            logprob = decimal.Decimal(str(row["logprob"]))
            if not logprob.is_finite():
                continue
            item = Candidate(int(row["id"]), raw, logprob.exp())
            prior = unique.get(raw)
            if prior is None or (item.weight, -item.token_id) > (prior.weight, -prior.token_id):
                unique[raw] = item
        return prefix_free(list(unique.values()))


def table(candidates: list[Candidate], key: bytes, history: list[int]):
    """Integer probabilities; largest-remainder allocation with stable ties."""
    with decimal.localcontext() as ctx:
        ctx.prec = 40
        mass = sum(c.weight for c in candidates)
        if not 1 < len(candidates) <= TOTAL:
            raise CodecError("Invalid candidate alphabet size.")
        remaining = TOTAL - len(candidates)
        exact = [c.weight * remaining / mass for c in candidates]
        counts = [1 + int(value) for value in exact]
        ranking = sorted(range(len(candidates)),
                         key=lambda i: (-(exact[i] - int(exact[i])), candidates[i].raw))
        for i in ranking[:TOTAL - sum(counts)]:
            counts[i] += 1
    context = hashlib.sha256(b"".join(struct.pack(">I", i) for i in history)).digest()
    order = sorted(range(len(candidates)),
                   key=lambda i: (hmac.digest(key, context + candidates[i].raw, "sha256"), candidates[i].raw))
    entries = [(candidates[i], counts[i]) for i in order]
    ends, running = [], 0
    for _, count in entries:
        running += count
        ends.append(running)
    return entries, ends


class Interval:
    """Exact rational interval with a common integer denominator."""
    def __init__(self):
        self.low, self.high, self.den = 0, 1, 1

    def choose(self, point_num: int, point_den: int, ends: list[int]) -> int:
        offset = ((point_num * self.den - self.low * point_den) * TOTAL
                  // ((self.high - self.low) * point_den))
        if not 0 <= offset < TOTAL:
            raise CodecError("Interval invariant violated.")
        return bisect.bisect_right(ends, offset)

    def advance(self, start: int, count: int):
        width = self.high - self.low
        self.low, self.high = (self.low * TOTAL + width * start,
                               self.low * TOTAL + width * (start + count))
        self.den *= TOTAL

    def common_bytes(self, size: int) -> bytes | None:
        bits = size * 8
        low = (self.low << bits) // self.den
        high = ((self.high << bits) - 1) // self.den
        return low.to_bytes(size, "big") if low == high else None

    def information_bits(self) -> float:
        return math.log2(self.den) - math.log2(self.high - self.low)


class Llama:
    def __init__(self, url: str = DEFAULT_URL, cold: bool = False):
        self.url = url.rstrip("/")
        self.cold = cold
        props = self.request("/props")
        model_path = props.get("model_path", "")
        if not model_path.endswith(MODEL_SHA):
            raise CodecError(f"Server must load the pinned {MODEL} GGUF (SHA256 {MODEL_SHA}).")
        if props.get("total_slots") != 1:
            raise CodecError("The prototype requires a dedicated single-slot server.")
        self.build = props.get("build_info", "unknown")
        self.base = self.request("/tokenize", {"content": PROMPT, "add_special": False,
                                               "parse_special": True})["tokens"]
        self.calls = 0
        self.mass_sum = 0.0

    def request(self, path, body=None):
        req = urllib.request.Request(self.url + path,
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise CodecError(f"Inference HTTP {error.code}: {error.read().decode()}") from error
        except urllib.error.URLError as error:
            raise CodecError(f"Cannot reach {self.url}; start `python3 poc/p2p.py serve` first.") from error

    def candidates(self, history: list[int]) -> list[Candidate]:
        # Both sides make the same ordered calls, starting with an empty cache.
        # Explicit token IDs prevent the API from retokenizing the chosen path.
        prompt = self.base + history[-CONTEXT_TOKENS:]
        response = self.request("/completion", {
            "prompt": prompt, "n_predict": 1, "n_probs": N_PROBS,
            "temperature": -1, "seed": 42, "stream": False,
            "cache_prompt": bool(self.calls) and not self.cold,
            "return_tokens": True, "top_k": 0, "top_p": 1.0,
            "min_p": 0.0, "repeat_penalty": 1.0,
        })
        if response.get("truncated"):
            raise CodecError("Inference server truncated the shared context.")
        records = response.get("completion_probabilities") or response.get("probs")
        if not records:
            raise CodecError("Inference server did not return token probabilities.")
        selected = candidates_from_response(records[0]["top_logprobs"])
        self.calls += 1
        self.mass_sum += float(sum(c.weight for c in selected))
        return selected


def finish(oracle, history: list[int], cover: bytes) -> bytes:
    """Deterministic sentence completion, also checked by the decoder."""
    suffix = bytearray()
    for _ in range(64):
        if SENTENCE_END.search(cover + suffix):
            return bytes(suffix)
        choices = oracle.candidates(history)
        choice = min(choices, key=lambda c: (-c.weight, c.raw))
        history.append(choice.token_id)
        suffix.extend(choice.raw)
    # A bounded, deterministic fallback; it carries no additional payload.
    return bytes(suffix) + b"."


def report(progress, count, interval, target=None):
    if progress and (count == 1 or count % 25 == 0):
        progress({"tokens": count, "bits": round(interval.information_bits(), 1),
                  "target_bits": target})


def encode(data: bytes, material: bytes, oracle, max_tokens=5000, progress=None):
    started = time.monotonic()
    encryption_key, order_key = derive_keys(material)
    frame = seal(data, encryption_key)
    # Finite random interior point: exact recovery, with 128 bits of random tail.
    point_num = ((int.from_bytes(frame, "big") << 128) | secrets.randbits(128)) * 2 + 1
    point_den = 1 << (len(frame) * 8 + 129)
    interval, history, parts = Interval(), [], []
    for count in range(1, max_tokens + 1):
        entries, ends = table(oracle.candidates(history), order_key, history)
        index = interval.choose(point_num, point_den, ends)
        choice, frequency = entries[index]
        interval.advance(0 if index == 0 else ends[index - 1], frequency)
        parts.append(choice.raw)
        history.append(choice.token_id)
        report(progress, count, interval, len(frame) * 8)
        if interval.common_bytes(len(frame)) == frame:
            cover = b"".join(parts)
            payload_tokens = len(history)
            cover += finish(oracle, history, cover)
            return cover, {
                "plaintext_bytes": len(data), "frame_bytes": len(frame),
                "cover_bytes": len(cover), "payload_tokens": payload_tokens,
                "total_tokens": len(history), "model_calls": oracle.calls,
                "average_retained_probability_mass": oracle.mass_sum / oracle.calls,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
    raise CodecError(f"Encoding exceeded {max_tokens} tokens; no cover file was written.")


def decode(cover: bytes, material: bytes, oracle, max_tokens=5000, progress=None):
    started = time.monotonic()
    encryption_key, order_key = derive_keys(material)
    interval, history, offset, next_size = Interval(), [], 0, BLOCK
    for count in range(1, max_tokens + 1):
        if offset >= len(cover):
            break
        entries, ends = table(oracle.candidates(history), order_key, history)
        matches = [i for i, (item, _) in enumerate(entries) if cover.startswith(item.raw, offset)]
        if len(matches) != 1:
            raise CodecError(f"Cover does not match the shared model at byte {offset}; "
                             "text was changed or the inference configuration differs.")
        index = matches[0]
        choice, frequency = entries[index]
        interval.advance(0 if index == 0 else ends[index - 1], frequency)
        offset += len(choice.raw)
        history.append(choice.token_id)
        report(progress, count, interval)
        while next_size <= MAX_FRAME:
            frame = interval.common_bytes(next_size)
            if frame is None:
                break
            try:
                plaintext = unseal(frame, encryption_key)
            except InvalidTag:
                next_size += BLOCK
                continue
            payload_tokens = len(history)
            expected_suffix = finish(oracle, history, cover[:offset])
            if cover[offset:] != expected_suffix:
                raise CodecError("Cover has an altered, missing, or extra sentence-completion suffix.")
            return plaintext, {
                "plaintext_bytes": len(plaintext), "frame_bytes": next_size,
                "cover_bytes": len(cover), "payload_tokens": payload_tokens,
                "total_tokens": len(history), "model_calls": oracle.calls,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "authenticated": True,
            }
    raise CodecError("No authenticated message recovered: wrong key, changed/truncated cover, "
                     "or incompatible inference configuration.")


@contextlib.contextmanager
def server_lock(url):
    name = hashlib.sha256(url.encode()).hexdigest()[:20]
    with open(Path(tempfile.gettempdir()) / f"p2p-poc-{name}.lock", "a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def locate_server() -> Path:
    override = os.environ.get("P2P_LLAMA_SERVER")
    choices = [Path(override)] if override else []
    found = shutil.which("llama-server")
    if found:
        choices.append(Path(found))
    choices.append(Path.home() / "Applications/ollama/lib/ollama/llama-server")
    ollama = shutil.which("ollama")
    if ollama:
        root = Path(ollama).resolve().parent
        choices.extend([root / "lib/ollama/llama-server", root.parent / "lib/ollama/llama-server"])
    for candidate in choices:
        if candidate.is_file():
            return candidate
    raise CodecError("Set P2P_LLAMA_SERVER to the llama-server executable.")


def serve(args):
    models = Path(os.environ.get("OLLAMA_MODELS", str(Path.home() / ".ollama/models")))
    model = models / "blobs" / ("sha256-" + MODEL_SHA)
    if not model.is_file():
        raise CodecError(f"Missing pinned model. Run: ollama pull {MODEL}")
    command = [str(locate_server()), "--model", str(model), "--host", "127.0.0.1",
               "--port", str(args.port), "--offline", "--no-webui", "--no-cache-prompt",
               "--no-cache-idle-slots", "--cache-ram", "0", "--parallel", "1",
               "--ctx-size", "2048", "--batch-size", "2048", "--ubatch-size", "2048",
               "--flash-attn", "off", "--gpu-layers", "0", "--threads", "4",
               "--log-verbosity", "1"]
    print("Starting dedicated CPU server; keep this terminal open.", file=sys.stderr)
    os.execv(command[0], command)


def probe(url, cold=False):
    sequences = []
    for _ in range(2):
        oracle, history, sequence = Llama(url, cold), [], []
        for step in range(12):
            choices = oracle.candidates(history)
            sequence.append([(c.token_id, c.raw.hex(), str(c.weight)) for c in choices])
            ranked = sorted(choices, key=lambda c: (-c.weight, c.raw))
            history.append(ranked[step % min(3, len(ranked))].token_id)
        sequences.append(sequence)
    equal = sequences[0] == sequences[1]
    if not equal:
        raise CodecError("The inference profile failed exact replay. Try --cold to disable cache reuse.")
    return {"exact_replay": True, "steps": 12, "repetitions": 2,
            "model": MODEL, "model_sha256": MODEL_SHA, "build": oracle.build,
            "cold": cold}


def write_new(path: str, content: bytes):
    target = Path(path)
    with target.open("xb") as handle:
        handle.write(content)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    server = commands.add_parser("serve", help="Run a dedicated server with the downloaded Ollama GGUF.")
    server.add_argument("--port", type=int, default=11535)
    for action in ("encode", "decode", "probe"):
        cmd = commands.add_parser(action)
        cmd.add_argument("--url", default=DEFAULT_URL)
        cmd.add_argument("--cold", action="store_true", help="Recompute every prompt without cache reuse.")
        if action != "probe":
            cmd.add_argument("--key", required=True)
            cmd.add_argument("--input", required=True)
            cmd.add_argument("--output", required=True)
            cmd.add_argument("--stats")
            cmd.add_argument("--max-tokens", type=int, default=5000)
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            serve(args)
            return 0
        with server_lock(args.url):
            if args.command == "probe":
                print(json.dumps(probe(args.url, args.cold), indent=2))
                return 0
            if Path(args.output).exists() or (args.stats and Path(args.stats).exists()):
                raise CodecError("Output or statistics file already exists; choose a new path.")
            data, material = Path(args.input).read_bytes(), Path(args.key).read_bytes()
            oracle = Llama(args.url, args.cold)
            operation = encode if args.command == "encode" else decode
            output, stats = operation(data, material, oracle, args.max_tokens,
                                      lambda row: print(json.dumps(row), file=sys.stderr, flush=True))
            write_new(args.output, output)
            stats.update({"model": MODEL, "model_sha256": MODEL_SHA,
                          "server_build": oracle.build, "cold": args.cold,
                          "key_sha256": hashlib.sha256(material).hexdigest()})
            if args.stats:
                write_new(args.stats, (json.dumps(stats, indent=2) + "\n").encode())
            print(json.dumps(stats, indent=2), file=sys.stderr)
        return 0
    except (CodecError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
