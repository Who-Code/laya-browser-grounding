"""Offline sanity check: how often does Laya route the game's messages correctly, and how fast?"""
import asyncio, json, pathlib, sys
from brain import Brain

from agents import TEAMS as OPTIONS, TEAM_Q as Q

async def main(repo):
    msgs = json.loads((pathlib.Path(__file__).parent / "static/messages.json").read_text())
    b = Brain(repo); await b.start()
    flat = [(t, k) for k, v in msgs.items() for t in v]
    out, ms = await b.choose([t for t, _ in flat], OPTIONS, Q)
    ok = sum(o["choice"] == k for o, (_, k) in zip(out, flat))
    print(f"{repo}: {ok}/{len(flat)} correct, batch of {len(flat)} in {ms:.1f} ms")
    for o, (t, k) in zip(out, flat):
        if o["choice"] != k: print("  MISS", k, "->", o["choice"], f"{o['p']:.2f}", t)
    singles = []
    for t, _ in flat[:12]:
        _, m = await b.choose([t], OPTIONS, Q); singles.append(m)
    singles.sort(); print(f"single-decision latency p50 {singles[len(singles)//2]:.1f} ms, max {singles[-1]:.1f} ms")

asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "aac6fef/laya-multilingual-mlx"))
