"""Method page: what the calculation does and what it assumes."""
import streamlit as st

st.markdown(
    "Weather, sun positions and analysis periods use **Ladybug Tools** (`ladybug-core`). "
    "Sky diffuse is split with the **Perez** model (`pvlib`) into isotropic, circumsolar and horizon parts. "
    "Beam and circumsolar radiation are blocked per hour by ray tests from every grid point toward the sun. "
    "Isotropic sky and ground-reflected radiation are scaled by each point's **diffuse shading "
    "coefficient**: the cosine-weighted visibility of the 145 Tregenza sky patches (and their ground "
    "mirror) relative to the unobstructed façade. The reported **Sky View Factor** is that ratio times "
    "$(1+\\cos\\beta)/2$ (0.5 for vertical glazing), i.e. the isotropic view factor to the sky.")

st.subheader("Assumptions")
st.markdown(
    "- Shading elements are thin, opaque plates with no reflections.\n"
    "- The wall extends indefinitely in its own plane, with no surrounding buildings.\n"
    "- Night-time diffuse radiation is ignored.\n"
    "- The sunpath diagram shows the solstice and equinox day arcs with an analemma for each hour, "
    "sampled every third day.")
