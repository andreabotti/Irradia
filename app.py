"""Facade incident solar radiation with parametric shading.
Ladybug Tools (EPW, Sunpath, AnalysisPeriod) + pvlib Perez + NumPy ray tests."""
import hashlib
import json
import urllib.request
from pathlib import Path

import numpy as np
import streamlit as st

from components.controls import shading_controls
from components.metrics import render_metrics
from components.viewer import render_viewer
from engine.climate import load_epw_bytes, period_hours, sky_components, sun_positions
from engine.geometry import build_scene, to_local
from engine.radiation import compute

st.set_page_config(page_title="Facade solar radiation", page_icon="☀️", layout="wide")
SAMPLE = Path(__file__).parent / "sample" / "chicago.epw"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS_IN = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


# ---------------------------------------------------------------- caching
@st.cache_data(show_spinner=False)
def fetch_url(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


@st.cache_data(show_spinner="Reading weather file…")
def climate_from_bytes(data: bytes):
    clim = load_epw_bytes(data)
    return clim, sun_positions(clim)


@st.cache_data(show_spinner="Calculating radiation…")
def run_analysis(epw_hash, _clim, _sun, period, azimuth, albedo, params_json):
    params = json.loads(params_json)
    hours = period_hours(*period)
    comps = sky_components(_clim, _sun, hours, azimuth, albedo)
    scene = build_scene(params)
    return compute(scene, comps, azimuth)


@st.cache_data(show_spinner=False)
def sunpath_paths(epw_hash, _sun, azimuth):
    """Sunpath diagram as polylines of unit sun vectors in facade-local coordinates:
    day arcs for the solstices and the equinox, plus an analemma for each hour."""
    vec, alt = to_local(_sun["vec"], azimuth), _sun["alt"]
    out = []

    def add(idx, kind):
        seg = []
        for i in idx:
            if alt[i] > 0:
                seg.append([round(float(c), 4) for c in vec[i]])
            else:
                if len(seg) > 1:
                    out.append({"kind": kind, "pts": seg})
                seg = []
        if len(seg) > 1:
            out.append({"kind": kind, "pts": seg})

    for day in (354, 79, 171):          # 21 Dec, 21 Mar, 21 Jun
        add(range(day * 24, day * 24 + 24), "day")
    for hour in range(24):              # analemma per hour, sampled every third day
        add(range(hour, 8760, 24 * 3), "hour")
    return out


CUM_DAYS = np.cumsum([0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])


def hoy_label(h):
    """Hour of the year (0-8759) as '21 Jun · 13:00', the hour it begins."""
    day, hour = int(h) // 24, int(h) % 24
    m = int(np.searchsorted(CUM_DAYS, day, side="right"))
    return f"{day - CUM_DAYS[m - 1] + 1} {MONTHS[m - 1]} · {hour:02d}:00"


def compass(az):
    names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return names[int(((az % 360) + 22.5) // 45) % 8]


# -------------------------------------------------------------- navigation
# declared before anything is drawn: on the 3D page the shading controls move out of
# the sidebar into a panel beside the viewer, so the layout depends on the selection
nav = st.navigation([
    st.Page("app_pages/view_3d.py", title="3D view", icon=":material/view_in_ar:", default=True),
    st.Page("app_pages/charts.py", title="Charts", icon=":material/bar_chart:"),
    st.Page("app_pages/export.py", title="Export", icon=":material/download:"),
    st.Page("app_pages/method.py", title="Method", icon=":material/function:"),
], position="top")
on_3d = nav.title == "3D view"

# ---------------------------------------------------------------- sidebar
sb = st.sidebar

sb_tabs = sb.tabs(["Climate", "Facade"] if on_3d else ["Climate", "Facade", "Shading"])
tab_climate, tab_facade = sb_tabs[0], sb_tabs[1]
tab_shading = None if on_3d else sb_tabs[2]

with tab_climate:
    src = st.radio("Weather file", ["Sample (Chicago)", "Upload EPW", "EPW / zip URL"],
                   label_visibility="collapsed")
    epw_bytes = None
    if src == "Upload EPW":
        f = st.file_uploader("EPW or zipped EPW", type=["epw", "zip"])
        if f:
            epw_bytes = f.getvalue()
    elif src == "EPW / zip URL":
        url = st.text_input("URL", placeholder="https://climate.onebuilding.org/…/ITA_ER_Bologna….zip",
                            help="Direct link to an .epw or a .zip from climate.onebuilding.org")
        if url:
            try:
                epw_bytes = fetch_url(url)
            except Exception as e:
                st.error(f"Download failed: {e}")
    else:
        epw_bytes = SAMPLE.read_bytes()

    preset = st.selectbox("Analysis period", ["Annual", "Summer (Jun–Aug)", "Winter (Dec–Feb)",
                                              "Cooling season (May–Sep)", "Custom"])
    if preset == "Custom":
        c1, c2 = st.columns(2)
        sm = c1.selectbox("From month", MONTHS, index=5); em = c2.selectbox("To month", MONTHS, index=7)
        smi, emi = MONTHS.index(sm) + 1, MONTHS.index(em) + 1
        sd = c1.number_input("From day", 1, DAYS_IN[smi - 1], 1)
        ed = c2.number_input("To day", 1, DAYS_IN[emi - 1], DAYS_IN[emi - 1])
        sh, eh = st.slider("Hours of day", 0, 23, (8, 18))
        period = (smi, int(sd), sh, emi, int(ed), eh)
    else:
        period = {"Annual": (1, 1, 0, 12, 31, 23), "Summer (Jun–Aug)": (6, 1, 0, 8, 31, 23),
                  "Winter (Dec–Feb)": (12, 1, 0, 2, 28, 23),
                  "Cooling season (May–Sep)": (5, 1, 0, 9, 30, 23)}[preset]
    albedo = st.slider("Ground albedo", 0.0, 0.8, 0.2, 0.05)

with tab_facade:
    c1, c2 = st.columns(2)
    fw = c1.number_input("Width (m)", 1.0, 30.0, 6.0, 0.5)
    fh = c2.number_input("Height (m)", 1.0, 20.0, 3.5, 0.1)
    az = st.slider("Orientation (azimuth of normal, °)", 0, 359, 180,
                   help="0 = north, 90 = east, 180 = south, 270 = west")
    st.caption(f"Facing {compass(az)}")
    st.subheader("Glazing and grid", divider="gray")
    max_margin = max(0.05, fw / 2 - 0.1)
    margin = st.number_input("Side margin (m)", 0.0, max_margin, min(0.5, max_margin), 0.05)
    sill, head = st.slider("Sill / head height (m)", 0.0, float(fh), (0.8, min(2.9, float(fh))), 0.05)
    grid = st.select_slider("Grid size (m)", [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.5], 0.2)

# ------------------------------------------------------------------ main
st.title("Facade solar radiation")
# filled in once the scene and the results exist, further down this script
caption_slot = st.empty()
metrics_slot = st.container()

if on_3d:
    panel, main_area = st.columns([0.24, 0.76], gap="large", vertical_alignment="top")
else:
    panel, main_area = tab_shading, st.container()

# the shading widgets must run before the scene is built, whichever column they sit in
with panel:
    if on_3d:
        st.markdown("##### Shading")
    shading = shading_controls(fw, fh, margin)

params = {
    "facade_width": fw, "facade_height": fh, "win_margin": margin,
    "win_sill": sill, "win_head": head, "grid": grid,
    **shading,
}
params_json = json.dumps(params, sort_keys=True)
scene = build_scene(params)

if epw_bytes is None:
    with main_area:
        st.info("Add a weather file in the sidebar to start: upload an EPW or paste a "
                "link from climate.onebuilding.org.")
        render_viewer(scene, azimuth=az)
    st.stop()

try:
    clim, sun = climate_from_bytes(epw_bytes)
except Exception as e:
    st.error(f"This file could not be read as an EPW: {e}")
    st.stop()

epw_hash = hashlib.md5(epw_bytes).hexdigest()
caption_slot.caption(
    f"{clim['city']}, {clim['country']} · lat {clim['latitude']:.2f}, lon {clim['longitude']:.2f} · "
    f"facade facing {compass(az)} ({az}°) · {len(scene['quads'])} shading elements · "
    f"{len(scene['points'])} analysis points")

# cost of the beam ray tests: one test per grid point, shading element and sunlit hour
hrs_all = period_hours(*period)
hrs = hrs_all[sun["alt"][hrs_all] > 0.5]
ray_tests = len(scene["points"]) * max(len(scene["quads"]), 1) * max(len(hrs), 1)
if ray_tests > 50_000_000:
    st.warning(f"Heavy combination of grid, shading elements and period "
               f"({ray_tests / 1e6:,.0f}M ray tests): the first run may take several seconds. "
               f"Increase the grid size if it is slow.")

res = run_analysis(epw_hash, clim, sun, period, az, albedo, params_json)
paths = sunpath_paths(epw_hash, sun, az)

if len(res["hours"]) == 0:
    with main_area:
        st.warning("This period contains no daylight hours. Widen the months or the hours of day.")
        render_viewer(scene, paths=paths, azimuth=az)
    st.stop()

# sun positions shown in the viewer (front hemisphere, subsampled)
sl = to_local(sun["vec"][hrs], az)
sl = sl[sl[:, 1] > 0][:: max(1, len(sl) // 700)]

mean_s, mean_u = res["shaded"].mean(), res["unshaded"].mean()
red = 100 * (1 - mean_s / mean_u) if mean_u > 0 else 0

# average irradiance the way the Ladybug components report it: cumulative radiation
# spread over every hour of the analysis period, night hours included
n_period = max(len(hrs_all), 1)
avg_s, avg_u = 1000 * mean_s / n_period, 1000 * mean_u / n_period

# peak hourly irradiance and when it happens, with the upper tail of the same series
hourly = res["hourly_shaded"]
peak_i = int(np.argmax(hourly))
peak_when = hoy_label(int(res["hours"][peak_i]))
p95, p975 = (float(v) for v in np.percentile(hourly, [95, 97.5]))

with metrics_slot:
    render_metrics([
        {
            "group": "Cumulative Solar Energy",
            "narrow": True,
            "spaced": True,
            "tiles": [
                {"label": "Unshaded", "value": f"{mean_u:,.0f}", "unit": "kWh/m²",
                 "note": "avg over glazing surface",
                 "hint": "Incident radiation on the glazing with no shading"},
                {"label": "With Shading", "value": f"{mean_s:,.0f}", "unit": "kWh/m²",
                 "note": f"−{red:.1f}% vs unshaded", "tone": "good" if red > 0 else "",
                 "hint": "Incident radiation on the glazing with the shading devices in place"},
            ],
        },
        {
            "group": "Avg irradiance",
            "narrow": True,
            "spaced": True,
            "tiles": [
                {"label": "Unshaded", "value": f"{avg_u:,.0f}", "unit": "W/m²",
                 "note": f"over {n_period:,} period hours",
                 "hint": f"Average irradiance as the Ladybug components report it: the "
                         f"cumulative radiation divided by the {n_period:,} hours of the "
                         f"analysis period, night hours included"},
                {"label": "With Shading", "value": f"{avg_s:,.0f}", "unit": "W/m²",
                 "note": f"−{red:.1f}% vs unshaded", "tone": "good" if red > 0 else "",
                 "hint": f"Average irradiance with shading, over the {n_period:,} hours of "
                         f"the analysis period, night hours included"},
            ],
        },
        {
            "group": "Peak Values",
            "spaced": True,
            "tiles": [
                {"label": "Max Value", "value": f"{hourly.max():,.0f}", "unit": "W/m²",
                 "note": peak_when, "tone": "warn",
                 "hint": f"Highest hourly irradiance of the period, in the hour beginning {peak_when}"},
                {"label": "97.5th Perc.", "value": f"{p975:,.0f}", "unit": "W/m²",
                 "note": f"{round(len(hourly) * 0.025):,} hours (2.5% of the period)\nhave higher values",
                 "hint": "97.5th percentile of hourly irradiance, sunlit hours only: "
                         "the level exceeded in 2.5% of them"},
                {"label": "95th Perc.", "value": f"{p95:,.0f}", "unit": "W/m²",
                 "note": f"{round(len(hourly) * 0.05):,} hours (5% of the period)\nhave higher values",
                 "hint": "95th percentile of hourly irradiance, sunlit hours only: "
                         "the level exceeded in 5% of them"},
            ],
        },
        # res["svf"] is the diffuse shading coefficient (unshaded = 1). Absolute sky
        # view factor for a vertical surface is that times Fsu = (1+cos 90°)/2 = 0.5.
        {"label": "Sky View Factor",
         "value": f"{50 * res['svf'].mean():.0f}", "unit": "% avg over the grid",
         "value2": "50", "unit2": "% when unshaded",
         "hint": "View factor from the glazing to the sky (isotropic assumption). "
                 "Unshaded vertical glazing = 50%. Scaled from the cosine-weighted "
                 "Tregenza sky visibility ratio"},
    ])

# everything the pages need, computed once per rerun in this entry script
st.session_state["ctx"] = {
    "scene": scene, "res": res, "paths": paths, "suns": sl,
    "params_json": params_json, "months": MONTHS, "az": az, "main": main_area,
}

nav.run()
