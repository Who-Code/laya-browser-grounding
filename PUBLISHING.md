# Publishing checklist

The repository starts **private**. Nothing here is published until you decide to.

1. **Fill the placeholders** (all in `submission/`): the repository/DOI sentence in `paper/main.tex` (red), `replication/CITATION.cff`, and the arXiv/Zenodo identifier in the root `CITATION.cff`. See `submission/SUBMISSION_GUIDE.md` for the full list and the review notes.
2. **Final read-through** of `keller-2026-laya-mlx-browser-automation.pdf`: every number against `experiments/results/`, every reference link.
3. **Rebuild the artifacts** after edits: `cd submission/paper && pdflatex main.tex && pdflatex main.tex`, then `.venv/bin/python experiments/make_figures_tables.py` if results changed, and re-zip (`arxiv_source.zip`: `main.tex`, `figures/`, `tables/`).
4. **Make the repository public** (GitHub: Settings, General, Danger Zone, Change visibility). Before that, look once at the commit history for anything you do not want public (author e-mail is the GitHub no-reply address).
5. **Zenodo DOI via GitHub** (needs a public repo): log in at zenodo.org with GitHub, switch the repository on in the GitHub settings page there, then create a release. The root `.zenodo.json` and `CITATION.cff` supply the metadata. Put the resulting DOI in the paper and rebuild.
6. **Release v1.0.0**: `git tag -a v1.0.0 -m "First public version"` and `gh release create v1.0.0 submission/keller-2026-laya-mlx-browser-automation.pdf submission/arxiv_source.zip submission/replication_package.zip --title "v1.0.0" --notes-file RELEASE_NOTES.md` (zips are git-ignored and attached as release assets).
7. **arXiv**: upload `arxiv_source.zip` (TeX source, not the PDF); abstract text is in `submission/arxiv_abstract.txt`. First-time authors need an endorsement.
