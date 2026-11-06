# Laya Browser Grounding

Measurements and a small demo of [Laya-MLX](https://github.com/mizorewww/laya-mlx), a small encoder that answers "which option?" questions in one forward pass on Apple GPUs, used as an **element-grounding engine for browser automation**: given an instruction ("Tick off *Walk dog*") and the interactive elements of a page, which element should be operated?

The study is written up in [`PAPER.pdf`](PAPER.pdf) (LaTeX source in `submission/paper/`). The preprint is also on Zenodo: [10.5281/zenodo.24005550](https://doi.org/10.5281/zenodo.24005550) (code archive: [10.5281/zenodo.24004198](https://doi.org/10.5281/zenodo.24004198)).

## Headline results (Apple M2 Pro, 16 GB; details and caveats in the paper)
- With a frame-aware snapshot, Laya-ML completed every checkout step through same-origin, cross-origin and nested iframes and open shadow DOM (2/6 with a main-frame-only snapshot) and chose the right element in all 94 live-site decisions (18 distinct decisions x 5 runs, median 51 ms).
- As a general element picker it was mid-pack against a lexical matcher, bge-m3 embeddings and a local Qwen3-8B model; no accuracy difference between grounders is significant after correction, and with 40+ candidates Laya behaved like string matching.
- Its confidence was informative; escalating uncertain decisions to the LLM is a reasonable design (see paper).

## Repository layout
| Path | Content |
|---|---|
| `app/` | Laya Pilot: a small dashboard + Triage Rush demo game where Laya drives Chrome (`./run.sh`) |
| `experiments/` | the study: snapshot/grounders (`pilot.py`), fixtures, suites, analysis, raw results in `results/` |
| `submission/` | paper source, PDF, arXiv bundle inputs, submission guide, and a self-contained replication package (`submission/replication/`, generated from `experiments/`) |
| `PAPER.pdf` | the paper |

## Quick start (demo)
Needs Apple Silicon, Python 3.12, Google Chrome.
```bash
./run.sh          # creates .venv, installs laya-mlx/playwright/aiohttp, starts http://127.0.0.1:8765
```
The first start downloads the Laya checkpoint (about 0.6 GB) from Hugging Face.

## Reproducing the study
See `submission/replication/README.md` (regeneration of all tables and figures from the included raw results needs no models; re-running needs Ollama with `qwen3:8b` and `bge-m3`).

## How this was made
The code, analysis and first draft were produced with substantial assistance from an AI coding assistant (Claude, Anthropic), directed by the author; commits carry a `Co-Authored-By` trailer accordingly. Commit dates were reconstructed from the files' modification times; the work took place on 5-6 November 2026.

## Citation and license
See `CITATION.cff`. Code: MIT (`LICENSE`). Third-party material (a Wikipedia link snapshot, CC BY-SA 4.0) is noted in the replication README.
