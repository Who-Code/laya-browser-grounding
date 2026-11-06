### T1. Todo app, step pass rate by runner and UI variant (7 steps x 2 instruction styles = 14 per cell)

| Variant | scripted-css | scripted-role | laya |
|---|---|---|---|
| A | 14/14 | 14/14 | 11/14 |
| B | 4/14 | 14/14 | 11/14 |
| C | 14/14 | 2/14 | 6/14 |
| D | 14/14 | 12/14 | 9/14 |
| E | 14/14 | 4/14 | 6/14 |

Laya by instruction style:

| Variant | literal (7) | natural (7) |
|---|---|---|
| A | 7/7 | 4/7 |
| B | 7/7 | 4/7 |
| C | 2/7 | 4/7 |
| D | 5/7 | 4/7 |
| E | 4/7 | 2/7 |

Step wall time (snapshot+Laya+act+settle): Laya median 99 ms, scripted median 66 ms; Laya ground-only median 34.6 ms.

Laya failures by step (all variants): {'add': 5, 'f_active': 6, 'f_all': 4, 'type': 3, 'delete': 4, 'clear': 5} 

### T2. Checkout flow: steps completed (of 6) by frame condition and snapshot mode

| Condition (frame/form) | frame-aware snapshot | main-frame-only snapshot |
|---|---|---|
| none/plain | 6/6 | 6/6 |
| same/plain | 6/6 | 2/6 |
| cross/plain | 6/6 | 2/6 |
| nested/plain | 6/6 | 2/6 |
| none/shadow-open | 6/6 | 6/6 |
| same/shadow-open | 6/6 | 2/6 |
| cross/shadow-open | 6/6 | 2/6 |
| none/shadow-closed | 2/6 | 2/6 |
| cross/shadow-closed | 2/6 | 2/6 |
| none/canvas | 5/6 | 5/6 |
| cross/canvas | 5/6 | 2/6 |

Frame-aware: median snapshot 3 ms, median Laya 29 ms, median candidates 8.

### T3. Live sites: step outcomes

| Task | steps passed (last run) | Laya picked gold | median Laya ms | candidates |
|---|---|---|---|---|
| checkboxes | 1/2 | 2/2 | 50 | 4,4 |
| dropdown | 1/1 | 1/1 | 41 | 3 |
| add_remove | 2/2 | 2/2 | 36 | 3,4 |
| dynamic_loading | 1/1 | 1/1 | 63 | 3 |
| js_alerts | 1/1 | 1/1 | 443 | 5 |
| inputs | 0/1 | 0/0 | n/a |  |
| status_codes | 1/1 | 1/1 | 444 | 7 |
| challenging_dom | 2/2 | 2/2 | 107 | 25,25 |
| tinymce_iframe | 1/1 | 1/1 | 74 | 21 |
| todomvc_react | 7/7 | 7/7 | 36 | 12,17,18,19,21,19,18 |

Last run: 17/19 steps passed end to end; Laya chose the gold element in 18/18 decisions; median snapshot 5 ms.

### T4. Element-grounding accuracy over all logged decisions (144 cases), 95% Wilson CI in brackets

| Grounder | Top-1 accuracy | warm p50 ms | warm p95 ms |
|---|---|---|---|
| laya-ml-choice | 80% (115/144) [73–86] | 14.1 | 16 |
| laya-td-choice | 84% (121/144) [77–89] | 35.5 | 55 |
| laya-td-pointwise | 83% (120/144) [76–89] | 132.7 | 1616 |
| lexical | 72% (104/144) [64–79] | 0.1 | 0 |
| embed(bge-m3) | 84% (121/144) [77–89] | 224.4 | 300 |
| llm(qwen3:8b) | 89% (128/144) [83–93] | 344.9 | 521 |

By suite group (top-1 correct / cases):

| Grounder | dev:todo-A | todo-B..E | shop(iframe/shadow) | live |
|---|---|---|---|---|
| laya-ml-choice | 10/14 | 31/56 | 56/56 | 18/18 |
| laya-td-choice | 11/14 | 39/56 | 56/56 | 15/18 |
| laya-td-pointwise | 12/14 | 38/56 | 56/56 | 14/18 |
| lexical | 9/14 | 26/56 | 56/56 | 13/18 |
| embed(bge-m3) | 12/14 | 37/56 | 56/56 | 16/18 |
| llm(qwen3:8b) | 12/14 | 44/56 | 56/56 | 16/18 |

By instruction style (todo suites only):

| Grounder | literal | natural |
|---|---|---|
| laya-ml-choice | 25/35 | 16/35 |
| laya-td-choice | 28/35 | 22/35 |
| laya-td-pointwise | 29/35 | 21/35 |
| lexical | 24/35 | 11/35 |
| embed(bge-m3) | 29/35 | 20/35 |
| llm(qwen3:8b) | 30/35 | 26/35 |

By todo UI variant (laya-ml-choice | lexical | embed | llm):

| Variant | laya-ml-choice | laya-td-choice | laya-td-pointwise | lexical | embed(bge-m3) | llm(qwen3:8b) |
|---|---|---|---|---|---|---|
| A | 10/14 | 11/14 | 12/14 | 9/14 | 12/14 | 12/14 |
| B | 10/14 | 12/14 | 12/14 | 9/14 | 12/14 | 11/14 |
| C | 6/14 | 11/14 | 9/14 | 4/14 | 9/14 | 11/14 |
| D | 9/14 | 12/14 | 12/14 | 9/14 | 11/14 | 13/14 |
| E | 6/14 | 4/14 | 5/14 | 4/14 | 5/14 | 9/14 |

### T5. Does Laya's probability predict correctness? Accuracy of the top choice by confidence bucket

**laya-ml-choice**

| p(top) | cases | accuracy |
|---|---|---|
| 0.0–0.5 | 11 | 36% |
| 0.5–0.7 | 10 | 60% |
| 0.7–0.9 | 25 | 48% |
| 0.9–1.0 | 98 | 95% |

**laya-td-choice**

| p(top) | cases | accuracy |
|---|---|---|
| 0.0–0.5 | 60 | 72% |
| 0.5–0.7 | 22 | 86% |
| 0.7–0.9 | 24 | 88% |
| 0.9–1.0 | 38 | 100% |

### T6. Cascade: Laya first, escalate to local LLM (qwen3:8b) when p(top) < threshold

**laya-ml-choice -> qwen3:8b**

| threshold | escalated | accuracy | mean ms/decision |
|---|---|---|---|
| 0.00 | 0% | 79.9% | 14 |
| 0.50 | 8% | 82.6% | 35 |
| 0.60 | 12% | 82.6% | 48 |
| 0.70 | 15% | 84.0% | 56 |
| 0.80 | 22% | 87.5% | 79 |
| 0.90 | 32% | 90.3% | 109 |
| 0.95 | 43% | 90.3% | 153 |
| always LLM (incl. Laya cost) | 100% | 88.9% | 356 |

**laya-td-choice -> qwen3:8b**

| threshold | escalated | accuracy | mean ms/decision |
|---|---|---|---|
| 0.00 | 0% | 84.0% | 40 |
| 0.50 | 42% | 88.9% | 180 |
| 0.60 | 48% | 90.3% | 198 |
| 0.70 | 57% | 89.6% | 226 |
| 0.80 | 63% | 91.7% | 249 |
| 0.90 | 74% | 91.7% | 283 |
| 0.95 | 85% | 91.0% | 338 |
| always LLM (incl. Laya cost) | 100% | 88.9% | 382 |

Reference: LLM alone 88.9% at 342 ms mean; Laya-ml alone 79.9% at 14 ms mean.

Oracle ensemble (any of Laya-ml / Laya-td / embed / LLM correct): 140/144

### T7. Accuracy vs. candidate-list size, live Wikipedia article (30 trials per cell; gold link + N-1 random distractors)

| Grounder | N=5 | N=10 | N=20 | N=40 | N=80 | N=160 |
|---|---|---|---|---|---|---|
| laya-ml-choice | 87% | 83% | 67% | 50% | 47% | 47% |
| laya-td-choice | 83% | 70% | 63% | 40% | 23% | 20% |
| lexical | 70% | 70% | 63% | 53% | 47% | 47% |
| hybrid(lex15->laya-ml) | 87% | 87% | 67% | 63% | 53% | 37% |
| embed(bge-m3) | 93% | 80% | 77% | 70% | 67% | 60% |
| llm(qwen3:8b) | 97% | 90% | 93% | 93% | 90% | 73% |

### T8. Warm latency (ms, p50) vs. candidate-list size, each grounder measured alone

| Grounder | N=5 | N=10 | N=20 | N=40 | N=80 | N=160 |
|---|---|---|---|---|---|---|
| laya-ml-choice | 12 | 16 | 24 | 29 | 35 | 61 |
| laya-td-choice | 28 | 39 | 59 | 71 | 83 | 140 |
| embed(bge-m3) | 139 | 223 | 489 | 824 | 1704 | 3346 |
| llm(qwen3:8b) | 251 | 318 | 959 | 877 | 3671 | 8490 |

Cold (first-ever shape) worst case per grounder, ms: {'laya-ml-choice': 1135, 'laya-td-choice': 1142, 'embed(bge-m3)': 8088, 'llm(qwen3:8b)': 15055} 

### T9. Runtime configuration (multilingual checkpoint, 70 real UI decisions run twice)

| config | 1st pass p50 | 1st pass p95 | 1st pass max | 2nd pass p50 | 2nd pass p95 |
|---|---|---|---|---|---|
| default | 18 | 24 | 1164 | 18 | 20 |
| compile | 17 | 23 | 30 | 16 | 18 |
| compile+pad16 | 16 | 20 | 29 | 17 | 20 |
| compile+pad16+cache | 16 | 21 | 31 | 17 | 20 |

### T10. Batch throughput (3-way routing, multilingual, compile+pad+cache)

| batch | p50 ms per batch | decisions/s |
|---|---|---|
| 1 | 18 | 57 |
| 4 | 21 | 193 |
| 16 | 69 | 231 |
| 64 | 319 | 201 |

### T11. Paired comparison on the same cases (exact McNemar): A-only-correct / B-only-correct / p-value

| A | B | A only | B only | p |
|---|---|---|---|---|
| llm(qwen3:8b) | laya-ml-choice | 22 | 9 | 0.029 |
| llm(qwen3:8b) | laya-td-choice | 16 | 9 | 0.230 |
| embed(bge-m3) | laya-ml-choice | 13 | 7 | 0.263 |
| laya-td-choice | laya-ml-choice | 14 | 8 | 0.286 |
| laya-ml-choice | lexical | 15 | 4 | 0.019 |
| llm(qwen3:8b) | embed(bge-m3) | 17 | 10 | 0.248 |

### T12. Cascade with the threshold chosen on the other three suite groups (leave-one-group-out), then evaluated on the held-out group

laya-ml-choice -> qwen3:8b: thresholds chosen [0.8, 0.9, 0.9, 0.95]; held-out accuracy 86.8%, escalation 25%, mean ~99 ms/decision

laya-td-choice -> qwen3:8b: thresholds chosen [0.8, 0.8, 0.8, 0.8]; held-out accuracy 91.7%, escalation 63%, mean ~256 ms/decision

### T13. Run-to-run variation (same code, same pages): live suite, steps passed per run

Live runs: ['19/19', '19/19', '18/19', '18/19', '17/19'] 

Unstable steps: {'checkboxes:0': '2/5', 'inputs:0': '4/5'} ; always failing: none 

Across all 5 runs: 91/95 steps passed end to end; Laya picked the gold element in 94/94 decisions; failures: {'TimeoutError': 3, 'load:Error': 1}

Live Laya decision latency across 94 decisions: p50 51 ms, p95 104 ms, max 444 ms

todo suite, Laya-driven steps passed per repeat: [43, 43, 43] 

shop suite, Laya-driven steps passed per repeat: [56, 56, 56] 

### T14. Latency after an idle gap (multilingual, one decision)

| idle before call (s) | p50 ms | max ms |
|---|---|---|
| 0 | 8 | 10 |
| 0.25 | 20 | 24 |
| 0.5 | 24 | 28 |
| 1 | 22 | 29 |
| 2 | 53 | 62 |
| 5 | 49 | 54 |
| 10 | 56 | 97 |
| 2 (with 10 Hz keep-alive) | 19 | 25 |
