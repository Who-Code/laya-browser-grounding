"""Turn results/*.json into the markdown tables used in the paper (results/tables.md)."""
import json, math, os, statistics as st, collections
R = os.path.join(os.path.dirname(__file__), "results")
L = lambda f: json.load(open(os.path.join(R, f)))
out = []
def P(*a): out.append(" ".join(str(x) for x in a))
def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - w) / d, (c + w) / d)
def pct(k, n): lo, hi = wilson(k, n); return f"{100*k/n:.0f}% ({k}/{n}) [{100*lo:.0f}–{100*hi:.0f}]"
def table(head, rows):
    P("| " + " | ".join(head) + " |"); P("|" + "---|" * len(head))
    for r in rows: P("| " + " | ".join(str(x) for x in r) + " |")
    P()

# ---- T1: todo e2e
d = L("todo.json")["results"]
P("### T1. Todo app, step pass rate by runner and UI variant (7 steps x 2 instruction styles = 14 per cell)\n")
runners = ["scripted-css", "scripted-role", "laya"]
table(["Variant"] + runners, [[v] + [f"{sum(r['ok'] for r in d if r['variant']==v and r['runner']==rn)}/14" for rn in runners] for v in "ABCDE"])
P("Laya by instruction style:\n")
table(["Variant", "literal (7)", "natural (7)"], [[v] + [f"{sum(r['ok'] for r in d if r['variant']==v and r['runner']=='laya' and r['style']==s)}/7" for s in ("literal", "natural")] for v in "ABCDE"])
lay = [r for r in d if r["runner"] == "laya"]; scr = [r for r in d if r["runner"] != "laya"]
P(f"Step wall time (snapshot+Laya+act+settle): Laya median {st.median(r['ms'] for r in lay):.0f} ms, scripted median {st.median(r['ms'] for r in scr):.0f} ms; Laya ground-only median {st.median(r['ground_ms'] for r in lay):.1f} ms.\n")
P("Laya failures by step (all variants):", dict(collections.Counter(r["step"] for r in lay if not r["ok"])), "\n")

# ---- T2: shop
s = L("shop.json")["results"]
P("### T2. Checkout flow: steps completed (of 6) by frame condition and snapshot mode\n")
conds = list(dict.fromkeys(r["cond"] for r in s))
table(["Condition (frame/form)", "frame-aware snapshot", "main-frame-only snapshot"],
      [[c] + [f"{sum(r['ok'] for r in s if r['cond']==c and r['frame_mode']==m)}/6" for m in ("all-frames", "main-only")] for c in conds])
fa = [r for r in s if r["frame_mode"] == "all-frames" and r["ok"]]
P(f"Frame-aware: median snapshot {st.median(r['snap_ms'] for r in fa):.0f} ms, median Laya {st.median(r['ground_ms'] for r in fa):.0f} ms, median candidates {st.median(r['ncands'] for r in fa):.0f}.\n")

# ---- T3: live
v = L("live.json")["results"]
P("### T3. Live sites: step outcomes\n")
tasks = list(dict.fromkeys(r["task"] for r in v))
vv = [r for r in v if "ground_ms" in r]
table(["Task", "steps passed (last run)", "Laya picked gold", "median Laya ms", "candidates"], [[t, f"{sum(r['ok'] for r in v if r['task']==t)}/{sum(1 for r in v if r['task']==t)}", f"{sum(r['picked_gold'] for r in vv if r['task']==t)}/{sum(1 for r in vv if r['task']==t)}", (f"{st.median(r['ground_ms'] for r in vv if r['task']==t):.0f}" if any(r['task']==t for r in vv) else "n/a"), ",".join(str(r['ncands']) for r in vv if r['task']==t)] for t in tasks])
P(f"Last run: {sum(r['ok'] for r in v)}/{len(v)} steps passed end to end; Laya chose the gold element in {sum(r['picked_gold'] for r in vv)}/{len(vv)} decisions; median snapshot {st.median(r['snap_ms'] for r in vv):.0f} ms.\n")

# ---- T4: grounding
ORDER = ["laya-ml-choice", "laya-td-choice", "laya-td-pointwise", "lexical", "embed(bge-m3)", "llm(qwen3:8b)"]
g = {}
for n in ORDER: g.update(L(f"grounding_{n}.json"))
names = list(g)
def grp(r):
    sname = r["suite"]
    return "dev:todo-A" if sname == "todo-A" else "todo-B..E" if sname.startswith("todo-") else "shop(iframe/shadow)" if sname.startswith("shop") else "live"
NC = len(g["lexical"])
P(f"### T4. Element-grounding accuracy over all logged decisions ({NC} cases), 95% Wilson CI in brackets\n")
rows = []
for n in names:
    r = g[n]; ms = sorted(x["ms2"] for x in r)
    rows.append([n, pct(sum(x["ok"] for x in r), len(r)), f"{ms[len(ms)//2]:.1f}", f"{ms[int(.95*(len(ms)-1))]:.0f}"])
table(["Grounder", "Top-1 accuracy", "warm p50 ms", "warm p95 ms"], rows)
P("By suite group (top-1 correct / cases):\n")
groups = ["dev:todo-A", "todo-B..E", "shop(iframe/shadow)", "live"]
table(["Grounder"] + groups, [[n] + [f"{sum(x['ok'] for x in g[n] if grp(x)==gr)}/{sum(1 for x in g[n] if grp(x)==gr)}" for gr in groups] for n in names])
P("By instruction style (todo suites only):\n")
table(["Grounder", "literal", "natural"], [[n] + [f"{sum(x['ok'] for x in g[n] if x['suite'].startswith('todo') and x['style']==s)}/{sum(1 for x in g[n] if x['suite'].startswith('todo') and x['style']==s)}" for s in ("literal", "natural")] for n in names])
P("By todo UI variant (laya-ml-choice | lexical | embed | llm):\n")
table(["Variant"] + names, [[v_] + [f"{sum(x['ok'] for x in g[n] if x['suite']=='todo-'+v_)}/{sum(1 for x in g[n] if x['suite']=='todo-'+v_)}" for n in names] for v_ in "ABCDE"])

# ---- T5: calibration + cascade
P("### T5. Does Laya's probability predict correctness? Accuracy of the top choice by confidence bucket\n")
for n in ("laya-ml-choice", "laya-td-choice"):
    r = g[n]; P(f"**{n}**\n")
    b = [(0, .5), (.5, .7), (.7, .9), (.9, 1.01)]
    table(["p(top)", "cases", "accuracy"], [[f"{lo:.1f}–{min(hi,1):.1f}", sum(1 for x in r if lo <= x['p'] < hi), (f"{100*sum(x['ok'] for x in r if lo<=x['p']<hi)/max(1,sum(1 for x in r if lo<=x['p']<hi)):.0f}%")] for lo, hi in b])
P("### T6. Cascade: Laya first, escalate to local LLM (qwen3:8b) when p(top) < threshold\n")
llm = g["llm(qwen3:8b)"]
for n in ("laya-ml-choice", "laya-td-choice"):
    r = g[n]; rows = []
    for th in (0, .5, .6, .7, .8, .9, .95, 1.01):
        esc = [i for i, x in enumerate(r) if x["p"] < th]
        acc = sum((llm[i]["ok"] if i in set(esc) else r[i]["ok"]) for i in range(len(r))) / len(r)
        lat = st.mean(r[i]["ms2"] + (llm[i]["ms2"] if i in set(esc) else 0) for i in range(len(r)))
        rows.append([f"{th:.2f}" if th < 1.01 else "always LLM (incl. Laya cost)", f"{100*len(esc)/len(r):.0f}%", f"{100*acc:.1f}%", f"{lat:.0f}"])
    P(f"**{n} -> qwen3:8b**\n"); table(["threshold", "escalated", "accuracy", "mean ms/decision"], rows)
P(f"Reference: LLM alone {100*sum(x['ok'] for x in llm)/len(llm):.1f}% at {st.mean(x['ms2'] for x in llm):.0f} ms mean; Laya-ml alone {100*sum(x['ok'] for x in g['laya-ml-choice'])/NC:.1f}% at {st.mean(x['ms2'] for x in g['laya-ml-choice']):.0f} ms mean.\n")
P("Oracle ensemble (any of Laya-ml / Laya-td / embed / LLM correct):", f"{sum(any(g[n][i]['ok'] for n in ('laya-ml-choice','laya-td-choice','embed(bge-m3)','llm(qwen3:8b)')) for i in range(NC))}/{NC}\n")

# ---- T7..T9: scaling
acc = L("scale_acc-laya.json")["candidates"] + L("scale_acc-ollama.json")["candidates"]; lat = L("scale_lat-laya.json")["lat"] + L("scale_lat-ollama.json")["lat"]
P("### T7. Accuracy vs. candidate-list size, live Wikipedia article (30 trials per cell; gold link + N-1 random distractors)\n")
Ns = sorted({r["N"] for r in acc}); gn = list(dict.fromkeys(r["grounder"] for r in acc))
table(["Grounder"] + [f"N={n}" for n in Ns], [[x] + [(lambda r: f"{100*r['acc']:.0f}%")(next(q for q in acc if q['N']==n and q['grounder']==x)) for n in Ns] for x in gn])
P("### T8. Warm latency (ms, p50) vs. candidate-list size, each grounder measured alone\n")
ln = list(dict.fromkeys(r["grounder"] for r in lat))
table(["Grounder"] + [f"N={n}" for n in Ns], [[x] + [(lambda r: f"{r['warm_p50']:.0f}")(next(q for q in lat if q['N']==n and q['grounder']==x)) for n in Ns] for x in ln])
P("Cold (first-ever shape) worst case per grounder, ms:", {x: round(max(q["cold_max"] for q in lat if q["grounder"] == x)) for x in ln}, "\n")
rt = L("scale_runtime.json")
P("### T9. Runtime configuration (multilingual checkpoint, 70 real UI decisions run twice)\n")
table(["config", "1st pass p50", "1st pass p95", "1st pass max", "2nd pass p50", "2nd pass p95"], [[c["cfg"]] + [f"{c[k]:.0f}" for k in ("first_pass_p50", "first_pass_p95", "first_pass_max", "second_pass_p50", "second_pass_p95")] for c in rt["compile"]])
P("### T10. Batch throughput (3-way routing, multilingual, compile+pad+cache)\n")
table(["batch", "p50 ms per batch", "decisions/s"], [[t["batch"], f"{t['p50_ms']:.0f}", f"{t['decisions_per_s']:.0f}"] for t in rt["throughput"]])

# ---- T11: paired significance + honest cascade (leave-one-group-out)
from math import comb
def mcnemar(a, b):
    x = sum(1 for p, q in zip(g[a], g[b]) if p["ok"] and not q["ok"]); y = sum(1 for p, q in zip(g[a], g[b]) if q["ok"] and not p["ok"])
    n = x + y; k = min(x, y); pv = min(1.0, 2 * sum(comb(n, j) for j in range(k + 1)) / 2 ** n) if n else 1.0
    return x, y, pv
P("### T11. Paired comparison on the same cases (exact McNemar): A-only-correct / B-only-correct / p-value\n")
pairs = [("llm(qwen3:8b)", "laya-ml-choice"), ("llm(qwen3:8b)", "laya-td-choice"), ("embed(bge-m3)", "laya-ml-choice"), ("laya-td-choice", "laya-ml-choice"), ("laya-ml-choice", "lexical"), ("llm(qwen3:8b)", "embed(bge-m3)")]
table(["A", "B", "A only", "B only", "p"], [[a, b2, *(lambda r: (r[0], r[1], f"{r[2]:.3f}"))(mcnemar(a, b2))] for a, b2 in pairs])
P("### T12. Cascade with the threshold chosen on the other three suite groups (leave-one-group-out), then evaluated on the held-out group\n")
for n in ("laya-ml-choice", "laya-td-choice"):
    r = g[n]; gi = [grp(x) for x in r]; tot_ok = tot_esc = 0; taus = []
    for hold in set(gi):
        tr = [i for i in range(len(r)) if gi[i] != hold]; te = [i for i in range(len(r)) if gi[i] == hold]
        def score(th, idx): return sum((llm[i]["ok"] if r[i]["p"] < th else r[i]["ok"]) for i in idx)
        best = max((0.5, .6, .7, .8, .9, .95), key=lambda th: (score(th, tr), -th))
        taus.append(best); tot_ok += score(best, te); tot_esc += sum(r[i]["p"] < best for i in te)
    lat = st.mean(r[i]["ms2"] for i in range(len(r))) + (tot_esc / len(r)) * st.mean(x["ms2"] for x in llm)
    P(f"{n} -> qwen3:8b: thresholds chosen {sorted(taus)}; held-out accuracy {100*tot_ok/len(r):.1f}%, escalation {100*tot_esc/len(r):.0f}%, mean ~{lat:.0f} ms/decision\n")

# ---- T13: run-to-run variation
import glob
runs = sorted(glob.glob(os.path.join(R, "runs", "live_*.json")))
if runs:
    P("### T13. Run-to-run variation (same code, same pages): live suite, steps passed per run\n")
    P("Live runs:", [f"{sum(r['ok'] for r in json.load(open(f))['results'])}/{len(json.load(open(f))['results'])}" for f in runs], "\n")
    per = collections.defaultdict(list)
    for f in runs:
        for r in json.load(open(f))["results"]: per[(r["task"], r["step"])].append(r["ok"])
    unstable = {f"{k[0]}:{k[1]}": f"{sum(v)}/{len(v)}" for k, v in per.items() if 0 < sum(v) < len(v)}
    always_fail = {f"{k[0]}:{k[1]}": f"{sum(v)}/{len(v)}" for k, v in per.items() if sum(v) == 0}
    P("Unstable steps:", unstable or "none", "; always failing:", always_fail or "none", "\n")
    allr = [r for f in runs for r in json.load(open(f))["results"]]; allg = [r for r in allr if "picked_gold" in r and r["picked_gold"] is not None and "ground_ms" in r]
    P(f"Across all {len(runs)} runs: {sum(r['ok'] for r in allr)}/{len(allr)} steps passed end to end; Laya picked the gold element in {sum(r['picked_gold'] for r in allg)}/{len(allg)} decisions; failures: {dict(collections.Counter(r.get('err') for r in allr if not r['ok']))}\n")
    lm = [r["ground_ms"] for r in allg]
    P(f"Live Laya decision latency across {len(lm)} decisions: p50 {st.median(lm):.0f} ms, p95 {sorted(lm)[int(.95*(len(lm)-1))]:.0f} ms, max {max(lm):.0f} ms\n")
for kind in ("todo", "shop"):
    rs = sorted(glob.glob(os.path.join(R, "runs", f"{kind}_*.json")))
    if rs:
        if kind == "todo": tot = [sum(r["ok"] for r in json.load(open(f))["results"] if r["runner"] == "laya") for f in rs]
        else: tot = [sum(r["ok"] for r in json.load(open(f))["results"] if r["frame_mode"] == "all-frames") for f in rs]
        P(f"{kind} suite, Laya-driven steps passed per repeat:", tot, "\n")
idle = L("idle.json")
P("### T14. Latency after an idle gap (multilingual, one decision)\n")
table(["idle before call (s)", "p50 ms", "max ms"], [[x["idle_s"], f"{x['p50']:.0f}", f"{x['max']:.0f}"] for x in idle])
open(os.path.join(R, "tables.md"), "w").write("\n".join(out)); print("\n".join(out))
