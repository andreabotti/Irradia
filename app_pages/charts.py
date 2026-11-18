"""Charts page: monthly totals and the hourly profile over the year."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st

# the browser has Ronzino from the app theme, so the charts can ask for it too
FONT = dict(family="Ronzino, system-ui, sans-serif")

ctx = st.session_state["ctx"]
res, MONTHS = ctx["res"], ctx["months"]

st.subheader("Monthly")
fig = go.Figure()
fig.add_bar(x=MONTHS, y=res["monthly_unshaded"], name="Unshaded", marker_color="#9aa5ad")
fig.add_bar(x=MONTHS, y=res["monthly_shaded"], name="With shading", marker_color="#ea7b00")
fig.update_layout(barmode="group", height=360, margin=dict(l=10, r=10, t=30, b=10),
                  font=FONT,
                  yaxis_title="kWh/m² (glazing average)", legend=dict(orientation="h", y=1.12))
st.plotly_chart(fig, width="stretch", alt="Monthly incident radiation on the glazing, "
                                          "unshaded against shaded")

st.subheader("Hourly")
grid_h = np.full((24, 365), np.nan)
h = res["hours"]
grid_h[h % 24, h // 24] = res["hourly_shaded"]
fig = go.Figure(go.Heatmap(z=grid_h, colorscale=[[i / 9, c] for i, c in enumerate(
    ["#4b6ba9", "#7393ca", "#aac8f7", "#c1d5d0", "#f5ef67", "#fce64a",
     "#ef9c15", "#ea7b00", "#ea4a00", "#ea2600"])],
    colorbar=dict(title="W/m²"), hoverongaps=False))
fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10), font=FONT,
                  xaxis_title="Day of year", yaxis_title="Hour")
st.plotly_chart(fig, width="stretch", alt="Shaded irradiance on the glazing for every hour of the year")

st.caption(f"Beam and circumsolar share of incident radiation: {100 * res['beam_share']:.0f}%")
