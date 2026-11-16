"""Run on a data pack: upload the SupeRR Selector data pack (zip) and reproduce every result in this session."""
from __future__ import annotations

import shutil
import tempfile
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from app import components as C, data as D
from pressure import run as R
from pressure.config import load_config
from pressure.datapack import extract

TMP_PREFIX = "superr_upload_"
MAX_AGE_H = 6

C.page_header("Run on a data pack", "Upload the SupeRR Selector data pack and the full model runs on it - same "
              "method, same settings, same results.")
st.warning("Your file is processed on the computer that runs this app (your own PC when run locally; the hosting "
           "provider's server when hosted). It is kept in a temporary folder for your session only - never added to "
           "the repository, never visible to other visitors - and deleted when you press Clear (or after "
           f"{MAX_AGE_H} hours). Only upload data you are allowed to process here.", icon=":material/shield:")

# housekeeping: remove other sessions' stale temp folders
for d in Path(tempfile.gettempdir()).glob(TMP_PREFIX + "*"):
    if time.time() - d.stat().st_mtime > MAX_AGE_H * 3600:
        shutil.rmtree(d, ignore_errors=True)

cur = D.upload_dir()
if cur:
    meta = D.js("run_meta.json")
    m = meta.get("metrics", {})
    st.success(f"Every page now shows results from your uploaded pack (run {C.fmt_run_at(meta.get('run_at'))}).",
               icon=":material/check_circle:")
    C.kpi_row([C.kpi_tile_html("Winner reconstruction", f"{m.get('winner_accuracy_pct', 0)}%"),
               C.kpi_tile_html("WP model Brier", f"{m.get('wp_brier', 0):.4f}"),
               C.kpi_tile_html("High-pressure balls", f"{m.get('pressure_share_pct', 0)}%"),
               C.kpi_tile_html("Eligible batters", f"{m.get('eligible_batters', 0)}"),
               C.kpi_tile_html("Eligible bowlers", f"{m.get('eligible_bowlers', 0)}")])
    st.page_link("views/1_Overview.py", label="Open the Overview →", icon=":material/arrow_forward:")
    if st.button("Clear uploaded results (delete the temporary copy)", key="up_clear"):
        shutil.rmtree(cur, ignore_errors=True)
        st.session_state.pop("upload_dir", None)
        st.cache_data.clear()
        st.rerun()
    st.stop()

quick_mode = st.toggle("Quick run (recommended on hosted servers)", value=D.public_mode(), key="up_quick",
                       help="Same method, same chosen model and the same rankings; fits only the chosen win-probability model "
                            "and uses 300 bootstrap resamples instead of 1,000 for the rank intervals. "
                            "About half the computing time.")
f = st.file_uploader("Data pack (.zip) - the file as downloaded from Unstop", type=["zip"], key="up_file")
st.caption("Needs the six CSVs: ball_by_ball, matches, competitions, teams, playing_eleven, "
           "competition_team_player_mapping. Folder names and download prefixes are handled automatically.")
if f is not None and st.button("Run the model", type="primary", key="up_run"):
    root = Path(tempfile.mkdtemp(prefix=TMP_PREFIX))
    try:
        with st.spinner("Reading the pack…"):
            status = extract(f, root / "raw")
        st.dataframe(pd.DataFrame([{"File": f"{k}.csv", "Found": s["present"], "Rows": s["rows"],
                                    "Official pack rows": s["expected"]} for k, s in status.items()]),
                     hide_index=True, width="stretch")
        missing = [k for k, s in status.items() if not s["present"]]
        if missing:
            raise ValueError(f"missing file(s): {', '.join(missing)}")
        if not all(s["matches_official_pack"] for s in status.values()):
            st.info("Row counts differ from the official pack: results will differ from ours accordingly.",
                    icon=":material/info:")
        cfg = load_config().with_overrides(**D.upload_paths(root))
        if quick_mode:
            cfg = R.quick(cfg)
        bar = st.progress(0.0, text="Starting…")
        labels = {"data": "Reconstructing scores", "pressure": "Win-probability model and pressure",
                  "rating": "Baselines and ratings", "reliability": "Bootstrap, sensitivity and figures",
                  "rr_target": "RR needs and auction targets"}
        t_start = time.time()

        def prog(name, i, n):
            txt = labels.get(name, name) if ":" not in name else name.split(":", 1)[1].strip()
            bar.progress(min(i / n + 0.01, 0.99), text=f"Step {i + 1}/{n}: {txt}… ({time.time() - t_start:.0f}s)")
        R.run(cfg, progress=prog)
        bar.progress(1.0, text="Done")
        st.session_state["upload_dir"] = str(root)
        st.cache_data.clear()
        st.rerun()
    except Exception as exc:  # noqa: BLE001
        shutil.rmtree(root, ignore_errors=True)
        st.error(f"The run failed: {type(exc).__name__}: {exc}", icon=":material/error:")
