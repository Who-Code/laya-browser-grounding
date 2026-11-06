#!/bin/zsh
# each grounder alone in its own process; Ollama models unloaded before the Laya runs
cd "$(dirname "$0")/.."
for g in laya-ml-choice laya-td-choice laya-td-pointwise lexical "embed(bge-m3)" "llm(qwen3:8b)"; do
  [[ $g == laya* ]] && { ollama stop qwen3:8b >/dev/null 2>&1; ollama stop bge-m3 >/dev/null 2>&1; }
  .venv/bin/python experiments/run_grounding.py "$g" 2>&1 | grep -E "acc " 
done
echo ALLDONE
