#!/bin/sh
# Re-run the experiments (Apple Silicon Mac, Google Chrome, Ollama with qwen3:8b and bge-m3 pulled, internet for live suites).
# Run on a quiet machine, and never keep Ollama models loaded while timing Laya (see paper, Section 3.6).
set -e
cd "$(dirname "$0")/code"
python fixtures.py 8801 & python fixtures.py 8802 & sleep 2
python suite_todo.py; python suite_shop.py; python suite_live.py
for g in laya-ml-choice laya-td-choice laya-td-pointwise lexical "embed(bge-m3)" "llm(qwen3:8b)"; do
  case "$g" in laya*) ollama stop qwen3:8b >/dev/null 2>&1; ollama stop bge-m3 >/dev/null 2>&1;; esac
  python run_grounding.py "$g"
done
python suite_scale.py acc-laya; python suite_scale.py acc-ollama; python suite_scale.py lat-laya; python suite_scale.py lat-ollama; python suite_scale.py runtime
python suite_idle.py
python analyze.py && python make_figures_tables.py
kill %1 %2 2>/dev/null || true
