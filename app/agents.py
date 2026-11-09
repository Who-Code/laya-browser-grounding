"""Browser agents. Each observes the page, asks Laya a narrow typed question, then acts."""
from __future__ import annotations
import asyncio, time
from playwright.async_api import Page

TEAMS = {
    "billing": "Payments, invoices, refunds, charges and receipts.",
    "technical": "Bugs, crashes, errors, outages and broken features.",
    "sales": "Pricing, plan costs, discounts, quotes, demos, upgrades and buying licenses.",
}
TEAM_Q = "Which department should handle this customer message?"

GAME_SNAPSHOT = """() => ({
  s: window.__score ? window.__score() : null,
  cards: [...document.querySelectorAll('.card:not(.ok):not(.bad)')].map(c => ({id: +c.dataset.id, text: c.textContent, y: c.getBoundingClientRect().top})),
  bins: Object.fromEntries([...document.querySelectorAll('.bin')].map(b => {const r = b.getBoundingClientRect(); return [b.dataset.team, [r.x + r.width/2, r.y + r.height/2]]}))
})"""


async def play_game(page: Page, brain, emit, base: str, level: str, duration: int, seed: int):
    """Triage Rush: read falling cards from the DOM, route each with Laya, click the right bin."""
    await page.goto(f"{base}/game?level={level}&duration={duration}&seed={seed}")
    await page.wait_for_function("window.__ready === true")
    await page.click("#start")
    chosen: dict[int, dict] = {}   # card id -> decision (made as soon as a card is first seen)
    seen_at: dict[int, float] = {}
    n = 0
    while True:
        t_obs = time.perf_counter()
        snap = await page.evaluate(GAME_SNAPSHOT)
        if snap["s"]["over"]:
            break
        cards = snap["cards"]
        fresh = [c for c in cards if c["id"] not in chosen]
        for c in fresh:
            seen_at[c["id"]] = t_obs
        if fresh:   # one batched forward pass for every newly visible card
            outs, ms = await brain.choose([c["text"] for c in fresh], TEAMS, TEAM_Q)
            for c, o in zip(fresh, outs):
                chosen[c["id"]] = {**o, "ms": ms / len(fresh), "batch_ms": ms, "text": c["text"]}
        if cards:
            low = max(cards, key=lambda c: c["y"])           # the game resolves the lowest card
            d = chosen[low["id"]]
            x, y = snap["bins"][d["choice"]]
            await page.mouse.click(x, y)
            n += 1
            emit({"type": "decision", "n": n, "text": d["text"], "choice": d["choice"], "p": d["p"],
                  "laya_ms": d["batch_ms"], "seen_to_click_ms": (time.perf_counter() - seen_at[low["id"]]) * 1000,
                  "score": snap["s"]["score"]})
            chosen.pop(low["id"], None)
        else:
            await asyncio.sleep(0.02)   # idle poll: 50 Hz is plenty and keeps Chrome/Python CPU low
    final = await page.evaluate("window.__score()")
    emit({"type": "finished", "mode": "game", "result": final, "decisions": n})
    return final


SNAPSHOT_LINKS = """() => {
  const out = [], seen = new Set();
  for (const el of document.querySelectorAll('a[href], button, [role=button]')) {
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4 || r.bottom < 0 || r.top > innerHeight * 3) continue;
    const clean = t => (t || '').replace(/\\s+/g, ' ').trim();
    const desc = clean(el.getAttribute('aria-label') || el.innerText || el.title).slice(0, 160);
    const text = clean(el.querySelector('h1,h2,h3,h4,strong')?.innerText || desc).slice(0, 60);  // short label
    if (text.length < 3 || seen.has(text)) continue;
    seen.add(text); out.push({text, desc, href: el.href || '', x: r.x + r.width/2, y: r.y + r.height/2});
    if (out.length >= 30) break;
  }
  return out;
}"""
PAGE_SUMMARY = "() => (document.title + '. ' + (document.querySelector('h1')?.innerText || '') + '. ' + (document.querySelector('main, article, p')?.innerText || '')).slice(0, 700)"


async def safe_eval(page: Page, js: str, tries: int = 5):
    """page.evaluate that survives an in-flight navigation (retries once the new document is ready)."""
    for _ in range(tries):
        try:
            return await page.evaluate(js)
        except Exception as e:
            if "context was destroyed" not in str(e) and "navigat" not in str(e).lower():
                raise
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(0.05)
    return await page.evaluate(js)


async def pursue_goal(page: Page, brain, emit, url: str, goal: str, max_steps: int = 4):
    """Generic web agent: 'does this page satisfy the goal?' (yes/no), else 'which link?' (choice)."""
    await page.goto(url, wait_until="domcontentloaded")
    visited: set[str] = set()
    for step in range(1, max_steps + 1):
        summary = await safe_eval(page, PAGE_SUMMARY)
        p_done, ms_j = await brain.judge(summary, f"Is this page the right place for someone who says: '{goal}'?")
        emit({"type": "decision", "n": step * 2 - 1, "text": f"[on page] {await page.title()}", "choice": "done?" if p_done > .8 else "keep looking",
              "p": p_done, "laya_ms": ms_j, "seen_to_click_ms": ms_j})
        if p_done > 0.8 and step > 1:
            emit({"type": "finished", "mode": "web", "result": {"url": page.url, "title": await page.title()}, "decisions": step * 2 - 1})
            return True
        visited.add(page.url)
        links = [l for l in await safe_eval(page, SNAPSHOT_LINKS) if l["href"] not in visited]   # never loop back
        if not links:
            break
        (pick,), ms = await brain.choose([f"Goal: {goal}"], {l["text"]: l["desc"] for l in links}, "Which link should be clicked to accomplish the goal?")
        link = next(l for l in links if l["text"] == pick["choice"])
        emit({"type": "decision", "n": step * 2, "text": f"{len(links)} links on page", "choice": pick["choice"], "p": pick["p"],
              "laya_ms": ms, "seen_to_click_ms": ms})
        try:   # a click that navigates: wait for the new document; a click that doesn't just continues
            async with page.expect_navigation(wait_until="domcontentloaded", timeout=2500):
                await page.mouse.click(link["x"], link["y"])
        except Exception:
            pass
    emit({"type": "finished", "mode": "web", "result": {"url": page.url, "title": await page.title()}, "decisions": max_steps * 2})
    return False
