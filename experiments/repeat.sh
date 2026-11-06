#!/bin/zsh
cd "$(dirname "$0")/.."
R=experiments/results; mkdir -p $R/runs
for k in 1 2 3 4 5; do
  .venv/bin/python experiments/suite_live.py >/dev/null 2>&1; cp $R/live.json $R/runs/live_$k.json
done
for k in 1 2 3; do
  .venv/bin/python experiments/suite_todo.py >/dev/null 2>&1; cp $R/todo.json $R/runs/todo_$k.json
  .venv/bin/python experiments/suite_shop.py >/dev/null 2>&1; cp $R/shop.json $R/runs/shop_$k.json
done
echo REPEATDONE
