"""Headless-client smoke test: talks to a running server over its WebSocket like the dashboard does."""
import asyncio, json, sys, statistics, aiohttp

async def run(cfg, port=8765):
    async with aiohttp.ClientSession() as s, s.ws_connect(f"http://127.0.0.1:{port}/ws") as ws:
        ready = False
        while not ready:
            m = json.loads((await ws.receive()).data); ready = m.get("state") == "ready"
        await ws.send_str(json.dumps({"cmd": "start", **cfg}))
        decs, fin = [], None
        async for msg in ws:
            m = json.loads(msg.data)
            if m["type"] == "decision": decs.append(m)
            elif m["type"] in ("finished", "error", "note"): print(m); fin = fin or m
            elif m["type"] == "status" and m["state"] == "ready" and fin: break
        if decs:
            l = [d["laya_ms"] for d in decs]; e = [d["seen_to_click_ms"] for d in decs]
            print(f"{len(decs)} decisions | laya median {statistics.median(l):.1f} ms | seen->click median {statistics.median(e):.1f} ms")
            for d in decs[:6]: print("  ", d["choice"], f"{d['p']:.2f}", d["text"][:60])

if __name__ == "__main__":
    asyncio.run(run(json.loads(sys.argv[1])))
