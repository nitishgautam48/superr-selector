"""Overview: KPIs and the two top-10 boards (model vs final)."""
from __future__ import annotations

import streamlit as st

from app import boards, components as C, data as D

dq, rep, sep, meta = D.js("data_quality.json"), D.js("wp_model_report.json"), D.js("pressure_separation.json"), D.js("run_meta.json")
fl = D.js("final_lists.json")
bat, bowl = D.rated("batter"), D.rated("bowler")
C.page_header("RR Pressure Index", "Who performs best when the game is on the line - IPL and T20I, 2022-2026",
              [("Your uploaded pack" if D.upload_dir() else "Real data pack", "success")]
              + ([] if (D.showcase_mode() or D.public_mode()) else [("Model proposes · you decide", "neutral")]))
rc = dq.get("row_counts", {})
C.kpi_row([C.kpi_tile_html("Matches", f"{rc.get('matches_with_balls', 0):,}"),
           C.kpi_tile_html("Balls", f"{rc.get('regular_balls', 0):,}"),
           C.kpi_tile_html("High-pressure balls", f"{sep.get('leverage', {}).get('high', {}).get('share_pct', 0):.1f}%",
                           help="Top 20% of the pressure index"),
           C.kpi_tile_html("Eligible batters", f"{int(bat['eligible'].sum())}"),
           C.kpi_tile_html("Eligible bowlers", f"{int(bowl['eligible'].sum())}"),
           C.kpi_tile_html("WP model Brier", f"{rep.get('summary', {}).get('brier_weighted', 0):.3f}",
                           help="Lower is better; no-skill = 0.25")])
_mlab = "Model (RR targets)" if D.cfg().get("rr_target.use_for_final", False) else "Model"
view = st.segmented_control("List", ["Final", _mlab, "Pure pressure"], default="Final", key="ov_view")
key = {"Final": "final", _mlab: "model", "Pure pressure": "pure_pressure"}.get(view, "final")
st.caption(f"{'Ranking' if (D.showcase_mode() or D.public_mode()) else 'Submission list'} basis: {fl.get('list_basis', 'pure pressure rating')}.")
changes = sum(len(fl.get(f"{r}s_changes", [])) for r in ("batter", "bowler"))
st.caption(("Final = model ranking plus the analyst's logged decisions (see My decisions). " if (D.showcase_mode() or D.public_mode())
            else "Final = model plus your logged decisions (Player profile → Analyst decision). ")
           + f"{changes} model pick(s) changed.")
with C.pair_grid("ov_boards"):
    with st.container():
        C._show(boards.board_html("Top 10 batters under pressure", fl.get(f"batters_{key}", fl.get("batters_model", [])), bat, key == "final"))
    with st.container():
        C._show(boards.board_html("Top 10 bowlers under pressure", fl.get(f"bowlers_{key}", fl.get("bowlers_model", [])), bowl, key == "final"))
st.caption("Labels: ★ Robust = top 10 in ≥ 80% of 1,000 match resamples and of sensitivity variants · ◆ Likely ≥ 50% · "
           "○ Sensitive < 50%. Rank 80% = bootstrap interval.")
