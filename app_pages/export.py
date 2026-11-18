"""Export page: grid and hourly results, geometry and the parameter set."""
import pandas as pd
import streamlit as st

from engine.geometry import scene_to_obj

ctx = st.session_state["ctx"]
scene, res = ctx["scene"], ctx["res"]

pts = scene["points"]
df = pd.DataFrame({"x_m": pts[:, 0], "z_m": pts[:, 2], "unshaded_kWh_m2": res["unshaded"],
                   "shaded_kWh_m2": res["shaded"],
                   # absolute SVF = diffuse ratio × (1+cos β)/2; vertical β → ×0.5
                   "sky_view_factor": 0.5 * res["svf"],
                   "diffuse_sky_ratio": res["svf"],
                   "ground_view_ratio": res["gvf"]})
hourly = pd.DataFrame({"hoy": res["hours"], "unshaded_W_m2": res["hourly_unshaded"],
                       "shaded_W_m2": res["hourly_shaded"]})

with st.container(horizontal=True):
    st.download_button("Grid results (CSV)", df.to_csv(index=False), "grid_results.csv", "text/csv")
    st.download_button("Hourly results (CSV)", hourly.to_csv(index=False), "hourly_results.csv", "text/csv")
    st.download_button("Geometry (OBJ)", scene_to_obj(scene), "facade_shading.obj", "text/plain")
    st.download_button("Parameters (JSON)", ctx["params_json"], "parameters.json", "application/json")

st.subheader("Grid results")
st.dataframe(df, width="stretch", height=320,
             alt="One row per analysis point, with unshaded and shaded radiation and view factors")

st.subheader("Hourly results")
st.dataframe(hourly, width="stretch", height=320,
             alt="One row per sunlit hour, with unshaded and shaded irradiance")
