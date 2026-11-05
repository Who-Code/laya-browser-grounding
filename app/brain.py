"""Thin wrapper around laya-mlx: turns 'which option fits this text?' into one fast local call."""
from __future__ import annotations

import statistics
import time
from concurrent.futures import ThreadPoolExecutor
import asyncio

import laya_mlx as laya

DEFAULT_MODEL = "aac6fef/laya-multilingual-mlx"  # 322M, 1024 ctx, fastest checkpoint


class Brain:
    """Owns the model. MLX streams are per-thread, so everything runs on ONE worker thread."""

    def __init__(self, repo: str = DEFAULT_MODEL):
        self.repo = repo
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="laya")
        self._agent = None
        self.latencies_ms: list[float] = []

    # -- sync API (must run on the worker thread) ---------------------------------------
    def _load(self):
        t = time.perf_counter()
        self._agent = laya.load(self.repo, compile=True, pad_to_multiple=16, cache_prompts=True)
        self.load_s = time.perf_counter() - t

    def _choose(self, texts: list[str], options, question: str):
        qs = {"pick": {"type": "choice", "instructions": question, "criteria": options}}
        t = time.perf_counter()
        res = self._agent.predict_batch(texts, qs)
        ms = (time.perf_counter() - t) * 1000
        out = []
        for r in res:
            a = r["answers"]["pick"]
            probs = a.get("probabilities", {})
            label = a["choice"]
            out.append({"choice": label, "p": float(probs.get(label, a.get("answer_confidence", 0.0)))})
        return out, ms

    def _judge(self, text: str, question: str):
        qs = {"j": {"type": "noul", "instructions": question}}
        t = time.perf_counter()
        r = self._agent.predict(text, qs)
        ms = (time.perf_counter() - t) * 1000
        return float(r["answers"]["j"]["noul"]), ms

    def _judge_batch(self, states: list[str], question: str):
        qs = {"j": {"type": "noul", "instructions": question}}
        t = time.perf_counter()
        res = self._agent.predict_batch(states, qs)
        ms = (time.perf_counter() - t) * 1000
        return [float(r["answers"]["j"]["noul"]) for r in res], ms

    # -- async API ---------------------------------------------------------------------
    async def start(self):
        await asyncio.get_running_loop().run_in_executor(self._pool, self._load)
        # warm-up: first calls compile kernels
        for _ in range(3):
            await self.choose(["warm up"], {"a": "first", "b": "second"}, "Which?")
        self.latencies_ms.clear()

    async def choose(self, texts: list[str], options, question: str):
        out, ms = await asyncio.get_running_loop().run_in_executor(
            self._pool, self._choose, texts, options, question
        )
        self.latencies_ms.append(ms)
        return out, ms

    async def judge(self, text: str, question: str):
        p, ms = await asyncio.get_running_loop().run_in_executor(self._pool, self._judge, text, question)
        self.latencies_ms.append(ms)
        return p, ms

    async def judge_batch(self, states: list[str], question: str):
        out, ms = await asyncio.get_running_loop().run_in_executor(self._pool, self._judge_batch, states, question)
        self.latencies_ms.append(ms)
        return out, ms

    def stats(self):
        l = sorted(self.latencies_ms)
        if not l:
            return {}
        return {"n": len(l), "p50": statistics.median(l), "p95": l[int(0.95 * (len(l) - 1))], "max": l[-1]}
