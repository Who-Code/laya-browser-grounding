"""E2E suite 1: todo app x 5 UI variants x 2 instruction styles, run by Laya-driven pilot vs two scripted Playwright styles."""
import asyncio, json, time, sys
from dataclasses import asdict
from playwright.async_api import async_playwright
from pilot import Pilot, LayaGrounder

BASE = "http://127.0.0.1:8801/todo?v="
S0 = {"todos": [{"text": "Buy milk", "done": False}, {"text": "Walk dog", "done": False}, {"text": "Write report", "done": False}], "filter": "all"}
def with_(**kw):
    import copy; s = copy.deepcopy(S0); s.update(kw); return s
def done(s, name): 
    import copy; s = copy.deepcopy(s)
    for t in s["todos"]:
        if t["text"] == name: t["done"] = True
    return s

STEPS = [  # key, literal instruction (written against variant A labels), natural instruction, pre-state, input, expected predicate, gold gt
 ("type",  "Type 'Call mom' into the What needs to be done? field", "Type 'Call mom' into the new task box", S0, "", lambda s: s["input"] == "Call mom" and len(s["todos"]) == 3, "input"),
 ("add",   "Click Add", "Submit the new task", S0, "Call mom", lambda s: [t["text"] for t in s["todos"]] == ["Buy milk", "Walk dog", "Write report", "Call mom"], "add"),
 ("toggle","Check the Walk dog checkbox", "Tick off 'Walk dog'", S0, "", lambda s: [t["text"] for t in s["todos"] if t["done"]] == ["Walk dog"], "toggle:Walk dog"),
 ("delete","Click Delete on Write report", "Get rid of the 'Write report' item", S0, "", lambda s: [t["text"] for t in s["todos"]] == ["Buy milk", "Walk dog"], "del:Write report"),
 ("f_active","Click the Active filter", "Show only the tasks that are still open", S0, "", lambda s: s["filter"] == "active", "f:active"),
 ("f_all", "Click the All filter", "Show every task again", with_(filter="active"), "", lambda s: s["filter"] == "all", "f:all"),
 ("clear", "Click Clear completed", "Remove all the finished tasks", done(S0, "Walk dog"), "", lambda s: [t["text"] for t in s["todos"]] == ["Buy milk", "Write report"], "clear"),
]

async def scripted(page, kind, key):
    """Scripted Playwright steps, authored once against variant A."""
    T = 900
    if kind == "css":
        sel = {"type": ("fill", "#new-todo"), "add": ("click", ".add-btn"), "toggle": ("click", 'li:has-text("Walk dog") .toggle'),
               "delete": ("click", 'li:has-text("Write report") .destroy'), "f_active": ("click", "[data-filter=active]"),
               "f_all": ("click", "[data-filter=all]"), "clear": ("click", ".clear-completed")}[key]
        loc = page.locator(sel[1])
    else:  # role / text based (Playwright best practice)
        r = page.get_by_role
        loc = {"type": page.get_by_placeholder("What needs to be done?"), "add": r("button", name="Add", exact=True),
               "toggle": page.get_by_role("listitem").filter(has_text="Walk dog").get_by_role("checkbox"), "delete": page.get_by_role("listitem").filter(has_text="Write report").get_by_role("button", name="Delete"),
               "f_active": r("button", name="Active"), "f_all": r("button", name="All", exact=True), "clear": r("button", name="Clear completed")}[key]
        sel = ("fill" if key == "type" else "click",)
    if sel[0] == "fill": await loc.fill("Call mom", timeout=T)
    else: await loc.click(timeout=T)

async def main(brain, out_path):
    results, cases = [], []
    async with async_playwright() as pw:
        br = await pw.chromium.launch(channel="chrome", headless=True)
        page = await (await br.new_context(viewport={"width": 900, "height": 700})).new_page()
        pilot = Pilot(page); laya = LayaGrounder(brain)
        async def opt_picker(instr, opts):
            labels = {o: o for o in opts}; (r,), _ = await brain.choose([instr], labels, "Which option should be selected?"); return r["choice"]
        for v in "ABCDE":
            await page.goto(BASE + v)
            for key, lit, nat, pre, inp, check, gold in STEPS:
                for style, instr in (("literal", lit), ("natural", nat)):
                    for runner in ("laya", "scripted-css", "scripted-role"):
                        await page.evaluate("([s, i]) => window.__reset(s, i)", [pre, inp])
                        t0 = time.perf_counter(); err = None; g_ms = 0.0
                        try:
                            if runner == "laya":
                                cands = await pilot.snapshot()
                                pk = await laya.pick(instr, cands); g_ms = pk["ms"]
                                if runner == "laya" and v and style:   # log the case once per (variant, step, style)
                                    cases.append({"suite": f"todo-{v}", "style": style, "step": key, "instruction": instr, "gold": [k for k, c in enumerate(cands) if c.gt == gold],
                                                  "cands": [asdict(c) for c in cands]})
                                if pk["idx"] is None: raise RuntimeError("no candidate")
                                await pilot.act(cands[pk["idx"]], instr, opt_picker)
                            else:
                                await scripted(page, runner.split("-")[1], key)
                        except Exception as e:
                            err = type(e).__name__
                        await page.wait_for_timeout(30)
                        st = await page.evaluate("window.__state()")
                        ok = err is None and bool(check(st))
                        results.append({"variant": v, "step": key, "style": style, "runner": runner, "ok": ok, "err": err,
                                        "ms": (time.perf_counter() - t0) * 1000, "ground_ms": g_ms})
        await br.close()
    json.dump({"results": results, "cases": cases}, open(out_path, "w"))
    return results

if __name__ == "__main__":
    from brain import Brain
    async def run():
        b = Brain(); await b.start()
        res = await main(b, __import__("os").path.join(__import__("os").path.dirname(__file__), "results", "todo.json"))
        import collections
        agg = collections.defaultdict(lambda: [0, 0])
        for r in res: a = agg[(r["runner"], r["variant"], r["style"])]; a[0] += r["ok"]; a[1] += 1
        for k, (o, n) in sorted(agg.items()): print(k, f"{o}/{n}")
    asyncio.run(run())
