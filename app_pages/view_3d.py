"""3D view page: the facade, its shading and the incident radiation on the glazing."""
import numpy as np
import streamlit as st

from components.viewer import render_viewer

ctx = st.session_state["ctx"]
scene, res = ctx["scene"], ctx["res"]

# the entry script opens a column for this page, with the shading panel to its left
with ctx.get("main") or st.container():
    mode = st.segmented_control("Show", ["With shading (kWh/m²)", "Reduction (%)", "Geometry only"],
                                default="With shading (kWh/m²)", label_visibility="collapsed")

    # caption removed: reclaim that space into the viewer while staying under 1080p
    view_h = 600
    if mode == "Reduction (%)":
        rr = 100 * (1 - res["shaded"] / np.maximum(res["unshaded"], 1e-9))
        render_viewer(scene, rr, 0, 100, "% reduction", suns=ctx["suns"], paths=ctx["paths"],
                      azimuth=ctx["az"], height=view_h)
    elif mode == "Geometry only":
        render_viewer(scene, suns=ctx["suns"], paths=ctx["paths"], azimuth=ctx["az"], height=view_h)
    else:
        render_viewer(scene, res["shaded"], 0, max(res["unshaded"].max(), 1), "kWh/m²",
                      suns=ctx["suns"], paths=ctx["paths"], azimuth=ctx["az"], height=view_h)
