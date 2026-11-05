"""E2E suite 2: checkout flow with payment form in same-origin / cross-origin / nested iframes, open & closed shadow DOM,
and a canvas-drawn button. Laya-driven pilot with frame-aware vs main-frame-only snapshots."""
import asyncio, json, os, time
from dataclasses import asdict
from playwright.async_api import async_playwright
from pilot import Pilot, LayaGrounder

BASE = "http://127.0.0.1:8801/shop"
CONDITIONS = [("none", "plain"), ("same", "plain"), ("cross", "plain"), ("nested", "plain"),
              ("none", "shadow-open"), ("same", "shadow-open"), ("cross", "shadow-open"),
              ("none", "shadow-closed"), ("cross", "shadow-closed"), ("none", "canvas"), ("cross", "canvas")]
STEPS = [
 ("add_blue", "Add the blue mug to the cart", "add-blue", lambda s: s["cart"] == ["Blue mug"]),
 ("checkout", "Go to checkout", "checkout", lambda s: s["stage"] == "checkout"),
 ("holder",   "Enter 'Ada Lovelace' as the cardholder name", "holder", lambda s: s["fields"].get("holder") == "Ada Lovelace"),
 ("cardno",   "Type '1234 5678 9012 3456' into the card number field", "cardno", lambda s: s["fields"].get("cardno") == "1234 5678 9012 3456"),
 ("country",  "Choose Germany as the country", "country", lambda s: s["fields"].get("country") == "Germany"),
 ("pay",      "Pay now", "pay", lambda s: s["stage"] == "done" and (s["order"] or {}).get("country") == "Germany"),
]

async def run_flow(page, brain, frame_mode, cond):
    fr, m = cond
    pilot = Pilot(page); laya = LayaGrounder(brain); rows, cases = [], []
    await page.goto(f"{BASE}?frame={fr}&m={m}")
    async def opt_picker(instr, opts):
        (r,), _ = await brain.choose([instr], {o: o for o in opts}, "Which option should be selected?"); return r["choice"]
    reached = True
    for key, instr, gold, check in STEPS:
        if key in ("holder",): await page.wait_for_timeout(500)           # iframe load
        cands = []
        for attempt in range(8):                                            # wait until the gold control exists (iframe may still load)
            cands = await pilot.snapshot(main_only=(frame_mode == "main-only"))
            if any(c.gt == gold for c in cands) or attempt == 7: break
            await page.wait_for_timeout(250)
        goldi = [k for k, c in enumerate(cands) if c.gt == gold]
        t0 = time.perf_counter(); err = None; pk = {"idx": None, "p": 0, "ms": 0}
        if not cands: err = "empty-snapshot"
        else:
            pk = await laya.pick(instr, cands)
            cases.append({"suite": f"shop-{fr}-{m}-{frame_mode}", "style": "natural", "step": key, "instruction": instr, "gold": goldi, "cands": [asdict(c) for c in cands]})
            try: await pilot.act(cands[pk["idx"]], instr, opt_picker)
            except Exception as e: err = type(e).__name__
        await page.wait_for_timeout(60)
        st = await page.evaluate("window.__shop()"); ok = err is None and bool(check(st))
        rows.append({"cond": f"{fr}/{m}", "frame_mode": frame_mode, "step": key, "ok": ok, "err": err, "gold_visible": bool(goldi),
                     "picked_gold": pk["idx"] in goldi if pk["idx"] is not None else False, "ms": (time.perf_counter() - t0) * 1000 + pilot.snap_ms * 0, "ground_ms": pk["ms"], "snap_ms": pilot.snap_ms,
                     "ncands": len(cands), "nframes": len(page.frames)})
        if not ok:   # resync with the gold element so later steps are still measured independently
            if not goldi: break                                              # control unreachable: flow cannot continue
            try: await pilot.act(cands[goldi[0]], instr, lambda i, o: asyncio.sleep(0, "Germany"))
            except Exception: break
            await page.wait_for_timeout(60)
    return rows, cases

async def main(brain):
    rows, cases = [], []
    async with async_playwright() as pw:
        br = await pw.chromium.launch(channel="chrome", headless=True)
        for cond in CONDITIONS:
            for frame_mode in ("all-frames", "main-only"):
                if frame_mode == "main-only" and cond[0] == "none" and cond[1] == "plain": pass
                page = await (await br.new_context(viewport={"width": 900, "height": 900})).new_page()
                r, c = await run_flow(page, brain, frame_mode, cond); rows += r; cases += c; await page.close()
        await br.close()
    json.dump({"results": rows, "cases": cases}, open(os.path.join(os.path.dirname(__file__), "results", "shop.json"), "w"))
    return rows

if __name__ == "__main__":
    from brain import Brain
    async def run():
        b = Brain(); await b.start(); rows = await main(b)
        import collections; agg = collections.defaultdict(lambda: [0, 0, 0])
        for r in rows: a = agg[(r["cond"], r["frame_mode"])]; a[0] += r["ok"]; a[1] += 1; a[2] += r["picked_gold"]
        for k, v in agg.items(): print(k, f"steps ok {v[0]}/6 (reached {v[1]}), picked-gold {v[2]}")
    asyncio.run(run())
