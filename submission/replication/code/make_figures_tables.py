"""Build all paper figures (vector PDF) and LaTeX table fragments from results/*.json."""
import json, math, os, glob, statistics as st, collections
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(HERE, "results")
OUT = os.environ.get("PAPER_DIR", os.path.join(HERE, "paper_assets"))
FIG, TAB = os.path.join(OUT, "figures"), os.path.join(OUT, "tables")
os.makedirs(FIG, exist_ok=True); os.makedirs(TAB, exist_ok=True)
L = lambda f: json.load(open(os.path.join(R, f)))
plt.rcParams.update({"font.family": "serif", "font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
COL = {"laya-ml-choice": "#0072B2", "laya-td-choice": "#56B4E9", "lexical": "#999999", "embed(bge-m3)": "#E69F00", "llm(qwen3:8b)": "#D55E00",
       "hybrid(lex15->laya-ml)": "#009E73", "laya-td-pointwise": "#CC79A7"}
MK = {"laya-ml-choice": "o", "laya-td-choice": "s", "lexical": "x", "embed(bge-m3)": "^", "llm(qwen3:8b)": "D", "hybrid(lex15->laya-ml)": "v", "laya-td-pointwise": "P"}
NAME = {"laya-ml-choice": "Laya-ML", "laya-td-choice": "Laya-TD", "lexical": "Lexical", "embed(bge-m3)": "bge-m3", "llm(qwen3:8b)": "Qwen3-8B",
        "hybrid(lex15->laya-ml)": "Lexical-15 + Laya-ML", "laya-td-pointwise": "Laya-TD pointwise"}
def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)); return (c - w) / d, (c + w) / d
import random as _rnd
def cluster_of(x):
    kind = "todo" if x["suite"].startswith("todo") else "shop" if x["suite"].startswith("shop") else "live"
    return f"{kind}|{x['step']}|{x['style']}"
def boot_ci(vals_by_cluster, B=10000, seed=0):
    """vals_by_cluster: list of (sum_ok, n_cases) per cluster; percentile bootstrap over clusters of the case-weighted accuracy."""
    rnd = _rnd.Random(seed); k = len(vals_by_cluster); out = []
    for _ in range(B):
        so = sn = 0
        for _i in range(k): a, n = vals_by_cluster[rnd.randrange(k)]; so += a; sn += n
        out.append(so / sn)
    out.sort(); return out[int(.025 * B)], out[int(.975 * B) - 1]
def clusters(rows, idx, key=lambda x: x["ok"]):
    d = {}
    for i in idx: c = cluster_of(rows[i]); a = d.setdefault(c, [0, 0]); a[0] += key(rows[i]); a[1] += 1
    return list(d.values())
def paired_test(ra, rb, idx, B=10000, P=20000, seed=1):
    d = {}
    for i in idx: c = cluster_of(ra[i]); a = d.setdefault(c, [0, 0]); a[0] += ra[i]["ok"] - rb[i]["ok"]; a[1] += 1
    cl = list(d.values()); n = sum(c[1] for c in cl); obs = sum(c[0] for c in cl) / n
    rnd = _rnd.Random(seed); bs = []
    for _ in range(B):
        so = sn = 0
        for _i in range(len(cl)): a, m = cl[rnd.randrange(len(cl))]; so += a; sn += m
        bs.append(so / sn)
    bs.sort(); ci = (bs[int(.025 * B)], bs[int(.975 * B) - 1]); T = abs(sum(c[0] for c in cl)); cnt = 0
    for _ in range(P):
        t = sum(c[0] if rnd.random() < .5 else -c[0] for c in cl)
        if abs(t) >= T - 1e-9: cnt += 1
    return obs, ci, (cnt + 1) / (P + 1), len(cl)
def wr(name, rows): open(os.path.join(TAB, name), "w").write("\n".join(rows) + "\n")
def tab(cols, body, head): return [f"\\begin{{tabular}}{{{cols}}}", "\\toprule", head + " \\\\", "\\midrule"] + [r + " \\\\" for r in body] + ["\\bottomrule", "\\end{tabular}"]

# ------------------------------------------------------------------ data
todo = L("todo.json")["results"]; shop = L("shop.json")["results"]; live = L("live.json")["results"]
ORDER = ["laya-ml-choice", "laya-td-choice", "laya-td-pointwise", "lexical", "embed(bge-m3)", "llm(qwen3:8b)"]
g = {}
for n in ORDER: g.update(L(f"grounding_{n}.json"))
NC = len(g["lexical"])
acc = L("scale_acc-laya.json")["candidates"] + L("scale_acc-ollama.json")["candidates"]
lat = L("scale_lat-laya.json")["lat"] + L("scale_lat-ollama.json")["lat"]
rt = L("scale_runtime.json"); idle = L("idle.json")
def grp(r): s = r["suite"]; return "A" if s == "todo-A" else "BE" if s.startswith("todo-") else "shop" if s.startswith("shop") else "live"

# ------------------------------------------------------------------ figures
# Fig 1: pipeline
fig, ax = plt.subplots(figsize=(7.0, 1.9)); ax.axis("off"); ax.set_xlim(-2, 104); ax.set_ylim(0, 30)
boxes = [(0, "Page\n(all frames,\nopen shadow DOM)"), (21, "Snapshot\n(name + row\ncontext per element)"), (42, "Grounder\n(Laya choice\nquestion or baseline)"), (63, "Confidence gate\n$p \\geq \\tau$ ?"), (84, "Executor\n(Playwright\nelement handle)")]
for x, t in boxes:
    ax.add_patch(FancyBboxPatch((x, 8), 19, 15, boxstyle="round,pad=0.3", fc="#eef3fb", ec="#33507a", lw=0.9)); ax.text(x + 9.5, 15.5, t, ha="center", va="center", fontsize=6.4)
for x0, x1 in [(19.6, 20.9), (40.6, 41.9), (61.6, 62.9), (82.6, 83.9)]:
    ax.add_patch(FancyArrowPatch((x0, 15.5), (x1, 15.5), arrowstyle="-|>", mutation_scale=7, lw=0.9, color="#33507a"))
ax.add_patch(FancyBboxPatch((63, 0.5), 19, 5, boxstyle="round,pad=0.3", fc="#fdf0e4", ec="#a05a10", lw=0.9)); ax.text(72.5, 3, "LLM fallback if $p<\\tau$", ha="center", va="center", fontsize=6.2)
ax.add_patch(FancyArrowPatch((72.5, 7.6), (72.5, 6.2), arrowstyle="-|>", mutation_scale=7, lw=0.8, color="#a05a10"))
ax.add_patch(FancyArrowPatch((82.4, 3), (93.5, 7.6), arrowstyle="-|>", mutation_scale=7, lw=0.8, color="#a05a10", connectionstyle="arc3,rad=-0.25"))
fig.savefig(os.path.join(FIG, "fig_pipeline.pdf"), bbox_inches="tight"); plt.close(fig)
# Fig 2: accuracy vs N
Ns = sorted({r["N"] for r in acc}); fig, axs = plt.subplots(1, 2, figsize=(6.8, 2.6))
for gn in ["lexical", "laya-ml-choice", "laya-td-choice", "hybrid(lex15->laya-ml)", "embed(bge-m3)", "llm(qwen3:8b)"]:
    ys = [next(q for q in acc if q["N"] == n and q["grounder"] == gn)["acc"] * 100 for n in Ns]
    axs[0].plot(Ns, ys, marker=MK[gn], ms=4, lw=1.1, color=COL[gn], label=NAME[gn])
axs[0].set_xscale("log", base=2); axs[0].set_xticks(Ns); axs[0].set_xticklabels(Ns); axs[0].set_xlabel("Candidate elements $N$"); axs[0].set_ylabel("Top-1 accuracy (%)"); axs[0].set_ylim(0, 100); axs[0].set_title("(a) Accuracy", fontsize=8.5)
for gn in ["laya-ml-choice", "laya-td-choice", "embed(bge-m3)", "llm(qwen3:8b)"]:
    ys = [next(q for q in lat if q["N"] == n and q["grounder"] == gn)["warm_p50"] for n in Ns]
    axs[1].plot(Ns, ys, marker=MK[gn], ms=4, lw=1.1, color=COL[gn], label=NAME[gn])
axs[1].set_xscale("log", base=2); axs[1].set_yscale("log"); axs[1].set_xticks(Ns); axs[1].set_xticklabels(Ns); axs[1].set_xlabel("Candidate elements $N$"); axs[1].set_ylabel("Warm median latency (ms)"); axs[1].set_title("(b) Latency", fontsize=8.5)
h, l = axs[0].get_legend_handles_labels(); fig.legend(h, l, loc="lower center", ncol=3, frameon=False, fontsize=7, bbox_to_anchor=(0.5, -0.17))
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_scaling.pdf"), bbox_inches="tight"); plt.close(fig)

# cascade (leave-one-group-out) + in-sample
llm = g["llm(qwen3:8b)"]
ALL = list(range(NC)); DISC = [i for i in ALL if grp(g["lexical"][i]) != "shop"]      # DISC = 88 discriminative (non-checkout) cases
def logo(name, idx):
    r = g[name]; gi = {i: grp(r[i]) for i in idx}; ok = esc = 0; taus = []; taus_by_case = {}
    for hold in sorted(set(gi.values())):
        tr = [i for i in idx if gi[i] != hold]; te = [i for i in idx if gi[i] == hold]
        sc = lambda th, I: sum((llm[i]["ok"] if r[i]["p"] < th else r[i]["ok"]) for i in I)
        best = max((0.5, .6, .7, .8, .9, .95), key=lambda th: (sc(th, tr), -th)); taus.append(best); ok += sc(best, te); esc += sum(r[i]["p"] < best for i in te)
        for i in te: taus_by_case[i] = best
    n = len(idx); return ok / n, esc / n, st.mean(r[i]["ms2"] + (llm[i]["ms2"] if r[i]["p"] < taus_by_case[i] else 0) for i in idx), sorted(taus)
casc = {(n, k): logo(n, ix) for n in ("laya-ml-choice", "laya-td-choice") for k, ix in (("all", ALL), ("disc", DISC))}
json.dump({f"{k[0]}|{k[1]}": {"acc": v[0], "esc": v[1], "ms": v[2], "taus": v[3]} for k, v in casc.items()}, open(os.path.join(R, "cascade_logo.json"), "w"))
# Fig 3: accuracy-latency
fig, ax = plt.subplots(figsize=(5.8, 3.0))
for n in ORDER:
    r = [g[n][i] for i in DISC]; a = sum(x["ok"] for x in r) / len(r); ms = st.mean(x["ms2"] for x in r); lo, hi = boot_ci(clusters(g[n], DISC))
    ax.errorbar(ms, a * 100, yerr=[[a * 100 - lo * 100], [hi * 100 - a * 100]], fmt=MK[n], color=COL[n], ms=5, capsize=2, lw=0.8, label=NAME[n])
for n, lab, cc in (("laya-ml-choice", "Laya-ML $\\to$ LLM", "#009E73"), ("laya-td-choice", "Laya-TD $\\to$ LLM", "#CC3311")):
    a, e, ms, _ = casc[(n, "disc")]; ax.scatter([ms], [a * 100], marker="*", s=80, color=cc, edgecolor="k", lw=0.5, zorder=5, label=lab + " (cascade)")
ax.set_xscale("log"); ax.set_xlabel("Mean latency per decision (ms, log scale)"); ax.set_ylabel("Top-1 accuracy (%)"); ax.set_ylim(35, 100)
ax.legend(fontsize=6.3, frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1.0))
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_pareto.pdf"), bbox_inches="tight"); plt.close(fig)
# Fig 4: reliability
fig, ax = plt.subplots(figsize=(3.4, 2.6)); bins = [(0, .5), (.5, .7), (.7, .9), (.9, 1.01)]; lab = ["<0.5", "0.5-0.7", "0.7-0.9", ">=0.9"]; w = 0.38
for k, (n, off) in enumerate((("laya-ml-choice", -w / 2), ("laya-td-choice", w / 2))):
    r = [g[n][i] for i in DISC]; ys = []; ns = []
    for lo, hi in bins:
        s = [x for x in r if lo <= x["p"] < hi]; ys.append(100 * sum(x["ok"] for x in s) / max(1, len(s))); ns.append(len(s))
    xs = [i + off for i in range(4)]; ax.bar(xs, ys, w, color=COL[n], label=NAME[n])
    for x, y, c in zip(xs, ys, ns): ax.text(x, y + 1.5, f"n={c}", ha="center", fontsize=5.8)
ax.set_xticks(range(4)); ax.set_xticklabels(lab); ax.set_xlabel("Laya confidence $p$ (top choice)"); ax.set_ylabel("Accuracy of top choice (%)"); ax.set_ylim(0, 112); ax.legend(fontsize=7, frameon=False, loc="upper left")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_reliability.pdf"), bbox_inches="tight"); plt.close(fig)

# ------------------------------------------------------------------ tables
# T todo
rows = []
for v, desc in zip("ABCDE", ["baseline", "obfuscated classes/ids, shuffled order", "relabeled visible text", "icon-only, aria-labels", "icon-only, no accessible name"]):
    f = lambda rn, s=None: sum(r["ok"] for r in todo if r["variant"] == v and r["runner"] == rn and (s is None or r["style"] == s))
    rows.append(f"{v} & {desc} & {f('scripted-css')}/14 & {f('scripted-role')}/14 & {f('laya')}/14 & {f('laya','literal')}/7 & {f('laya','natural')}/7")
wr("todo.tex", tab("llp{0.9cm}p{0.9cm}p{0.9cm}p{0.9cm}p{0.9cm}".replace("p{0.9cm}", "r"), rows, "Var. & Change & CSS & Role & Laya & \\multicolumn{1}{c}{Lit.} & \\multicolumn{1}{c}{Nat.}"))
# T shop
conds = list(dict.fromkeys(r["cond"] for r in shop)); NM = {"none/plain": "Inline form", "same/plain": "Same-origin iframe", "cross/plain": "Cross-origin iframe", "nested/plain": "Nested iframes (cross-origin chain)",
    "none/shadow-open": "Open shadow DOM, inline", "same/shadow-open": "Open shadow DOM, same-origin iframe", "cross/shadow-open": "Open shadow DOM, cross-origin iframe",
    "none/shadow-closed": "Closed shadow DOM, inline", "cross/shadow-closed": "Closed shadow DOM, cross-origin iframe", "none/canvas": "Canvas Pay button, inline", "cross/canvas": "Canvas Pay button, cross-origin iframe"}
rows = [f"{NM[c]} & {sum(r['ok'] for r in shop if r['cond']==c and r['frame_mode']=='all-frames')}/6 & {sum(r['ok'] for r in shop if r['cond']==c and r['frame_mode']=='main-only')}/6" for c in conds]
wr("shop.tex", tab("lrr", rows, "Payment form location & All-frames snapshot & Main-frame-only"))
# T grounding main
rows = []
for n in ORDER:
    r = g[n]; k = sum(x["ok"] for x in r); lo, hi = boot_ci(clusters(r, ALL)); ms = sorted(x["ms2"] for x in r)
    rd = [g[n][i] for i in DISC]; kd = sum(x["ok"] for x in rd); lod, hid = boot_ci(clusters(g[n], DISC))
    rows.append(f"{NAME[n]} & {100*kd/len(rd):.0f}\\% ({kd}/{len(rd)}) & [{100*lod:.0f}, {100*hid:.0f}] & {100*k/len(r):.0f}\\% ({k}/{len(r)}) & [{100*lo:.0f}, {100*hi:.0f}] & {ms[len(ms)//2]:.1f} & {('<1' if ms[int(.95*(len(ms)-1))] < 1 else format(ms[int(.95*(len(ms)-1))], '.0f'))}")
wr("grounding.tex", tab("lrrrrrr", rows, "Grounder & \\multicolumn{2}{c}{88 discriminative cases} & \\multicolumn{2}{c}{All 144 cases} & p50 (ms) & p95 (ms)"))
# T grounding by slice
rows = []
for n in ORDER:
    r = g[n]; c = lambda f: f"{sum(x['ok'] for x in r if f(x))}/{sum(1 for x in r if f(x))}"
    rows.append(f"{NAME[n]} & {c(lambda x: grp(x)=='A')} & {c(lambda x: grp(x)=='BE')} & {c(lambda x: grp(x)=='shop')} & {c(lambda x: grp(x)=='live')} & {c(lambda x: x['suite'].startswith('todo') and x['style']=='literal')} & {c(lambda x: x['suite'].startswith('todo') and x['style']=='natural')}")
wr("slices.tex", tab("lrrrrrr", rows, "Grounder & Dev (A) & Todo B--E & Checkout & Live & Literal & Natural"))
# T scaling acc + latency
rows = [f"{NAME[gn]} & " + " & ".join(f"{100*next(q for q in acc if q['N']==n and q['grounder']==gn)['acc']:.0f}" for n in Ns) for gn in ["lexical", "laya-ml-choice", "laya-td-choice", "hybrid(lex15->laya-ml)", "embed(bge-m3)", "llm(qwen3:8b)"]]
wr("scale_acc.tex", tab("l" + "r" * len(Ns), rows, "Grounder & " + " & ".join(f"$N{{=}}{n}$" for n in Ns)))
rows = [f"{NAME[gn]} & " + " & ".join(f"{next(q for q in lat if q['N']==n and q['grounder']==gn)['warm_p50']:.0f}" for n in Ns) for gn in ["laya-ml-choice", "laya-td-choice", "embed(bge-m3)", "llm(qwen3:8b)"]]
wr("scale_lat.tex", tab("l" + "r" * len(Ns), rows, "Grounder & " + " & ".join(f"$N{{=}}{n}$" for n in Ns)))
# T scaling literal/natural
if "acc_literal" in acc[0]:
    rows = []
    for gn in ["lexical", "laya-ml-choice", "laya-td-choice", "hybrid(lex15->laya-ml)", "embed(bge-m3)", "llm(qwen3:8b)"]:
        cells = []
        for n in Ns:
            q = next(q for q in acc if q["N"] == n and q["grounder"] == gn); cells.append(f"{100*q['acc_literal']:.0f}/{100*q['acc_natural']:.0f}")
        rows.append(f"{NAME[gn]} & " + " & ".join(cells))
    wr("scale_split.tex", tab("l" + "r" * len(Ns), rows, "Grounder & " + " & ".join(f"$N{{=}}{n}$" for n in Ns)))
# T confidence + cascade
rows = []
for n in ("laya-ml-choice", "laya-td-choice"):
    for lab, ix in (("88 cases", DISC), ("all 144", ALL)):
        r = [g[n][i] for i in ix]; cells = []
        for lo, hi in bins:
            s = [x for x in r if lo <= x["p"] < hi]; cells.append(f"{len(s)} / {100*sum(x['ok'] for x in s)/max(1,len(s)):.0f}\\%")
        rows.append(f"{NAME[n]} ({lab}) & " + " & ".join(cells))
wr("conf.tex", tab("lrrrr", rows, "Checkpoint (cases) & $p<0.5$ & $0.5$--$0.7$ & $0.7$--$0.9$ & $\\geq 0.9$"))
def line(lab, n, ix, key):
    r = [g[n][i] for i in ix]; return r
rows = []
def both(label, fa, fd): rows.append(f"{label} & {fd[0]} & {fd[1]} & {fd[2]} & {fa[0]} & {fa[1]} & {fa[2]}")
def only(n, ix): r = [g[n][i] for i in ix]; return (f"{100*(0 if n!='llm(qwen3:8b)' else 1):.0f}\\%", f"{100*sum(x['ok'] for x in r)/len(r):.1f}\\%", f"{st.mean(x['ms2'] for x in r):.0f}")
def casc_f(n, k): a, e, ms, _ = casc[(n, k)]; return (f"{100*e:.0f}\\%", f"{100*a:.1f}\\%", f"{ms:.0f}")
both("Laya-ML only", only("laya-ml-choice", ALL), only("laya-ml-choice", DISC))
both("Laya-ML $\\to$ LLM (LOGO)", casc_f("laya-ml-choice", "all"), casc_f("laya-ml-choice", "disc"))
both("Laya-TD only", only("laya-td-choice", ALL), only("laya-td-choice", DISC))
both("Laya-TD $\\to$ LLM (LOGO)", casc_f("laya-td-choice", "all"), casc_f("laya-td-choice", "disc"))
both("Qwen3-8B only", only("llm(qwen3:8b)", ALL), only("llm(qwen3:8b)", DISC))
wr("cascade.tex", tab("lrrrrrr", rows, "Configuration & \\multicolumn{3}{c}{88 discriminative cases} & \\multicolumn{3}{c}{All 144 cases}  \\\\ \\cmidrule(lr){2-4}\\cmidrule(lr){5-7} & Escal. & Acc. & ms & Escal. & Acc. & ms"))
# T paired tests (cluster-level, all 15 pairs, Holm)
import itertools
PN = ["lexical", "laya-ml-choice", "laya-td-choice", "laya-td-pointwise", "embed(bge-m3)", "llm(qwen3:8b)"]
res = []
for a, b2 in itertools.combinations(PN, 2):
    obs, ci, pv, ncl = paired_test(g[b2], g[a], DISC)       # b2 minus a, ordered so that the first listed is the weaker in PN order
    res.append([a, b2, obs, ci, pv, ncl])
order = sorted(range(len(res)), key=lambda i: res[i][4]); m = len(res); holm = [0] * m; prev = 0
for rank, i in enumerate(order): prev = max(prev, min(1.0, (m - rank) * res[i][4])); holm[i] = prev
rows = []
for i in order:
    a, b2, obs, ci, pv, ncl = res[i]
    rows.append(f"{NAME[b2]} $-$ {NAME[a]} & {100*obs:+.1f} & [{100*ci[0]:+.1f}, {100*ci[1]:+.1f}] & {pv:.4f} & {holm[i]:.3f}")
wr("mcnemar.tex", tab("lrrrr", rows, "A $-$ B & Diff.\\ (points) & 95\\% CI & $p$ & $p_{\\mathrm{Holm}}$"))
json.dump([{"a": r[0], "b": r[1], "diff": r[2], "ci": r[3], "p": r[4], "p_holm": holm[i]} for i, r in enumerate(res)], open(os.path.join(R, "paired_tests.json"), "w"), indent=1)
# T idle
rows = [f"{x['idle_s'] if not isinstance(x['idle_s'], str) else '2, with 10\\,Hz keep-alive'} & {x['p50']:.0f} & {x['max']:.0f}" for x in idle]
wr("idle.tex", tab("lrr", rows, "Idle before call (s) & p50 (ms) & max (ms)"))
# T runtime
rows = [f"{c['cfg'].replace('_','\\_').replace('+', '+')} & {c['first_pass_p50']:.0f} & {c['first_pass_p95']:.0f} & {c['first_pass_max']:.0f} & {c['second_pass_p50']:.0f} & {c['second_pass_p95']:.0f}" for c in rt["compile"]]
wr("compile.tex", tab("lrrrrr", rows, "Configuration & 1st p50 & 1st p95 & 1st max & 2nd p50 & 2nd p95"))
rows = [f"{t['batch']} & {t['p50_ms']:.0f} & {t['decisions_per_s']:.0f}" for t in rt["throughput"]]
wr("batch.tex", tab("lrr", rows, "Batch size & p50 per batch (ms) & Decisions/s"))
# live
runs = sorted(glob.glob(os.path.join(R, "runs", "live_*.json"))); allr = [r for f in runs for r in json.load(open(f))["results"]]
tasks = list(dict.fromkeys(r["task"] for r in allr)); rows = []
for t in tasks:
    rr = [r for r in allr if r["task"] == t]; gg = [r for r in rr if r.get("picked_gold") is not None and "ground_ms" in r]
    rows.append(f"{t.replace('_','\\_')} & {len(set(r['step'] for r in rr))} & {sum(r['ok'] for r in rr)}/{len(rr)} & {sum(r['picked_gold'] for r in gg)}/{len(gg)}")
wr("live.tex", tab("lrrr", rows, "Task & Steps & Passed (5 runs) & Gold chosen"))
summ = {"live_pass": sum(r["ok"] for r in allr), "live_n": len(allr), "live_gold": sum(r["picked_gold"] for r in allr if r.get("picked_gold") is not None and "ground_ms" in r), "live_dec": sum(1 for r in allr if r.get("picked_gold") is not None and "ground_ms" in r),
        "live_lat_p50": st.median([r["ground_ms"] for r in allr if "ground_ms" in r and r.get("picked_gold") is not None]), "n_cases": NC}
json.dump(summ, open(os.path.join(R, "summary.json"), "w"), indent=1); print(summ); print(casc)

# ------------------------------------------------------------------ instruction appendix (generated from the suites themselves)
import sys; sys.path.insert(0, HERE)
import suite_todo as T, suite_shop as SH, suite_live as LV
def esc(t): return t.replace("\\", "\\textbackslash{}").replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#").replace("$", "\\$").replace("'", "\\textquotesingle{}")
rows = [f"{esc(k)} & {esc(lit)} & {esc(nat)}" for k, lit, nat, *_ in T.STEPS]
wr("instr_todo.tex", ["\\begin{tabular}{@{}lp{5.4cm}p{5.6cm}@{}}", "\\toprule", "Step & Literal instruction & Natural instruction \\\\", "\\midrule"] + [r + " \\\\" for r in rows] + ["\\bottomrule", "\\end{tabular}"])
rows = [f"{esc(k)} & {esc(ins)}" for k, ins, *_ in SH.STEPS]
wr("instr_shop.tex", ["\\begin{tabular}{@{}lp{11cm}@{}}", "\\toprule", "Step & Instruction \\\\", "\\midrule"] + [r + " \\\\" for r in rows] + ["\\bottomrule", "\\end{tabular}"])
rows = []
for name, url, steps in LV.TASKS:
    for i, (ins, *_r) in enumerate(steps): rows.append(f"{esc(name)} & {i+1} & {esc(ins)}")
wr("instr_live.tex", ["\\begin{tabular}{@{}llp{9.4cm}@{}}", "\\toprule", "Task & \\# & Instruction \\\\", "\\midrule"] + [r + " \\\\" for r in rows] + ["\\bottomrule", "\\end{tabular}"])
print("instruction tables written")
