# Replication package

Code, local test fixtures and raw results for *Laya-MLX as a Fast Local Decision Engine for Browser Automation: Element Grounding in Iframes, UI Tests and Live Sites on Apple Silicon*.

## Contents
| Path | Purpose |
|---|---|
| `code/pilot.py` | page snapshot (frames, open shadow DOM), grounders (Laya, lexical, embedding, LLM), executor |
| `code/brain.py` | thin wrapper around `laya-mlx` (single worker thread) |
| `code/fixtures.py` | todo app (5 UI variants) and checkout flow (iframe / shadow DOM / canvas conditions); run on two ports for cross-origin frames |
| `code/suite_todo.py`, `suite_shop.py`, `suite_live.py` | end-to-end suites (Tables 2-4 of the paper) |
| `code/run_grounding.py` | replays all logged decisions through one grounder (run each grounder in its own process) |
| `code/suite_scale.py`, `suite_idle.py` | candidate-count scaling, runtime configuration, batching, idle-gap latency |
| `code/analyze.py`, `make_figures_tables.py` | statistics, tables (`results/tables.md`) and the paper's figures/LaTeX tables |
| `code/results/` | raw per-decision results (JSON) for every experiment, including repeated runs in `runs/` |
| `code/messages.json` | message corpus used for the batch-throughput test |

## Requirements
Apple Silicon Mac, Python 3.12, Google Chrome, [Ollama](https://ollama.com) with `qwen3:8b` and `bge-m3` pulled (baselines only), internet access for the live suites. `pip install -r requirements.txt`; the Laya checkpoints `aac6fef/laya-multilingual-mlx` (revision `f2b4faf51023039425946074e2cf1361d2db11d5`) and `aac6fef/laya-typed-decisions-mlx` (revision `f9e501c2080cc57c13d6887820329758f5351125`) are downloaded from Hugging Face on first use. Model weights are **not** redistributed here and keep their own licenses.

## Regenerating tables and figures from the included raw results (no models needed)
```
cd code
python analyze.py              # prints and writes results/tables.md
python make_figures_tables.py  # writes paper_assets/figures and paper_assets/tables
```

## Re-running the experiments
`./reproduce.sh` runs everything in order. Notes: results of the Laya-driven suites are deterministic across repeats on the same machine, but live-site results can change when the sites change; timings depend strongly on machine state (use a quiet machine; do not keep Ollama models loaded while timing Laya).

## Note on `results/tables.md`
The paper's tables and figures are produced by `make_figures_tables.py` (instruction-level cluster statistics, all 15 paired tests with Holm adjustment, exact per-case cascade latency). `results/tables.md` from `analyze.py` is an earlier, naive summary (Wilson intervals, six McNemar tests, approximate cascade latency) kept for comparison; where they differ, the paper's tables are authoritative.

## Third-party content
`code/results/wiki_cands.json` contains link labels captured from one English Wikipedia article (text licensed CC BY-SA 4.0; (c) Wikipedia contributors). The live suites interact with the-internet.herokuapp.com and todomvc.com; please be considerate of their servers.

## License
Code: MIT (see `LICENSE`; copyright holder to be completed by the author). Data/results: CC BY 4.0 unless noted above.
