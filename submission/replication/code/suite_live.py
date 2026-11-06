"""Live suites: public practice sites (the-internet.herokuapp.com) and a third-party app (TodoMVC React).
Instruction-driven runs with Laya grounding; oracle resync after a failed step so each step is measured independently."""
import asyncio, json, os, time
from dataclasses import asdict
from playwright.async_api import async_playwright
from pilot import Pilot, LayaGrounder

I = "https://the-internet.herokuapp.com"
async def wait_for(page, js, timeout=6.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if await page.evaluate(js): return True
        except Exception: pass
        await asyncio.sleep(0.1)
    return False

first = lambda role: (lambda cs: [k for k, c in enumerate(cs) if c.role == role][:1])
nth = lambda role, n: (lambda cs: [k for k, c in enumerate(cs) if c.role == role][n:n + 1])
named = lambda role, nm, ctx=None: (lambda cs: [k for k, c in enumerate(cs) if c.role == role and c.name.lower() == nm.lower() and (ctx is None or ctx in c.ctx)])

TASKS = [
 ("checkboxes", f"{I}/checkboxes", [
   ("Tick the first checkbox", nth("checkbox", 0), "document.querySelectorAll('#checkboxes input')[0].checked===true"),
   ("Untick the second checkbox", nth("checkbox", 1), "document.querySelectorAll('#checkboxes input')[1].checked===false")]),
 ("dropdown", f"{I}/dropdown", [
   ("Choose Option 2 from the dropdown list", first("combobox"), "document.querySelector('#dropdown').value==='2'")]),
 ("add_remove", f"{I}/add_remove_elements/", [
   ("Click Add Element", named("button", "Add Element"), "document.querySelectorAll('.added-manually').length===1"),
   ("Remove the element you just added", named("button", "Delete"), "document.querySelectorAll('.added-manually').length===0")]),
 ("dynamic_loading", f"{I}/dynamic_loading/1", [
   ("Start the loading process", named("button", "Start"), "document.querySelector('#finish')?.innerText.includes('Hello World!')")]),
 ("js_alerts", f"{I}/javascript_alerts", [
   ("Trigger the JS confirm dialog", named("button", "Click for JS Confirm"), "document.querySelector('#result')?.innerText==='You clicked: Ok'")]),
 ("inputs", f"{I}/inputs", [
   ("Type '42' into the number input", first("textbox"), "document.querySelector('input').value==='42'")]),
 ("status_codes", f"{I}/status_codes", [
   ("Open the page for status code 404", named("link", "404"), "location.pathname.endsWith('/404')")]),
 ("challenging_dom", f"{I}/challenging_dom", [
   ("Click the edit link in the table row for 'Iuvaret5'", named("link", "edit", "Iuvaret5"), "window.__last && window.__last.includes('Iuvaret5') && window.__lt==='edit'"),
   ("Click the delete link in the table row for 'Apeirian7'", named("link", "delete", "Apeirian7"), "window.__last && window.__last.includes('Apeirian7') && window.__lt==='delete'")]),
 ("tinymce_iframe", f"{I}/iframe", [
   ("Type 'Hello from Laya' into the text editor", lambda cs: [k for k, c in enumerate(cs) if c.frame > 0 and c.editable][:1],
    "(()=>{const f=document.querySelector('iframe');return f&&f.contentDocument.body.innerText.includes('Hello from Laya')})()")]),
 ("todomvc_react", "https://todomvc.com/examples/react/dist/", [
   ("Type 'Buy milk' into the new todo input and press Enter", first("textbox"), "document.querySelectorAll('.todo-list li').length===1"),
   ("Type 'Walk dog' into the new todo input and press Enter", first("textbox"), "document.querySelectorAll('.todo-list li').length===2"),
   ("Type 'Write report' into the new todo input and press Enter", first("textbox"), "document.querySelectorAll('.todo-list li').length===3"),
   ("Mark 'Walk dog' as done", lambda cs: [k for k, c in enumerate(cs) if c.role == "checkbox" and "walk dog" in (c.name + c.ctx).lower()], "[...document.querySelectorAll('li.completed')].map(l=>l.innerText.trim()).join()==='Walk dog'"),
   ("Show only the active items", named("link", "Active"), "document.querySelectorAll('.todo-list li').length===2"),
   ("Show only the finished items", named("link", "Completed"), "document.querySelectorAll('.todo-list li').length===1"),
   ("Clear the finished items", named("button", "Clear completed"), "document.querySelectorAll('.todo-list li').length===0 && document.querySelector('.todo-count').innerText.includes('2 items')")]),
]

async def main(brain):
    rows, cases = [], []
    async with async_playwright() as pw:
        br = await pw.chromium.launch(channel="chrome", headless=True)
        for name, url, steps in TASKS:
            page = await (await br.new_context(viewport={"width": 1100, "height": 800})).new_page()
            page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
            pilot = Pilot(page); laya = LayaGrounder(brain)
            async def opt_picker(instr, opts):
                (r,), _ = await brain.choose([instr], {o: o for o in opts}, "Which option should be selected?"); return r["choice"]
            try:
                await page.goto(url, wait_until="load", timeout=30000)
                if name == "challenging_dom":
                    await page.evaluate("document.addEventListener('click',e=>{window.__last=e.target.closest('tr')?.innerText;window.__lt=e.target.innerText.trim()},true)")
                await page.wait_for_timeout(800 if name == "tinymce_iframe" else 200)
            except Exception as e:
                rows.append({"task": name, "step": 0, "ok": False, "err": "load:" + type(e).__name__}); continue
            for si, (instr, goldf, check) in enumerate(steps):
                cands = await pilot.snapshot(); goldi = goldf(cands)
                t0 = time.perf_counter(); err = None; pk = {"idx": None, "p": 0, "ms": 0}
                if cands:
                    pk = await laya.pick(instr, cands)
                    cases.append({"suite": f"live-{name}", "style": "natural", "step": f"{name}:{si}", "instruction": instr, "gold": goldi, "cands": [asdict(c) for c in cands]})
                    try: await pilot.act(cands[pk["idx"]], instr, opt_picker)
                    except Exception as e: err = type(e).__name__
                else: err = "empty-snapshot"
                ok = err is None and await wait_for(page, check, 6.0)
                rows.append({"task": name, "step": si, "ok": bool(ok), "err": err, "gold_visible": bool(goldi), "picked_gold": (pk["idx"] in goldi) if pk["idx"] is not None else False,
                             "ms": (time.perf_counter() - t0) * 1000, "ground_ms": pk["ms"], "snap_ms": pilot.snap_ms, "ncands": len(cands), "instruction": instr})
                if not ok and goldi:
                    try: await pilot.act(cands[goldi[0]], instr, lambda i, o: asyncio.sleep(0, o[1] if len(o) > 1 else o[0])); await page.wait_for_timeout(300)
                    except Exception: pass
            await page.close()
        await br.close()
    json.dump({"results": rows, "cases": cases}, open(os.path.join(os.path.dirname(__file__), "results", "live.json"), "w"))
    return rows

if __name__ == "__main__":
    from brain import Brain
    async def run():
        b = Brain(); await b.start(); rows = await main(b)
        for r in rows: print(r["task"], r["step"], "OK " if r["ok"] else "FAIL", "gold_visible" if r.get("gold_visible") else "no-gold", r.get("err") or "", f'{r.get("ground_ms",0):.0f}ms n={r.get("ncands")}', r.get("instruction", "")[:50])
    asyncio.run(run())
