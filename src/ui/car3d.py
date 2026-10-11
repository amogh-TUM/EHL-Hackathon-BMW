"""3D customer-voice map: requirements pinned to the part of a generic sedan where customers feel them.

The sedan is drawn procedurally with three.js (vendored, MIT) - no third-party car model, no brand assets.
Placement is deterministic and traceable: a requirement goes to the zone most of its VFC topics map to.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

# zone -> (label, anchor point on the car: x = length (front +), y = height, z = width (camera side +))
ZONES = {
    "cockpit": ("Cockpit & displays", (0.55, 1.12, 0.0)),
    "front_seats": ("Front seats & comfort", (0.05, 0.98, 0.40)),
    "rear_cabin": ("Rear cabin & space", (-0.80, 1.02, 0.0)),
    "interior": ("Interior quality & storage", (0.30, 0.98, -0.42)),
    "roof_light": ("Climate, light & roof", (-0.25, 1.45, 0.0)),
    "trunk": ("Trunk & loading", (-2.05, 1.02, 0.0)),
    "charging": ("Charging & range", (-1.60, 0.88, 0.92)),
    "powertrain": ("Powertrain & sound", (1.85, 0.80, 0.0)),
    "chassis": ("Ride, handling & brakes", (1.45, 0.36, 0.98)),
    "assist": ("Driver assistance & sensors", (2.42, 0.58, 0.0)),
    "access": ("Doors, keys & access", (0.35, 0.80, 0.93)),
    "exterior": ("Exterior design & lights", (-0.40, 0.66, 0.95)),
    "digital": ("Digital services (no physical location)", None),
}

# Ordered keyword rules on lower-cased VFC topic names (first match wins).
RULES = [
    ("rear seat", "rear_cabin"), ("space / spatial", "rear_cabin"), ("rear passenger", "rear_cabin"),
    ("legroom", "rear_cabin"), ("chauffeur", "rear_cabin"), ("long-wheelbase", "rear_cabin"),
    ("material", "interior"), ("craftsmanship", "interior"), ("cabin quality", "interior"),
    ("ev range", "charging"), ("range", "charging"),
    ("driving pleasure", "powertrain"), ("acceleration", "powertrain"),
    ("profile", "cockpit"), ("connected", "digital"), ("app ", "digital"),
    ("wireless charging", "interior"), ("usb", "interior"), ("cupholder", "interior"), ("storage", "interior"),
    ("glove", "interior"), ("center console", "interior"), ("upholstery", "interior"), ("interior design", "interior"),
    ("body equipment", "interior"), ("interior acoustics", "interior"),
    ("charg", "charging"), ("electric range", "charging"), ("high voltage battery", "charging"), ("recuperation", "charging"),
    ("trunk", "trunk"), ("luggage", "trunk"),
    ("seat", "front_seats"), ("headrest", "front_seats"), ("lumbar", "front_seats"), ("interior comfort", "front_seats"),
    ("ambient", "roof_light"), ("climatization", "roof_light"), ("air conditioning", "roof_light"), ("blower", "roof_light"),
    ("panorama", "roof_light"), ("sun protection", "roof_light"), ("interior, lighting", "roof_light"), ("climate", "roof_light"),
    ("parking brake", "chassis"),
    ("assist", "assist"), ("cruise", "assist"), ("lane", "assist"), ("park", "assist"), ("camera", "assist"),
    ("surround", "assist"), ("all-round", "assist"), ("speed limit", "assist"), ("safety", "assist"),
    ("drive recorder", "assist"), ("automated driving", "assist"),
    ("software upgrade", "digital"), ("my bmw app", "digital"), ("esim", "digital"), ("owner's manual", "digital"),
    ("general enquiry", "digital"), ("remote", "digital"), ("connecteddrive services", "digital"), ("wifi", "digital"),
    ("accessories", "digital"),
    ("vehicle key", "access"), ("digital key", "access"), ("door", "access"), ("lock", "access"),
    ("comfort access", "access"), ("access and exit", "access"), ("window", "access"),
    ("touch screen", "cockpit"), ("operating", "cockpit"), ("infotainment", "cockpit"), ("navigation", "cockpit"),
    ("carplay", "cockpit"), ("android", "cockpit"), ("instrument", "cockpit"), ("head-up", "cockpit"), ("audio", "cockpit"),
    ("radio", "cockpit"), ("voice", "cockpit"), ("personal assistant", "cockpit"), ("steering wheel", "cockpit"),
    ("gesture", "cockpit"), ("controller", "cockpit"), ("driver profile", "cockpit"), ("bluetooth", "cockpit"),
    ("apps (in-car)", "cockpit"), ("selector lever", "cockpit"), ("screen", "cockpit"), ("display", "cockpit"),
    ("exterior", "exterior"), ("mirror", "exterior"), ("lighting", "exterior"), ("styling", "exterior"),
    ("drivetrain", "powertrain"), ("transmission", "powertrain"), ("engine", "powertrain"), ("my modes", "powertrain"),
    ("start-stop", "powertrain"), ("vehicle battery", "powertrain"),
    ("handling", "chassis"), ("riding", "chassis"), ("chassis", "chassis"), ("cushioning", "chassis"), ("brak", "chassis"),
    ("wheels", "chassis"), ("tire", "chassis"), ("steering", "chassis"), ("automatic-hold", "chassis"), ("clearance", "chassis"),
]


def zone_of_text(text: str) -> str | None:
    t = text.lower()
    for kw, zone in RULES:
        if kw in t:
            return zone
    return None


def place(req: dict) -> tuple[str, str]:
    """(zone, why). Score per zone: keyword hits in the requirement's own title (x2) and statement (x1),
    plus its VFC topics (x0.5) as tie-breaker; equal scores go to the earlier, more specific rule."""
    title, stmt = req["title"].lower(), req["statement"].lower()
    topics = req.get("computed", {}).get("topics", [])
    score, first, why = Counter(), {}, {}
    for i, (kw, zone) in enumerate(RULES):
        hit = 2 * (kw in title) + (kw in stmt)
        if hit:
            score[zone] += hit
            first.setdefault(zone, i)
            why.setdefault(zone, {"brak": "braking", "charg": "charging"}.get(kw, kw.strip()))
    for t in topics:
        z = zone_of_text(t)
        if z:
            score[z] += 0.5
            first.setdefault(z, len(RULES))
            why.setdefault(z, f"topic '{t}'")
    if not score:
        return "digital", "no physical location found in wording or topics"
    zone = max(score, key=lambda z: (score[z], -first[z]))
    return zone, f"by '{why[zone]}' in the requirement (topics as tie-breaker)"


STATUS_COLOR = {"proposed": "#30a9dd", "approved": "#2fbf84", "modified": "#2fbf84", "postponed": "#e2a83c", "rejected": "#e0566a"}


def hotspots(reqs: list[dict], scored) -> list[dict]:
    out, per_zone = [], Counter()
    for r in sorted(reqs, key=lambda x: scored.loc[x["id"], "rank"]):
        zone, how = place(r)
        label, anchor = ZONES[zone]
        k = per_zone[zone]
        per_zone[zone] += 1
        pos = None
        if anchor:
            x, y, z = anchor
            pos = [x + ((k % 3) - 1) * 0.24, y + (k // 3) * 0.22, z]
        ev = r.get("evaluation") or {}
        out.append({
            "id": r["id"], "title": r["title"], "statement": r["statement"], "status": r["status"],
            "color": STATUS_COLOR.get(r["status"], "#30a9dd"), "score": float(scored.loc[r["id"], "priority_score"]),
            "rank": int(scored.loc[r["id"], "rank"]), "markets": r["target_markets"], "zone": zone, "zone_label": label,
            "placed": how, "pos": pos, "verdict": (ev.get("verdict") or "not evaluated").replace("_", " "),
            "confidence": r["confidence"],
        })
    return out


_THREE = None


def _three_js() -> str:
    global _THREE
    if _THREE is None:
        _THREE = (Path(__file__).resolve().parents[2] / "assets" / "vendor" / "three.min.js").read_text(encoding="utf-8")
    return _THREE


def html(spots: list[dict], height: int = 620) -> str:
    data = json.dumps([s for s in spots if s["pos"]], ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html><html><head><meta charset="utf-8">
<style>
html,body{{margin:0;height:100%;background:#0b1118;overflow:hidden;font-family:Inter,Segoe UI,Arial,sans-serif}}
#wrap{{position:relative;width:100%;height:{height}px}}
canvas{{display:block}}
.lbl{{position:absolute;transform:translate(-50%,-140%);font:700 11px Inter,Arial,sans-serif;color:#0b1118;padding:2px 6px;border-radius:9px;
     pointer-events:none;white-space:nowrap;box-shadow:0 0 12px rgba(0,0,0,.5)}}
#tip{{position:absolute;display:none;max-width:320px;background:rgba(10,16,24,.95);border:1px solid #30a9dd66;color:#e8eef3;
     padding:10px 12px;font-size:12px;line-height:1.45;pointer-events:none;box-shadow:0 10px 30px rgba(0,0,0,.5)}}
#tip b{{font-size:13px}} #tip .k{{color:#8fa0ae}}
#hint{{position:absolute;left:14px;bottom:10px;color:#6f8291;font-size:11px;letter-spacing:.5px}}
#legend{{position:absolute;right:14px;top:12px;color:#c9d4dc;font-size:11px;display:flex;gap:12px}}
#legend span:before{{content:'';display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;background:var(--c);vertical-align:-1px}}
</style></head><body><div id="wrap"><div id="tip"></div>
<div id="legend"><span style="--c:#30a9dd">to decide</span><span style="--c:#2fbf84">approved</span><span style="--c:#e2a83c">postponed</span><span style="--c:#e0566a">rejected</span></div>
<div id="hint">Drag to rotate · scroll to zoom · hover a hotspot · size = priority score</div></div>
<script>{_three_js()}</script>
<script>
const SPOTS = {data};
const wrap = document.getElementById('wrap'), tip = document.getElementById('tip');
const W = () => wrap.clientWidth, H = {height};
const renderer = new THREE.WebGLRenderer({{antialias:true}});
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); renderer.setSize(W(), H);
renderer.shadowMap.enabled = true; wrap.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.fog = new THREE.Fog(0x0b1118, 9, 18);
const camera = new THREE.PerspectiveCamera(38, W()/H, 0.1, 100);
scene.add(new THREE.HemisphereLight(0xcfe8ff, 0x0b1118, 0.75));
const sun = new THREE.DirectionalLight(0xffffff, 0.9); sun.position.set(4, 7, 5); sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024); scene.add(sun);
const rim = new THREE.DirectionalLight(0x30a9dd, 0.6); rim.position.set(-5, 3, -4); scene.add(rim);

// ground
const ground = new THREE.Mesh(new THREE.CircleGeometry(4.2, 64), new THREE.MeshStandardMaterial({{color:0x111b25, roughness:1}}));
ground.rotation.x = -Math.PI/2; ground.receiveShadow = true; scene.add(ground);
const ring = new THREE.Mesh(new THREE.RingGeometry(3.6, 3.63, 96), new THREE.MeshBasicMaterial({{color:0x30a9dd, transparent:true, opacity:.35}}));
ring.rotation.x = -Math.PI/2; ring.position.y = .005; scene.add(ring);

// procedural sedan (side profile extruded across the width)
const car = new THREE.Group(); scene.add(car);
function extrude(shape, depth, mat, bevel) {{
  const g = new THREE.ExtrudeGeometry(shape, {{depth, bevelEnabled:true, bevelThickness:bevel, bevelSize:bevel, bevelSegments:4, curveSegments:24}});
  g.translate(0, 0, -depth/2); const m = new THREE.Mesh(g, mat); m.castShadow = true; m.receiveShadow = true; return m;
}}
const body = new THREE.Shape();
body.moveTo(-2.38, 0.30); body.lineTo(-1.93, 0.30);
body.absarc(-1.45, 0.34, 0.48, Math.PI, 0, true);
body.lineTo(0.97, 0.30);
body.absarc(1.45, 0.34, 0.48, Math.PI, 0, true);
body.lineTo(2.30, 0.30); body.quadraticCurveTo(2.50, 0.36, 2.47, 0.58);
body.quadraticCurveTo(2.40, 0.74, 2.05, 0.80); body.lineTo(0.95, 0.94);
body.lineTo(-1.35, 0.98); body.lineTo(-2.22, 0.94);
body.quadraticCurveTo(-2.46, 0.86, -2.44, 0.58); body.quadraticCurveTo(-2.44, 0.34, -2.38, 0.30);
const paint = new THREE.MeshStandardMaterial({{color:0x7d8b98, metalness:0.6, roughness:0.35, transparent:true, opacity:0.92}});
car.add(extrude(body, 1.62, paint, 0.08));
const green = new THREE.Shape();
green.moveTo(0.95, 0.93); green.quadraticCurveTo(0.45, 1.30, 0.12, 1.42);
green.lineTo(-0.80, 1.44); green.quadraticCurveTo(-1.30, 1.30, -1.52, 0.97); green.lineTo(0.95, 0.93);
const glass = new THREE.MeshStandardMaterial({{color:0x0d1b28, metalness:0.9, roughness:0.08, transparent:true, opacity:0.88}});
car.add(extrude(green, 1.36, glass, 0.06));
// wheels
const tyreM = new THREE.MeshStandardMaterial({{color:0x111111, roughness:0.85}});
const rimM = new THREE.MeshStandardMaterial({{color:0xb8c3cc, metalness:0.9, roughness:0.25}});
[[1.45,.88],[1.45,-.88],[-1.45,.88],[-1.45,-.88]].forEach(([x,z]) => {{
  const t = new THREE.Mesh(new THREE.CylinderGeometry(.37,.37,.26,40), tyreM); t.rotation.x = Math.PI/2; t.position.set(x,.37,z); t.castShadow = true; car.add(t);
  const r = new THREE.Mesh(new THREE.CylinderGeometry(.24,.24,.27,30), rimM); r.rotation.x = Math.PI/2; r.position.set(x,.37,z); car.add(r);
}});
// lights
const head = new THREE.MeshStandardMaterial({{color:0xe8f6ff, emissive:0x9fdcff, emissiveIntensity:1.2}});
const tail = new THREE.MeshStandardMaterial({{color:0x550000, emissive:0xff2a2a, emissiveIntensity:1.0}});
[.55,-.55].forEach(z => {{
  const h = new THREE.Mesh(new THREE.BoxGeometry(.06,.07,.38), head); h.position.set(2.47,.66,z); car.add(h);
  const t = new THREE.Mesh(new THREE.BoxGeometry(.05,.08,.42), tail); t.position.set(-2.47,.80,z); car.add(t);
}});

// hotspots
const maxScore = Math.max(1, ...SPOTS.map(s => s.score));
const pick = [], labels = [];
SPOTS.forEach(s => {{
  const r = 0.055 + 0.075 * (s.score / maxScore);
  const col = new THREE.Color(s.color);
  const m = new THREE.Mesh(new THREE.SphereGeometry(r, 24, 24), new THREE.MeshBasicMaterial({{color:col, depthTest:false}}));
  m.renderOrder = 10;
  m.position.set(...s.pos); m.userData = s; scene.add(m); pick.push(m);
  const halo = new THREE.Mesh(new THREE.SphereGeometry(r*1.5, 24, 24), new THREE.MeshBasicMaterial({{color:col, transparent:true, opacity:.16, depthWrite:false, depthTest:false}}));
  halo.renderOrder = 9;
  halo.position.copy(m.position); scene.add(halo); m.userData.halo = halo;
  const l = document.createElement('div'); l.className = 'lbl'; l.style.background = s.color; l.textContent = '#' + s.rank;
  wrap.appendChild(l); labels.push([l, m]);
}});

// orbit controls (minimal, no extra library)
let theta = 0.5, phi = 1.27, dist = 7.0, drag = false, px = 0, py = 0, auto = true;
let hover = false;
renderer.domElement.addEventListener('mouseenter', () => hover = true);
renderer.domElement.addEventListener('mouseleave', () => {{ hover = false; tip.style.display = 'none'; }});
const target = new THREE.Vector3(0, 0.75, 0);
function place() {{
  const d = dist * Math.max(1, 1.55 / camera.aspect);  // pull back on narrow screens so the whole car fits
  camera.position.set(target.x + d*Math.sin(phi)*Math.sin(theta), target.y + d*Math.cos(phi), target.z + d*Math.sin(phi)*Math.cos(theta));
  camera.lookAt(target);
}}
renderer.domElement.addEventListener('pointerdown', e => {{ drag = true; auto = false; px = e.clientX; py = e.clientY; }});
window.addEventListener('pointerup', () => drag = false);
window.addEventListener('pointermove', e => {{
  if (drag) {{ theta -= (e.clientX - px) * 0.006; phi = Math.min(1.5, Math.max(0.35, phi - (e.clientY - py) * 0.005)); px = e.clientX; py = e.clientY; }}
}});
renderer.domElement.addEventListener('wheel', e => {{ e.preventDefault(); auto = false; dist = Math.min(12, Math.max(4.2, dist + e.deltaY * 0.004)); }}, {{passive:false}});

// hover tooltip
const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
renderer.domElement.addEventListener('mousemove', e => {{
  const b = renderer.domElement.getBoundingClientRect();
  mouse.x = ((e.clientX - b.left) / b.width) * 2 - 1; mouse.y = -((e.clientY - b.top) / b.height) * 2 + 1;
  ray.setFromCamera(mouse, camera);
  const hit = ray.intersectObjects(pick)[0];
  if (hit) {{
    const s = hit.object.userData;
    tip.innerHTML = `<b>#${{s.rank}} · ${{s.title}}</b><br><span class="k">${{s.zone_label}} · ${{s.markets.join(' · ')}}</span><br>` +
      `${{s.statement}}<br><span class="k">Score</span> ${{s.score.toFixed(0)}} · <span class="k">status</span> ${{s.status}} · ` +
      `<span class="k">AI self-review</span> ${{s.verdict}} · <span class="k">confidence</span> ${{s.confidence}}<br>` +
      `<span class="k">Placed ${{s.placed}}</span>`;
    tip.style.display = 'block';
    tip.style.left = Math.min(e.clientX - b.left + 14, b.width - 330) + 'px'; tip.style.top = (e.clientY - b.top + 14) + 'px';
    renderer.domElement.style.cursor = 'pointer';
  }} else {{ tip.style.display = 'none'; renderer.domElement.style.cursor = drag ? 'grabbing' : 'grab'; }}
}});

const v = new THREE.Vector3(); let t0 = 0;
function loop(t) {{
  if (auto && !hover) theta += 0.0022;
  place();
  const pulse = 1 + 0.18 * Math.sin(t / 380);
  pick.forEach(m => m.userData.halo.scale.setScalar(pulse));
  renderer.render(scene, camera);
  labels.forEach(([l, m]) => {{
    v.copy(m.position).project(camera);
    l.style.left = ((v.x + 1) / 2 * W()) + 'px'; l.style.top = ((1 - v.y) / 2 * H) + 'px';
    l.style.display = v.z < 1 ? 'block' : 'none';
  }});
  requestAnimationFrame(loop);
}}
window.addEventListener('resize', () => {{ renderer.setSize(W(), H); camera.aspect = W()/H; camera.updateProjectionMatrix(); }});
requestAnimationFrame(loop);
</script></body></html>"""
