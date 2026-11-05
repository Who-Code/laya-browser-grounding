"""Laya Pilot: local dashboard + Playwright-driven Chrome + Laya-MLX decisions."""
from __future__ import annotations
import argparse, asyncio, json, pathlib, webbrowser
from aiohttp import web, WSMsgType
from playwright.async_api import async_playwright

import helpcenter
from agents import play_game, pursue_goal
from brain import Brain, DEFAULT_MODEL

HERE = pathlib.Path(__file__).parent


class App:
    def __init__(self, port: int, model: str):
        self.port, self.base = port, f"http://127.0.0.1:{port}"
        self.brain = Brain(model)
        self.clients: set[web.WebSocketResponse] = set()
        self.task: asyncio.Task | None = None
        self.pw = self.browser = self.page = None
        self.status = {"type": "status", "state": "loading", "model": model}

    def emit(self, msg: dict):
        self.status = msg if msg["type"] == "status" else self.status
        data = json.dumps(msg)
        for ws in list(self.clients):
            asyncio.ensure_future(ws.send_str(data))

    async def ensure_page(self):
        if self.page is None or self.page.is_closed():
            if self.browser is None or not self.browser.is_connected():
                self.pw = self.pw or await async_playwright().start()
                self.browser = await self.pw.chromium.launch(channel="chrome", headless=False)
            ctx = await self.browser.new_context(viewport={"width": 1000, "height": 760})
            self.page = await ctx.new_page()
        await self.page.bring_to_front()
        return self.page

    async def run(self, cfg: dict):
        try:
            page = await self.ensure_page()
            self.emit({"type": "status", "state": "running", "mode": cfg["mode"]})
            self.brain.latencies_ms.clear()
            if cfg["mode"] == "game":
                await play_game(page, self.brain, self.emit, self.base, cfg.get("level", "fast"),
                                int(cfg.get("duration", 30)), int(cfg.get("seed", 7)))
            elif cfg["mode"] == "human":
                await page.goto(f"{self.base}/game?level={cfg.get('level','fast')}&duration={cfg.get('duration',30)}&seed={cfg.get('seed',7)}")
                self.emit({"type": "note", "text": "Your turn: play in the Chrome window (keys 1/2/3). Same seed as the bot, so scores are comparable."})
            else:
                url = cfg.get("url") or f"{self.base}/help"
                await pursue_goal(page, self.brain, self.emit, url, cfg["goal"])
        except asyncio.CancelledError:
            self.emit({"type": "note", "text": "Stopped."}); raise
        except Exception as e:  # surface to the UI instead of dying silently
            self.emit({"type": "error", "text": f"{type(e).__name__}: {e}"})
        finally:
            self.emit({"type": "stats", **self.brain.stats()})
            self.emit({"type": "status", "state": "ready", "model": self.brain.repo})

    # -- HTTP handlers ---------------------------------------------------------------
    async def ws(self, req):
        ws = web.WebSocketResponse(); await ws.prepare(req); self.clients.add(ws)
        await ws.send_str(json.dumps(self.status))
        async for m in ws:
            if m.type == WSMsgType.TEXT:
                cfg = json.loads(m.data)
                if cfg.get("cmd") == "stop" and self.task:
                    self.task.cancel()
                elif cfg.get("cmd") == "start" and (not self.task or self.task.done()) and self.status.get("state") == "ready":
                    self.task = asyncio.create_task(self.run(cfg))
        self.clients.discard(ws); return ws

    async def boot(self, app):
        async def load():
            await self.brain.start()
            self.emit({"type": "status", "state": "ready", "model": self.brain.repo, "load_s": round(self.brain.load_s, 2)})
        app["load"] = asyncio.create_task(load())

    async def shutdown(self, app):
        if self.browser: await self.browser.close()
        if self.pw: await self.pw.stop()


def make_app(a: App) -> web.Application:
    app = web.Application()
    page = lambda f: (lambda r: web.FileResponse(HERE / "static" / f))
    app.add_routes([
        web.get("/", page("dashboard.html")), web.get("/game", page("game.html")), web.get("/ws", a.ws),
        web.get("/help", lambda r: web.Response(text=helpcenter.home(), content_type="text/html")),
        web.get("/help/{slug}", lambda r: web.Response(text=helpcenter.article(r.match_info["slug"]) or "not found",
                                                       content_type="text/html")),
        web.static("/static", HERE / "static"),
    ])
    app.on_startup.append(a.boot); app.on_cleanup.append(a.shutdown)
    return app


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--model", default=DEFAULT_MODEL); ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()
    a = App(args.port, args.model)
    if not args.no_open:
        asyncio.get_event_loop_policy()  # noqa
        import threading; threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}/")).start()
    web.run_app(make_app(a), host="127.0.0.1", port=args.port, print=lambda *_: print(f"Laya Pilot -> http://127.0.0.1:{args.port}"))
