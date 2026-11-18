"""Shading device controls, rendered either in the sidebar or beside the 3D view."""
import streamlit as st


def shading_controls(fw, fh, margin):
    """The three shading families as a tab strip; returns their parameter dicts.

    The widget keys are fixed, so the settings survive this block moving between the
    sidebar and the panel next to the viewer when the page changes.
    """
    # which families are on, as a caption: the tab labels stay fixed, because changing a
    # label remounts the tab strip and would throw you back to the first tab on every toggle
    on_now = [n for n, k, d in (("louvres", "L_on", True), ("overhang", "O_on", False),
                                ("fins", "F_on", False)) if st.session_state.get(k, d)]
    st.caption("On: " + (", ".join(on_now) if on_now else "nothing — the glazing is unshaded"))
    tab_louvre, tab_over, tab_fin = st.tabs(["Louvres", "Overhang", "Fins"])

    with tab_louvre:
        L_on = st.toggle("Enable", True, key="L_on")
        L_depth = st.slider("Depth (m)", 0.05, 1.5, 0.30, 0.01, key="L_d")
        L_tilt = st.slider("Tilt (°, + downward)", -60, 60, 0, 1, key="L_t")
        L_sp = st.slider("Spacing (m)", 0.05, 2.0, 0.35, 0.01, key="L_s")
        L_z = st.slider("From / to height (m)", 0.0, float(fh),
                        (min(0.9, float(fh)), min(2.9, float(fh))), 0.05, key="L_z")
        L_off = st.slider("Offset from glass (m)", 0.0, 1.0, 0.10, 0.01, key="L_o")
        L_ext = st.slider("Side extension (m)", 0.0, 2.0, 0.0, 0.05, key="L_e")

    with tab_over:
        O_on = st.toggle("Enable", False, key="O_on")
        O_depth = st.slider("Depth (m)", 0.1, 3.0, 1.0, 0.05, key="O_d")
        O_tilt = st.slider("Tilt (°, + downward)", -45, 45, 0, 1, key="O_t")
        O_gap = st.slider("Height above head (m)", 0.0, 1.5, 0.1, 0.05, key="O_g")
        O_off = st.slider("Offset from glass (m)", 0.0, 1.0, 0.0, 0.01, key="O_o")
        O_ext = st.slider("Side extension (m)", 0.0, 3.0, 0.3, 0.05, key="O_e")

    with tab_fin:
        F_on = st.toggle("Enable", False, key="F_on")
        F_depth = st.slider("Depth (m)", 0.05, 1.5, 0.30, 0.01, key="F_d")
        F_ang = st.slider("Rotation (°, + toward right)", -75, 75, 0, 1, key="F_a")
        F_sp = st.slider("Spacing (m)", 0.1, 3.0, 0.5, 0.05, key="F_s")
        F_x = st.slider("From / to position (m)", 0.0, float(fw),
                        (float(margin), float(fw - margin)), 0.05, key="F_x")
        F_ext = st.slider("Extension below / above glazing (m)", 0.0, 1.0, (0.0, 0.0), 0.05, key="F_e")
        F_off = st.slider("Offset from glass (m)", 0.0, 1.0, 0.05, 0.01, key="F_o")

    return {
        "louvres": dict(on=L_on, depth=L_depth, tilt=L_tilt, spacing=L_sp, z_start=L_z[0],
                        z_end=L_z[1], offset=L_off, ext=L_ext),
        "overhang": dict(on=O_on, depth=O_depth, tilt=O_tilt, gap=O_gap, ext=O_ext, offset=O_off),
        "fins": dict(on=F_on, depth=F_depth, angle=F_ang, spacing=F_sp, x_start=F_x[0],
                     x_end=F_x[1], ext_bottom=F_ext[0], ext_top=F_ext[1], offset=F_off),
    }
