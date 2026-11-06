"""Does Laya's first call after an idle gap cost more? (browser agents wait on page loads between decisions)"""
import asyncio, json, os, statistics, sys, time
from brain import Brain
OPTS = {"billing": "Payments, invoices, refunds.", "technical": "Bugs and outages.", "sales": "Pricing and demos."}
Q = "Which department should handle this message?"

async def main():
    b = Brain(); await b.start(); res = []
    for _ in range(10): await b.choose(["I was charged twice"], OPTS, Q)
    for idle in (0, 0.25, 0.5, 1, 2, 5, 10):
        ts = []
        for k in range(8):
            await b.choose([f"warm {k}"], OPTS, Q)
            await asyncio.sleep(idle)
            _, ms = await b.choose([f"The app crashes when I log in {k}"], OPTS, Q); ts.append(ms)
        res.append({"idle_s": idle, "p50": statistics.median(ts), "max": max(ts)}); print(res[-1], flush=True)
    # mitigation: background keep-alive ping every 100 ms during a 2 s idle
    ts = []
    for k in range(8):
        end = time.time() + 2
        while time.time() < end: await b.choose(["ping"], OPTS, Q); await asyncio.sleep(0.1)
        _, ms = await b.choose([f"The app crashes when I log in {k}"], OPTS, Q); ts.append(ms)
    res.append({"idle_s": "2 (with 10 Hz keep-alive)", "p50": statistics.median(ts), "max": max(ts)}); print(res[-1])
    json.dump(res, open(os.path.join(os.path.dirname(__file__), "results", "idle.json"), "w"))
if __name__ == "__main__":
    asyncio.run(main())
