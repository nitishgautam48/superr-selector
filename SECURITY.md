# Security

- **No data in this repository.** The data pack and everything derived from it are gitignored (`data/`, `outputs/`).
  `scripts/check_repo_safety.py` blocks CSV / Parquet / Excel / zip files, files over 2 MB and anything that looks like a
  secret; enable it as a pre-commit hook with `git config core.hooksPath scripts/git-hooks`.
- **Uploads are temporary and per session.** "Run on a data pack" processes the file in a temporary folder for that
  browser session only; it is never written to the repository, never shown to other visitors, and deleted on Clear or
  after 6 hours. The file is processed on whichever computer runs the app - only upload data you are allowed to
  process there.
- **No outbound network calls** from the pipeline or the dashboard.
- **Password gate** (`APP_PASSWORD` in `.streamlit/secrets.toml` or the hosting platform's secrets). Saving settings is
  disabled in the public build, so visitors cannot change the app for others.
- **showcase/ holds aggregates only** (made by the private project's showcase export): player-level ratings and
  summaries, reliability tables and PNG figures. It has no ball-by-ball rows, no match identifiers, no raw pack files
  and no CSVs; `scripts/check_repo_safety.py` re-checks every showcase table's columns and row count before commit.
