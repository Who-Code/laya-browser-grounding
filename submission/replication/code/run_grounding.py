"""Replay every logged (instruction, candidate list, gold) case through all grounders. Pass 1 = accuracy + cold latency,
pass 2 = warm latency (compiled shapes / loaded Ollama models)."""
import asyncio, json, os, sys, time
from pilot import *
R = os.path.join(os.path.dirname(__file__), "results")

def load_cases():
    cases = []
    for f, flt in (("todo.json", lambda c: True), ("shop.json", lambda c: c["suite"].endswith("all-frames")), ("live.json", lambda c: True)):
        for c in json.load(open(os.path.join(R, f)))["cases"]:
            if flt(c) and c["gold"]: cases.append(c)
    return cases

async def main(only):
    """Each grounder runs alone in its own process so timings are not distorted by co-resident models."""
    from brain import Brain
    cases = load_cases(); print(len(cases), "cases", file=sys.stderr)
    brains = {"ml": "aac6fef/laya-multilingual-mlx", "td": "aac6fef/laya-typed-decisions-mlx"}
    need = {"laya-ml-choice": "ml", "laya-td-choice": "td", "laya-td-pointwise": "td"}.get(only)
    b = None
    if need: b = Brain(brains[need]); await b.start()
    make = {"laya-ml-choice": lambda: LayaGrounder(b, "laya-ml-choice"), "laya-td-choice": lambda: LayaGrounder(b, "laya-td-choice"),
            "laya-td-pointwise": lambda: PointwiseLayaGrounder(b, "laya-td-pointwise"), "lexical": LexicalGrounder, "embed(bge-m3)": EmbedGrounder,
            "llm(qwen3:8b)": lambda: LLMGrounder("qwen3:8b")}
    grounders = [make[only]()]
    out = {}
    for g in grounders:
        rows = []
        for passno in (1, 2):
            for k, c in enumerate(cases):
                cands = [Cand(**x) for x in c["cands"]]
                r = await g.pick(c["instruction"], cands)
                if passno == 1:
                    rows.append({"suite": c["suite"], "style": c["style"], "step": c["step"], "n": len(cands), "idx": r["idx"], "p": r["p"], "ms1": r["ms"],
                                 "ok": r["idx"] in c["gold"]})
                else: rows[k]["ms2"] = r["ms"]
        out[g.name] = rows
        acc = sum(r["ok"] for r in rows) / len(rows)
        ms = sorted(r["ms2"] for r in rows)
        print(f"{g.name:22s} acc {acc:.3f}  warm p50 {ms[len(ms)//2]:.1f} ms  p95 {ms[int(.95*(len(ms)-1))]:.1f} ms", file=sys.stderr, flush=True)
    json.dump(out, open(os.path.join(R, f"grounding_{only}.json"), "w"))

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
