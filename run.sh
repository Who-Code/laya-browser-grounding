#!/bin/zsh
# Laya Pilot launcher: double-click or run ./run.sh   (add --model aac6fef/laya-typed-decisions-mlx for the larger model)
cd "$(dirname "$0")"
[ -d .venv ] || { uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python laya-mlx playwright aiohttp; }
exec .venv/bin/python app/server.py "$@"
