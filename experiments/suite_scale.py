"""Scaling experiments. (a) candidate-list size on a live Wikipedia article, (b) batch throughput, (c) compile/cache settings."""
import asyncio, json, os, random, statistics, sys, time
from dataclasses import asdict
from playwright.async_api import async_playwright
from pilot import *
R = os.path.join(os.path.dirname(__file__), "results")

TARGETS = [  # (href, literal instruction, natural instruction)
 ("/wiki/Turing_machine", "Open the 'Turing machine' article", "Open the article about the abstract device he used to formalise computation"),
 ("/wiki/Enigma_machine", "Open the 'Enigma machine' article", "Open the article about the German cipher machine that was broken"),
 ("/wiki/Bletchley_Park", "Open the 'Bletchley Park' article", "Open the page about the wartime codebreaking centre in Buckinghamshire"),
 ("/wiki/Turing_test", "Open the 'Turing test' article", "Open the page about the imitation game for judging machine intelligence"),
 ("/wiki/Alonzo_Church", "Open the 'Alonzo Church' article", "Open the page about his doctoral supervisor at Princeton"),
]

class HybridGrounder:
    """lexical shortlist (top-K) then Laya choice on the shortlist"""
    def __init__(self, brain, k=15, tag=None): self.lex = LexicalGrounder(); self.laya = LayaGrounder(brain); self.k = k; self.name = tag or f"hybrid(lex{k}->laya)"
    async def pick(self, instruction, cands):
        t = time.perf_counter(); q = toks(instruction)
        sc = [sum(1 for w in set(q) if w in toks(c.text)) for c in cands]
        top = sorted(range(len(cands)), key=lambda i: -sc[i])[: self.k]
        r = await self.laya.pick(instruction, [cands[i] for i in top])
        return {"idx": top[r["idx"]] if r["idx"] is not None else None, "p": r["p"], "ms": (time.perf_counter() - t) * 1000}

async def wiki_cands():
    path = os.path.join(R, "wiki_cands.json")
    if os.path.exists(path): return [Cand(**x) for x in json.load(open(path))]
    async with async_playwright() as pw:
        br = await pw.chromium.launch(channel="chrome", headless=True); page = await br.new_page()
        await page.goto("https://en.wikipedia.org/wiki/Alan_Turing", wait_until="domcontentloaded")
        c = await Pilot(page).snapshot(); await br.close()
    json.dump([asdict(x) for x in c], open(path, "w")); return c

async def part_a(ml, td, which):
    allc = await wiki_cands()
    # one candidate per unique href, with duplicates by name removed so the gold is unambiguous
    seen, pool = set(), []
    for c in allc:
        c.href = c.href.replace("https://en.wikipedia.org", "")
        if c.href and c.href.startswith("/wiki/") and ":" not in c.href and len(c.name) > 2 and not c.name.startswith('[') and c.href not in seen and c.name not in {p.name for p in pool}:
            seen.add(c.href); pool.append(c)
    print("wiki pool", len(pool), "of", len(allc), file=sys.stderr)
    hrefs = {c.href: c for c in pool}; missing = [t[0] for t in TARGETS if t[0] not in hrefs]; print("missing targets", missing, file=sys.stderr)
    grounders = ([LayaGrounder(ml, "laya-ml-choice"), LayaGrounder(td, "laya-td-choice"), LexicalGrounder(), HybridGrounder(ml, 15, "hybrid(lex15->laya-ml)")]
                 if which == "laya" else [EmbedGrounder(), LLMGrounder("qwen3:8b")])
    rows = []
    for N in (5, 10, 20, 40, 80, 160):
        for g in grounders:
            ok = tot = errs = 0; ms = []; lasterr = ""; oks = {"literal": 0, "natural": 0}; tots = {"literal": 0, "natural": 0}
            for href, lit, nat in TARGETS:
                if href not in hrefs: continue
                for style, instr in (("literal", lit), ("natural", nat)):
                    for seed in range(3):
                        rnd = random.Random(f"{N}-{href}-{seed}")
                        others = rnd.sample([c for c in pool if c.href != href], min(N - 1, len(pool) - 1))
                        cands = others + [hrefs[href]]; rnd.shuffle(cands)
                        try: r = await g.pick(instr, cands)
                        except Exception as e: r = {"idx": None, "ms": float("nan")}; errs += 1; lasterr = f"{type(e).__name__}: {e}"
                        hit = int(cands[r["idx"]].href == href) if r["idx"] is not None else 0
                        ok += hit; tot += 1; ms.append(r["ms"]); oks[style] += hit; tots[style] += 1
            ms = [m for m in ms if m == m] or [float("nan")]
            rows.append({"N": N, "grounder": g.name, "acc": ok / tot, "n": tot, "acc_literal": oks["literal"] / tots["literal"], "acc_natural": oks["natural"] / tots["natural"], "pool": len(pool), "errors": errs, "lasterr": lasterr, "p50": statistics.median(ms), "p95": sorted(ms)[int(.95 * (len(ms) - 1))]})
            print(rows[-1], file=sys.stderr, flush=True)
    return rows

async def part_b():
    from brain import Brain
    import laya_mlx as laya
    out = []
    cases = json.load(open(os.path.join(R, "todo.json")))["cases"]
    labels_list = [uniq_labels([Cand(**x) for x in c["cands"]]) for c in cases]
    for cfg_name, kw in (("default", {}), ("compile", {"compile": True}), ("compile+pad16", {"compile": True, "pad_to_multiple": 16}),
                         ("compile+pad16+cache", {"compile": True, "pad_to_multiple": 16, "cache_prompts": True})):
        b = Brain(); b._agent = None
        def load(): b._agent = laya.load("aac6fef/laya-multilingual-mlx", **kw)
        await asyncio.get_running_loop().run_in_executor(b._pool, load)
        lat = []
        for k in range(len(cases)):
            _, ms = await b.choose([cases[k]["instruction"]], labels_list[k], Q); lat.append(ms)
        warm = []
        for k in range(len(cases)):
            _, ms = await b.choose([cases[k]["instruction"]], labels_list[k], Q); warm.append(ms)
        out.append({"cfg": cfg_name, "first_pass_p50": statistics.median(lat), "first_pass_p95": sorted(lat)[int(.95 * (len(lat) - 1))], "first_pass_max": max(lat),
                    "second_pass_p50": statistics.median(warm), "second_pass_p95": sorted(warm)[int(.95 * (len(warm) - 1))], "n": len(lat)})
        print(out[-1], file=sys.stderr, flush=True)
    # batch throughput (same question, B states) with the fastest config
    b = Brain(); 
    def load2(): b._agent = laya.load("aac6fef/laya-multilingual-mlx", compile=True, pad_to_multiple=16, cache_prompts=True)
    await asyncio.get_running_loop().run_in_executor(b._pool, load2)
    opts = {"billing": "Payments, invoices, refunds.", "technical": "Bugs and outages.", "sales": "Pricing and demos."}
    msgs = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "static", "messages.json"))); texts = [t for v in msgs.values() for t in v]
    thr = []
    for B in (1, 4, 16, 64):
        batch = (texts * 4)[:B]
        for _ in range(3): await b.choose(batch, opts, "Which department should handle this message?")
        ts = []
        for _ in range(10): _, ms = await b.choose(batch, opts, "Which department should handle this message?"); ts.append(ms)
        m = statistics.median(ts); thr.append({"batch": B, "p50_ms": m, "decisions_per_s": B / (m / 1000)})
        print(thr[-1], file=sys.stderr, flush=True)
    return out, thr

def memstate():
    import subprocess
    sw = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True).stdout.strip()
    mp = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout.strip().splitlines()[-1]
    return {"swap": sw, "mem": mp}

async def pools():
    allc = await wiki_cands(); seen, pool = set(), []
    for c in allc:
        c.href = c.href.replace("https://en.wikipedia.org", "")
        if c.href and c.href.startswith("/wiki/") and ":" not in c.href and len(c.name) > 2 and not c.name.startswith('[') and c.href not in seen and c.name not in {p.name for p in pool}:
            seen.add(c.href); pool.append(c)
    return pool, {c.href: c for c in pool}

async def lat_vs_n(grounder, tag):
    """isolated latency vs candidate count: 15 fixed trials per N, two passes (cold then warm)."""
    pool, hrefs = await pools(); rows = []
    for N in (5, 10, 20, 40, 80, 160):
        trials = []
        for href, lit, nat in TARGETS:
            for seed in range(3):
                rnd = random.Random(f"{N}-{href}-{seed}"); others = rnd.sample([c for c in pool if c.href != href], N - 1)
                cands = others + [hrefs[href]]; rnd.shuffle(cands); trials.append((lit, cands))
        p1 = [(await grounder.pick(i, c))["ms"] for i, c in trials]; p2 = [(await grounder.pick(i, c))["ms"] for i, c in trials]
        rows.append({"grounder": tag, "N": N, "cold_p50": statistics.median(p1), "cold_max": max(p1), "warm_p50": statistics.median(p2), "warm_p95": sorted(p2)[int(.95 * (len(p2) - 1))]})
        print(rows[-1], file=sys.stderr, flush=True)
    return rows

async def main(mode):
    from brain import Brain
    res = {"mode": mode, "env_before": memstate()}
    if mode in ("acc-laya", "acc-ollama"):
        ml = td = None
        if mode == "acc-laya":
            ml, td = Brain("aac6fef/laya-multilingual-mlx"), Brain("aac6fef/laya-typed-decisions-mlx"); await ml.start(); await td.start()
        res["candidates"] = await part_a(ml, td, mode.split("-")[1])
    elif mode == "lat-laya":
        res["lat"] = []
        for tag, repo in (("laya-ml-choice", "aac6fef/laya-multilingual-mlx"), ("laya-td-choice", "aac6fef/laya-typed-decisions-mlx")):
            b = Brain(repo); await b.start(); res["lat"] += await lat_vs_n(LayaGrounder(b, tag), tag); b._pool.shutdown()
    elif mode == "lat-ollama":
        res["lat"] = await lat_vs_n(EmbedGrounder(), "embed(bge-m3)") + await lat_vs_n(LLMGrounder("qwen3:8b"), "llm(qwen3:8b)")
    elif mode == "runtime":
        res["compile"], res["throughput"] = await part_b()
    res["env_after"] = memstate()
    json.dump(res, open(os.path.join(R, f"scale_{mode}.json"), "w"))
if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
