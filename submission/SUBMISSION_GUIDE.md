# Submission guide

## 1. What is in this folder
| Item | Use |
|---|---|
| `keller-2026-laya-mlx-browser-automation.pdf` | Final PDF (17 pages, built from the LaTeX source) |
| `paper/main.tex`, `paper/figures/`, `paper/tables/` | LaTeX source (tables and figures are generated from the raw results by `replication/code/make_figures_tables.py`) |
| `arxiv_source.zip` | The source bundle for arXiv; verified to compile on its own in an empty directory |
| `replication/` and `replication_package.zip` | Code, fixtures, raw results, README, license, `CITATION.cff` (for a Zenodo/GitHub deposit) |
| `arxiv_abstract.txt` | Plain-text abstract (1,664 characters) for web forms |
| `zenodo_metadata.json`, `replication/.zenodo.json` | Metadata for the paper record and the software/data record |

## 2. Status of the placeholders
Filled in: author, contributions, competing interests (none), funding (none), license holder, citation files, and the repository URL (<https://github.com/Who-Code/laya-browser-grounding>; the paper's availability sentence is only true once the repository is public).
Zenodo DOI: filled (concept DOI 10.5281/zenodo.24004198; v1.0.0 = 10.5281/zenodo.24004199). The archived v1.0.0 snapshot was taken before the DOI was written into the paper; to archive a DOI-bearing copy, publish a v1.0.1 release. Still open: the arXiv identifier, to be added after arXiv assigns it.
License choices (paper CC BY 4.0, code MIT, data CC BY 4.0) are my defaults; change them if needed.

## 3. Verify before you submit (recommended, not optional)
* **Read the whole paper and check each number against `replication/code/results/` and the paper's generated tables.** arXiv reportedly started one-year submission bans in May 2026 for papers with unchecked AI-generated content such as hallucinated references (secondary sources; confirm on arXiv's own pages).
* **References**: the three arXiv papers (ModernBERT 2412.13663, BGE M3-Embedding 2402.03216, Qwen3 2505.09388) were confirmed against arXiv (titles, first authors, dates) and all other URLs return HTTP 200 (checked 6 November 2026); the BGE-M3 title now matches the arXiv listing. Author names I could not verify were left out.
* **Related work is thin by design** and the paper says so (Limitations). Before a journal or conference submission add a proper survey of LLM web agents, GUI grounding and self-healing test automation.
* **Review round (independent read-only review plus my own audit) changed these things:** (1) the 56 checkout cases are non-discriminative, so the headline accuracy is now reported on the 88 discriminative cases as well as on all 144; (2) all intervals and tests are now instruction-level (38 distinct instructions), and with all 15 pairs and Holm adjustment **no accuracy difference between grounders is significant** (the earlier draft's "McNemar" claims were too strong); (3) the scaling result at large N turned out to be literal-vs-natural: Laya-ML behaves like the lexical matcher there; (4) the claim that long lists are truncated was wrong (660 of 1,024 tokens at N=160) and was removed; (5) the paper now says the executed suites used Laya-ML only, that "94/94" is 18 distinct decisions repeated five times, that Laya did not beat scripted tests overall, that latencies are indicative (swap/contention caveat), and defines all terms in the Introduction; (6) stale artifacts were rebuilt.
* Live-site results can change with the sites; the checkbox click timeout seen in three live runs could not be reproduced (8 isolated attempts), so its cause is undetermined.

## 4. Where to submit, and what each needs (from the sources I could check)
**arXiv.** Submit the **TeX source** (`arxiv_source.zip`): arXiv accepts a PDF only when it was *not* produced from TeX/LaTeX, so do not upload `keller-2026-laya-mlx-browser-automation.pdf` instead. First-time authors need an **endorsement** for the category (an institutional e-mail alone no longer suffices since January 2026). Suggested categories (moderators may change them): primary **cs.SE** or **cs.AI**, cross-list **cs.HC**. Suggested comments: "14 pages, 4 figures; code and data: <DOI>". Use `arxiv_abstract.txt` for the abstract. Sources are secondary summaries, so confirm at <https://info.arxiv.org/help/submit/>.

**Zenodo** (gives a citable DOI, no endorsement). Create two records: (a) the paper (`keller-2026-laya-mlx-browser-automation.pdf`, upload type Publication, subtype Preprint, metadata from `zenodo_metadata.json`), (b) `replication_package.zip` (upload type Software or Dataset, `replication/.zenodo.json`). Required fields reported by community guides: title, description, upload type, creators, access rights, license. Publish (b) first, put its DOI into the paper's availability statement and `CITATION.cff`, rebuild, then publish (a). Files can only be changed for a short period after publishing; later changes need a new version.

**OSF Preprints, SSRN, ResearchGate, TechRxiv** and similar: I did not research their rules. Typical requirements are the PDF, title, abstract, author list with affiliations, keywords and a license; check each site's current policy, especially on AI-assisted content and on whether they take a paper already on arXiv.

**Peer-reviewed venues**: this is a measurement paper on one machine with small samples; expect reviewers to ask for more suites, stronger LLM baselines, other hardware and the broader related work.

## 5. Privacy / file-system scrub
Done: code now uses relative paths (no absolute home-directory paths), the Markdown/HTML drafts that contained them were deleted, PDF author metadata is empty, and the replication package was built from sanitized copies. Verified by searching all files in `submission/` (including inside both zip files and the PDFs) for the user name, home-directory prefixes, project-folder names, e-mail addresses and temporary-directory prefixes: no matches (see the result of the final scan in the conversation). Deliberately kept: hardware model (Apple M2 Pro, 16 GB), software versions, Hugging Face revision hashes and Ollama digests (needed for reproducibility).

## 6. Changes relative to the earlier draft (`PAPER.md`, now deleted)
Reformatted as a LaTeX paper with abstract, keywords, numbered references, four figures, declarations, ethics and availability statements, appendices with exact prompts and instruction sets; corrected the significance claims (section 3); removed unverified reference authors; removed all repository paths; added instruction-level statistics and an explicit LOGO cascade table.
