# Facade solar radiation (Streamlit)

Incident solar radiation on a glazed facade with parametric shading
(horizontal louvres, overhang, vertical fins). Uses Ladybug Tools
(`ladybug-core`) for EPW, sun path and analysis periods, `pvlib` for the
Perez sky split, and vectorised NumPy ray tests for shading. The 3D viewer
is three.js, loaded from a CDN, so there is no JavaScript build step.

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud
1. Create a GitHub repo and push this folder (keep `sample/chicago.epw`).
2. Go to share.streamlit.io, choose **Create app**, then pick the repo, branch and `app.py`.
3. Under Advanced settings, choose Python 3.11 or 3.12, then **Deploy**.

## Embed on absrd.xyz
```html
<iframe src="https://YOUR-APP.streamlit.app/?embed=true"
        style="width:100%;height:1000px;border:0" loading="lazy"></iframe>
```

## Structure
```
app.py                 UI and orchestration
engine/climate.py      EPW, sun positions, analysis period, Perez components
engine/geometry.py     facade, glazing grid, parametric shading rectangles, OBJ export
engine/radiation.py    occlusion tests and integration
components/viewer.py   three.js viewer (st.iframe)
```

## Method and limits
Beam and circumsolar radiation are blocked hourly by ray tests toward the sun.
Isotropic sky and ground-reflected radiation are scaled by cosine-weighted
visibility of the 145 Tregenza patches. Shading elements are thin, opaque and
non-reflective. There is no surrounding context, and night diffuse is ignored.
