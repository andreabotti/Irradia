"""three.js 3D viewer rendered inside a Streamlit HTML component (no build step)."""
import json

import numpy as np
import streamlit as st
import streamlit.components.v1 as components

# Ladybug Tools default legend colours
LB_COLORS = np.array([
    (75, 107, 169), (115, 147, 202), (170, 200, 247), (193, 213, 208),
    (245, 239, 103), (252, 230, 74), (239, 156, 21), (234, 123, 0),
    (234, 74, 0), (234, 38, 0)], dtype=float)


def colorize(values, vmin, vmax):
    t = np.clip((np.asarray(values) - vmin) / max(vmax - vmin, 1e-9), 0, 1)
    pos = t * (len(LB_COLORS) - 1)
    i = np.minimum(pos.astype(int), len(LB_COLORS) - 2)
    f = (pos - i)[:, None]
    rgb = LB_COLORS[i] * (1 - f) + LB_COLORS[i + 1] * f
    return ["#%02x%02x%02x" % tuple(c) for c in rgb.astype(int)]


HTML = r"""
<div id="wrap">
  <div id="bar">
   <div class="row">
    <span class="grp" title="Viewpoint">
      <button data-view="se" title="From the south-east (1)">SE</button>
      <button data-view="sw" title="From the south-west (2)">SW</button>
      <button data-view="ne" title="From the north-east (3)">NE</button>
      <button data-view="nw" title="From the north-west (4)">NW</button>
      <button data-view="front" title="Front view, from outside (F)">Front</button>
      <button data-view="side" title="Side view (S)">Side</button>
      <button data-view="top" title="Top view (T)">Top</button>
    </span>
    <span class="grp" title="Projection">
      <button id="p-persp" class="on" title="Perspective projection (O)">Persp</button>
      <button id="p-ortho" title="Orthographic projection (O)">Ortho</button>
    </span>
    <span class="grp" title="Background">
      <button id="b-dark" class="on" title="Dark background (B)">Dark</button>
      <button id="b-light" title="White background (B)">Light</button>
    </span>
    <span class="grp" title="Shading devices">
      <button id="t-shade" class="on" title="Show the shading devices (D)">Shade</button>
      <button id="d-fill" class="on" title="Filled surfaces (E)">Filled</button>
      <button id="d-edge" title="Outlines only (E)">Edges</button>
    </span>
    <span class="grp">
      <button id="shot" title="Save this view as a PNG (P)">PNG</button>
      <button id="full" title="Fullscreen (X)">Full</button>
      <button id="reset" title="Reset the camera (0)">Reset</button>
    </span>
   </div>
   <div class="row">
    <span class="grp stack">
      <span class="lbl">Show</span>
      <span class="btns">
        <button id="t-sun" class="on" title="Sun positions for the period (U)">Suns</button>
        <button id="t-path" class="on" title="Sunpath diagram: solstice and equinox arcs with hour analemmas (A)">Sunpath</button>
        <button id="t-grid" class="on" title="Horizontal x-y grid on the ground (G)">XY grid</button>
        <button id="t-cell" title="Edges of the analysis mesh on the facade plane (C)">Mesh Edges</button>
      </span>
    </span>
   </div>
  </div>
  <div id="legend"></div>
  <div id="tip"></div>
  <div id="probe"></div>
  <div id="hint">Drag to orbit · right-drag to pan · scroll to zoom · hover a cell to read it · click to pin</div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<style>
  @font-face{font-family:"Ronzino";src:url("/app/static/fonts/Ronzino-Regular.otf") format("opentype");
             font-weight:400;font-style:normal;font-display:swap}
  @font-face{font-family:"Ronzino";src:url("/app/static/fonts/Ronzino-Medium.otf") format("opentype");
             font-weight:500;font-style:normal;font-display:swap}
  @font-face{font-family:"Ronzino";src:url("/app/static/fonts/Ronzino-Bold.otf") format("opentype");
             font-weight:700;font-style:normal;font-display:swap}
  html,body{margin:0;background:transparent;font-family:"Ronzino",system-ui,sans-serif}
  #wrap{position:relative;width:100%;height:__H__px;border-radius:6px;overflow:hidden;background:#20262b}
  #wrap.light{background:#f2f4f6}
  #wrap:fullscreen{height:100vh;border-radius:0}
  #bar{position:absolute;left:14px;top:14px;z-index:3;display:flex;flex-direction:column;gap:6px;
       align-items:flex-start}
  #bar .row{display:flex;flex-wrap:wrap;gap:8px}
  #bar .grp{display:flex;gap:4px;background:rgba(32,38,43,.72);padding:3px;border-radius:5px}
  /* the second row carries its own caption above the buttons */
  #bar .grp.stack{flex-direction:column;align-items:flex-start;gap:3px;padding:4px 5px 5px}
  #bar .btns{display:flex;gap:4px}
  #bar .lbl{font-size:9.5px;font-weight:500;letter-spacing:.09em;text-transform:uppercase;
            color:#9aa5ad;padding-left:2px;line-height:1}
  #wrap.light #bar .lbl{color:#5d6a74}
  #wrap.light #bar .grp{background:rgba(255,255,255,.75)}
  #bar button{background:#2f383f;color:#c6ced4;border:1px solid #46525b;border-radius:4px;
               padding:4px 9px;font:500 11px/1.2 inherit;cursor:pointer}
  #bar button:hover{background:#3a454d;color:#e9ecef}
  #wrap.light #bar button{background:#ffffff;color:#49555f;border-color:#c7d0d7}
  #wrap.light #bar button:hover{background:#e8edf1;color:#20262b}
  #bar button.on,#wrap.light #bar button.on{background:#ea7b00;border-color:#ea7b00;color:#1b1f23}
  #bar button:focus-visible{outline:2px solid #f5c443;outline-offset:1px}
  #legend{position:absolute;right:14px;top:14px;color:#e9ecef;font-size:12px;z-index:2}
  #wrap.light #legend{color:#20262b}
  #legend .bar{width:14px;height:180px;border-radius:2px;margin-top:6px}
  #legend .ticks{position:absolute;left:22px;top:24px;height:180px;display:flex;flex-direction:column;justify-content:space-between}
  #legend .stats{margin-top:10px;color:#9aa5ad;font-size:11px;line-height:1.5}
  #wrap.light #legend .stats{color:#5d6a74}
  #hint{position:absolute;left:14px;bottom:10px;color:#9aa5ad;font-size:11px;z-index:2}
  #wrap.light #hint{color:#5d6a74}
  #tip{position:absolute;z-index:4;display:none;pointer-events:none;background:rgba(15,19,22,.92);
       color:#e9ecef;border:1px solid #46525b;border-radius:4px;padding:5px 8px;font-size:11px;white-space:nowrap}
  #wrap.light #tip{background:rgba(255,255,255,.95);color:#20262b;border-color:#c7d0d7}
  #probe{position:absolute;right:14px;bottom:10px;z-index:2;display:none;font-size:11px;
         color:#f5c443;background:rgba(15,19,22,.8);border:1px solid #46525b;border-radius:4px;padding:5px 8px}
  #wrap.light #probe{color:#a15200;background:rgba(255,255,255,.9);border-color:#c7d0d7}
</style>
<script>
const D = __DATA__;
const wrap = document.getElementById('wrap');
const W = () => wrap.clientWidth, H = () => wrap.clientHeight;
const renderer = new THREE.WebGLRenderer({antialias:true, preserveDrawingBuffer:true});
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(W(), H());
wrap.appendChild(renderer.domElement);
const scene = new THREE.Scene();

// local (x along facade, y outward, z up) -> three (x, z, y)
const P = (x,y,z) => new THREE.Vector3(x, z, y);
const S = Math.max(D.W, D.H);

// ------------------------------------------------------------- cameras
const persp = new THREE.PerspectiveCamera(40, W()/H(), 0.05, 500);
const ortho = new THREE.OrthographicCamera(-1, 1, 1, -1, -500, 500);
let cam = persp;
let controls = makeControls(cam);
function makeControls(c){
  const k = new THREE.OrbitControls(c, renderer.domElement);
  k.enableDamping = true;
  k.addEventListener('end', save);
  return k;
}
function fitOrtho(){
  const dist = cam.position.distanceTo(controls.target);
  const hh = Math.max(dist * Math.tan(THREE.MathUtils.degToRad(persp.fov/2)), 0.5);
  const hw = hh * (W()/H());
  ortho.left = -hw; ortho.right = hw; ortho.top = hh; ortho.bottom = -hh;
  ortho.updateProjectionMatrix();
}

scene.add(new THREE.HemisphereLight(0xffffff, 0x445566, 0.85));
const dl = new THREE.DirectionalLight(0xffffff, 0.45); dl.position.set(4, 8, 10); scene.add(dl);

// shading devices keep their own mesh and edge subgroups, so hiding them hides both
const gShade = new THREE.Group(), gShadeMesh = new THREE.Group(), gShadeEdge = new THREE.Group();
gShade.add(gShadeMesh, gShadeEdge);
const gEdge = new THREE.Group(),
      gSun = new THREE.Group(), gPath = new THREE.Group(), gCell = new THREE.Group();
scene.add(gShade, gEdge, gSun, gPath, gCell);
gCell.visible = false;

const edgeMat = new THREE.LineBasicMaterial({color:0x0f1316, transparent:true, opacity:0.5});
const cellLineMat = new THREE.LineBasicMaterial({color:0x2b3238, transparent:true, opacity:0.55});
function quad(O,u,v,color,opacity,parent){
  const g = new THREE.BufferGeometry();
  const c = [O, [O[0]+u[0],O[1]+u[1],O[2]+u[2]],
             [O[0]+u[0]+v[0],O[1]+u[1]+v[1],O[2]+u[2]+v[2]], [O[0]+v[0],O[1]+v[1],O[2]+v[2]]]
            .map(p=>P(p[0],p[1],p[2]));
  g.setFromPoints([c[0],c[1],c[2],c[0],c[2],c[3]]); g.computeVertexNormals();
  const m = new THREE.MeshLambertMaterial({color, side:THREE.DoubleSide, transparent:opacity<1, opacity});
  const mesh = new THREE.Mesh(g,m);
  const shading = parent === gShade;
  (shading ? gShadeMesh : (parent||scene)).add(mesh);
  solids.push(mesh);
  (shading ? gShadeEdge : gEdge).add(new THREE.LineSegments(new THREE.EdgesGeometry(g), edgeMat));
}
const solids = [];                                 // every filled surface, for the Filled/Edges mode

// ground, wall and glazing
const grid = new THREE.GridHelper(S*3, 30, 0x3a454d, 0x2c353b);
grid.position.set(D.W/2, 0, 1.5); scene.add(grid);
quad([0,-0.02,0],[D.W,0,0],[0,0,D.H],0xbfc4c7,1);
if(!D.cells) quad([D.win.x0,0,D.win.z0],[D.win.x1-D.win.x0,0,0],[0,0,D.win.z1-D.win.z0],0x7fb3d5,1);
D.quads.forEach(q => quad(q.O,q.u,q.v, q.kind==='fin'?0xd8d2c4:0xe6e0d2, 1, gShade));

// ------------------------------------------------------------- result cells
function fmt(x){ return Math.abs(x) >= 100 ? x.toFixed(0) : x.toFixed(1); }
let cellMesh = null;
if(D.cells){
  const pos=[], col=[], c=new THREE.Color();
  D.cells.pts.forEach((p,i)=>{
    const x0=p[0]-D.cells.dx/2, x1=p[0]+D.cells.dx/2,
          z0=p[2]-D.cells.dz/2, z1=p[2]+D.cells.dz/2, y=0.004;
    [[x0,z0],[x1,z0],[x1,z1],[x0,z0],[x1,z1],[x0,z1]].forEach(v=>{const q=P(v[0],y,v[1]); pos.push(q.x,q.y,q.z);});
    c.set(D.cells.colors[i]); for(let k=0;k<6;k++) col.push(c.r,c.g,c.b);
  });
  const g=new THREE.BufferGeometry();
  g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
  g.setAttribute('color',new THREE.Float32BufferAttribute(col,3));
  cellMesh = new THREE.Mesh(g,new THREE.MeshBasicMaterial({vertexColors:true,side:THREE.DoubleSide}));
  scene.add(cellMesh);
  // outline of every analysis cell, on the facade plane
  const lp=[];
  D.cells.pts.forEach(p=>{
    const x0=p[0]-D.cells.dx/2, x1=p[0]+D.cells.dx/2,
          z0=p[2]-D.cells.dz/2, z1=p[2]+D.cells.dz/2, y=0.006;
    [[x0,z0,x1,z0],[x1,z0,x1,z1],[x1,z1,x0,z1],[x0,z1,x0,z0]].forEach(s=>{
      const a=P(s[0],y,s[1]), b=P(s[2],y,s[3]); lp.push(a.x,a.y,a.z,b.x,b.y,b.z);
    });
  });
  const lg2=new THREE.BufferGeometry();
  lg2.setAttribute('position', new THREE.Float32BufferAttribute(lp,3));
  gCell.add(new THREE.LineSegments(lg2, cellLineMat));

  const v=D.cells.vals; let mn=Infinity, mx=-Infinity, sum=0;
  for(let i=0;i<v.length;i++){ if(v[i]<mn)mn=v[i]; if(v[i]>mx)mx=v[i]; sum+=v[i]; }
  document.getElementById('legend').innerHTML =
    '<div>'+D.legend.title+'</div>'+
    '<div class="bar" style="background:linear-gradient(to bottom,'+D.legend.colors.slice().reverse().join(',')+')"></div>'+
    '<div class="ticks"><span>'+D.legend.max+'</span><span>'+D.legend.mid+'</span><span>'+D.legend.min+'</span></div>'+
    '<div class="stats">min '+fmt(mn)+'<br>mean '+fmt(sum/v.length)+'<br>max '+fmt(mx)+'</div>';
}

// ------------------------------------------------------------- sky dome
const R = S*1.7, CX = D.W/2, CZ = 0.0;           // dome centred on the ground
const dome = (s) => P(CX + R*s[0], R*s[1], CZ + R*s[2]);

if(D.suns && D.suns.length){
  // round dots of a fixed pixel size: the dome is wide enough that world-space markers
  // balloon on the near side and vanish on the far one, so size attenuation is off
  const disc = document.createElement('canvas'); disc.width = disc.height = 64;
  const dc = disc.getContext('2d');
  dc.beginPath(); dc.arc(32, 32, 30, 0, Math.PI*2); dc.fillStyle = '#fff'; dc.fill();
  const pos=[]; D.suns.forEach(s=>{const q=dome(s); pos.push(q.x,q.y,q.z);});
  const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
  gSun.add(new THREE.Points(g, new THREE.PointsMaterial({
    color:0xf5c443, size:10, sizeAttenuation:false, map:new THREE.CanvasTexture(disc),
    transparent:true, opacity:0.9, alphaTest:0.4, depthWrite:false})));
}

if(D.paths && D.paths.length){
  const mats = {
    day:  new THREE.LineBasicMaterial({color:0xea7b00, transparent:true, opacity:0.95}),
    hour: new THREE.LineBasicMaterial({color:0x8fa3b3, transparent:true, opacity:0.55}),
  };
  D.paths.forEach(p=>{
    const g=new THREE.BufferGeometry().setFromPoints(p.pts.map(dome));
    gPath.add(new THREE.Line(g, mats[p.kind] || mats.hour));
  });
  // horizon circle on the ground plane
  const ring=[]; for(let i=0;i<=120;i++){ const a=i/120*Math.PI*2; ring.push(dome([Math.cos(a),Math.sin(a),0])); }
  gPath.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(ring),
            new THREE.LineBasicMaterial({color:0x8fa3b3, transparent:true, opacity:0.4})));
}

// ------------------------------------------------------------- hover / pin probe
const tip=document.getElementById('tip'), probeBox=document.getElementById('probe');
const ray=new THREE.Raycaster(), ndc=new THREE.Vector2();
let marker=null, pinned=null;
if(cellMesh){
  marker=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.PlaneGeometry(D.cells.dx, D.cells.dz)),
                                new THREE.LineBasicMaterial({color:0xffffff}));
  marker.rotation.x=-Math.PI/2; marker.visible=false; scene.add(marker);
}
function pick(ev){
  if(!cellMesh) return -1;
  const r=renderer.domElement.getBoundingClientRect();
  ndc.x=((ev.clientX-r.left)/r.width)*2-1; ndc.y=-((ev.clientY-r.top)/r.height)*2+1;
  ray.setFromCamera(ndc, cam);
  const hit=ray.intersectObject(cellMesh,false)[0];
  return hit ? Math.floor(hit.faceIndex/2) : -1;
}
function cellText(i){
  const p=D.cells.pts[i];
  return fmt(D.cells.vals[i])+' '+D.legend.unit+' · x '+p[0].toFixed(2)+' m, z '+p[2].toFixed(2)+' m';
}
renderer.domElement.addEventListener('pointermove', ev=>{
  const i=pick(ev);
  if(i<0){ tip.style.display='none'; if(marker && pinned===null) marker.visible=false; return; }
  tip.textContent=cellText(i); tip.style.display='block';
  const r=wrap.getBoundingClientRect();
  tip.style.left=Math.min(ev.clientX-r.left+12, r.width-tip.offsetWidth-6)+'px';
  tip.style.top=(ev.clientY-r.top+14)+'px';
  if(marker && pinned===null){ const p=D.cells.pts[i]; marker.position.set(p[0],0.006,p[2]); marker.visible=true; }
});
renderer.domElement.addEventListener('pointerleave', ()=>{
  tip.style.display='none'; if(marker && pinned===null) marker.visible=false;
});
renderer.domElement.addEventListener('click', ev=>{
  if(!cellMesh) return;
  const i=pick(ev);
  if(i<0 || i===pinned){ pinned=null; probeBox.style.display='none'; if(marker) marker.visible=false; return; }
  pinned=i; const p=D.cells.pts[i];
  probeBox.textContent='Pinned: '+cellText(i); probeBox.style.display='block';
  if(marker){ marker.position.set(p[0],0.006,p[2]); marker.visible=true; }
});

// ------------------------------------------------------------- viewpoints
// camera positions and targets, already in three coordinates (x along, y up, z outward)
const VIEWS={
  front:[[D.W/2,          D.H/2,   S*1.7], [D.W/2, D.H/2, 0.0]],
  side: [[D.W/2 + S*1.6,  D.H/2,   S*0.4], [D.W/2, D.H/2, 0.3]],
  top:  [[D.W/2,          S*1.8,   0.9  ], [D.W/2, 0.0,   0.9]],
};
// oblique viewpoints by true compass bearing: the camera stands on that side of the
// building, so which of them face the wall depends on the facade's own orientation
const BEARINGS={se:135, sw:225, ne:45, nw:315};
let DEFV=null, bestFacing=-Infinity;
for(const k in BEARINGS){
  // along = sin(azimuth - bearing), outward = cos(azimuth - bearing)
  const d=THREE.MathUtils.degToRad(D.az-BEARINGS[k]), L=S*2.2;
  VIEWS[k]=[[D.W/2 + L*Math.sin(d), D.H*1.6, L*Math.cos(d)], [D.W/2, D.H/2, 0.3]];
  if(Math.cos(d)>bestFacing){ bestFacing=Math.cos(d); DEFV=k; }   // most front-on corner
}
// looking straight down leaves the screen orientation undefined, so the top view
// fixes its own up vector: the wall sits at the top, the shading hangs below it
const UPS={top:[0,0,-1]};
function setView(k){
  const v=VIEWS[k]||VIEWS[DEFV], u=UPS[k]||[0,1,0];
  cam.up.set(u[0], u[1], u[2]);
  cam.position.set(v[0][0], v[0][1], v[0][2]);
  controls.target.set(v[1][0], v[1][1], v[1][2]);
  cam.zoom = 1; fitOrtho(); cam.updateProjectionMatrix(); controls.update(); save();
  document.querySelectorAll('#bar [data-view]').forEach(b=>b.classList.toggle('on', b.dataset.view===k));
}
const KEY='facade-view';
// every toggle in the bar, so the whole look of the view survives a rerun: changing a
// facade or shading parameter rebuilds this iframe from scratch, and without this the
// buttons would snap back to their defaults on every slider move
const TOGGLES=['t-shade','t-sun','t-path','t-grid','t-cell'];
const isOn=(id)=>document.getElementById(id).classList.contains('on');
let ready=false;                                  // no saving while the scene is still being set up
function save(){
  if(!ready) return;
  const v={}; TOGGLES.forEach(id=>{ v[id]=isOn(id); });
  try{ localStorage.setItem(KEY, JSON.stringify({
    p:cam.position.toArray(), t:controls.target.toArray(), z:cam.zoom, u:cam.up.toArray(),
    o:cam===ortho, l:wrap.classList.contains('light'),
    w:isOn('d-edge'), v:v})); }catch(e){}
}
document.querySelectorAll('#bar [data-view]').forEach(b=>b.onclick=()=>setView(b.dataset.view));
document.getElementById('reset').onclick=()=>{
  if(cam===ortho) setProjection(false);
  if(wrap.classList.contains('light')) setBackground(false);
  setDrawMode(false);
  TOGGLES.forEach(id=>{ if(isOn(id)!==TOG_DEF[id]) document.getElementById(id).click(); });
  setView(DEFV); try{localStorage.removeItem(KEY);}catch(e){}
  if(isOn('t-path')) frameDome();
};

// ------------------------------------------------------------- toggles
function toggle(id, fn, on){
  const b=document.getElementById(id);
  if(on) b.classList.add('on');
  b.onclick=()=>{ const v=!b.classList.contains('on'); b.classList.toggle('on',v); fn(v); save(); };
  return b;
}
const TOG_DEF={'t-shade':true, 't-sun':true, 't-path':true, 't-grid':true, 't-cell':false};
toggle('t-shade', v=>{ gShade.visible=v; }, TOG_DEF['t-shade']);
toggle('t-sun',   v=>{ gSun.visible=v;   }, TOG_DEF['t-sun']);
function frameDome(){                       // pull the camera back so the whole dome fits
  const t=controls.target, dir=cam.position.clone().sub(t);
  const want=R*2.4;
  if(dir.length() < want){ cam.position.copy(t).add(dir.setLength(want)); }
  cam.zoom=1; fitOrtho(); cam.updateProjectionMatrix(); controls.update(); save();
}
toggle('t-path',  v=>{ gPath.visible=v; if(v) frameDome(); }, TOG_DEF['t-path']);
toggle('t-grid',  v=>{ grid.visible=v;   }, TOG_DEF['t-grid']);
toggle('t-cell',  v=>{ gCell.visible=v;  }, TOG_DEF['t-cell']);

// two-state switches: the active half of the pair is highlighted
function pair(idA, idB, fn){
  const a=document.getElementById(idA), b=document.getElementById(idB);
  const set=(second)=>{ a.classList.toggle('on',!second); b.classList.toggle('on',second); fn(second); };
  a.onclick=()=>set(false); b.onclick=()=>set(true);
  return set;
}

// filled surfaces, or outlines only (a wireframe of the same geometry)
function setDraw(edgesOnly){ solids.forEach(m=>{ m.visible = !edgesOnly; }); save(); }
const setDrawMode = pair('d-fill', 'd-edge', setDraw);

function setLight(v){
  wrap.classList.toggle('light', v);
  renderer.setClearColor(v ? 0xf2f4f6 : 0x20262b, 1);
  grid.material.color.set(v ? 0x9aa5ad : 0x2c353b);
  edgeMat.color.set(v ? 0x5d6a74 : 0x0f1316);
  cellLineMat.color.set(v ? 0x7b878f : 0x2b3238);
  if(marker) marker.material.color.set(v ? 0x20262b : 0xffffff);
  save();
}
const setBackground = pair('b-dark', 'b-light', setLight);
setLight(false);

function setOrtho(v){
  const prev=cam; cam = v ? ortho : persp;
  cam.position.copy(prev.position); cam.up.copy(prev.up); cam.zoom = 1;
  const t=controls.target.clone();
  controls.dispose(); controls = makeControls(cam);
  controls.target.copy(t);
  fitOrtho(); cam.updateProjectionMatrix(); controls.update(); save();
}
const setProjection = pair('p-persp', 'p-ortho', setOrtho);

// restore the previous camera, projection and background
try{
  const s=JSON.parse(localStorage.getItem(KEY));
  const ok = s && s.p && s.t && new THREE.Vector3().fromArray(s.p).distanceTo(new THREE.Vector3().fromArray(s.t)) > 0.1;
  if(ok){
    // the toggles go back first: switching the sunpath on pulls the camera out to frame
    // the dome, and the saved camera below has to be the one that wins
    if(s.v) TOGGLES.forEach(id=>{ if(id in s.v && s.v[id] !== isOn(id)) document.getElementById(id).click(); });
    if(s.l) setBackground(true);
    if(s.o) setProjection(true);
    if(s.w) setDrawMode(true);
    if(s.u) cam.up.fromArray(s.u);
    cam.position.fromArray(s.p); controls.target.fromArray(s.t);
    if(s.z) cam.zoom=s.z;
    fitOrtho(); cam.updateProjectionMatrix(); controls.update();
    document.querySelectorAll('#bar [data-view]').forEach(b=>b.classList.remove('on'));
  } else {
    setView(DEFV);
    if(isOn('t-path')) frameDome();
  }
}catch(e){
  setView(DEFV);
  if(isOn('t-path')) frameDome();
}
ready=true; save();

// ------------------------------------------------------------- png + fullscreen
document.getElementById('shot').onclick=()=>{
  renderer.render(scene, cam);
  const a=document.createElement('a');
  a.href=renderer.domElement.toDataURL('image/png');
  a.download='facade_view.png'; a.click();
};
document.getElementById('full').onclick=()=>{
  if(document.fullscreenElement) document.exitFullscreen();
  else if(wrap.requestFullscreen) wrap.requestFullscreen();
};
document.addEventListener('fullscreenchange', resize);

// ------------------------------------------------------------- keyboard
const VKEYS={'1':'se', '2':'sw', '3':'ne', '4':'nw', f:'front', s:'side', t:'top'};
const BKEYS={d:'t-shade', u:'t-sun', a:'t-path', g:'t-grid', c:'t-cell',
             p:'shot', x:'full', '0':'reset'};
// each pair key flips the pair rather than clicking one half of it
const PKEYS={o:()=>setProjection(cam!==ortho),
             b:()=>setBackground(!wrap.classList.contains('light')),
             e:()=>setDrawMode(!document.getElementById('d-edge').classList.contains('on'))};
window.addEventListener('keydown', e=>{
  if(e.metaKey||e.ctrlKey||e.altKey) return;
  const k=e.key.toLowerCase();
  if(VKEYS[k]) setView(VKEYS[k]);
  else if(PKEYS[k]) PKEYS[k]();
  else if(BKEYS[k]) document.getElementById(BKEYS[k]).click();
  else return;
  e.preventDefault();
});

function resize(){
  renderer.setSize(W(),H());
  persp.aspect=W()/H(); persp.updateProjectionMatrix();
  fitOrtho();
}
window.addEventListener('resize', resize);
if(window.ResizeObserver) new ResizeObserver(resize).observe(wrap);
(function loop(){ requestAnimationFrame(loop); controls.update(); renderer.render(scene,cam); })();
</script>
"""


def render_viewer(scene, values=None, vmin=None, vmax=None, title="", suns=None,
                  paths=None, azimuth=180, height=600):
    data = {
        "W": scene["W"], "H": scene["H"], "win": scene["win"], "az": float(azimuth),
        "quads": [{k: (np.asarray(q[k]).tolist() if k != "kind" else q[k]) for k in q}
                  for q in scene["quads"]],
        "suns": suns.tolist() if suns is not None else [],
        "paths": paths or [],
    }
    if values is not None:
        data["cells"] = {"pts": scene["points"].round(4).tolist(),
                         "dx": scene["dx"], "dz": scene["dz"],
                         "vals": np.asarray(values).round(2).tolist(),
                         "colors": colorize(values, vmin, vmax)}
        data["legend"] = {"title": title, "unit": "%" if "%" in title else title,
                          "min": f"{vmin:.0f}", "max": f"{vmax:.0f}",
                          "mid": f"{(vmin + vmax) / 2:.0f}",
                          "colors": colorize(np.linspace(vmin, vmax, 10), vmin, vmax)}
    payload = json.dumps(data).replace("</", "<\\/")  # keep JSON safe inside <script>
    html = HTML.replace("__DATA__", payload).replace("__H__", str(height))
    if hasattr(st, "iframe"):  # Streamlit >= 1.5x
        st.iframe(html, height=height + 4)
    else:
        components.html(html, height=height + 4)
