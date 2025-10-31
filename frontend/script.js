// frontend/script.js
//
// StarMind - Frontend script
// - Renders galaxy (canvas)
// - Attaches galaxy to backend AI engine
// - Lets player select planets and perform actions (attack/negotiate/expand)
// - Animates fleet movement when backend returns a path
//
// Requirements:
// - index.html must have: <canvas id="galaxyCanvas"></canvas>, <div id="uiPanel"></div>, <div id="log"></div>
// - Backend endpoints: POST /api/attach_galaxy and POST /api/player_move
//
// Author: ChatGPT (delivered code)

const API_BASE = "http://127.0.0.1:5000/api"; // change if needed
const CANVAS_ID = "galaxyCanvas";
const UI_PANEL_ID = "uiPanel";
const LOG_ID = "log";

let canvas, ctx;
let width = 960, height = 540;
let galaxies = {}; // systems: id -> {pos:[x,y], owner, resources}
let adjacency = {}; // id -> [ids]
let planets = []; // list of system ids for easy iteration
let selectedPlanet = null;
let playerId = 0; // assume player id 0 for now
let animating = false;
let animationQueue = [];

// Visual config
const PLANET_RADIUS = 14;
const COLORS = ["#7AD3FF", "#FFD27A", "#C8FF7A", "#FF9AA2", "#D1B3FF"];

function init() {
  canvas = document.getElementById(CANVAS_ID);
  if (!canvas) {
    console.error("Canvas not found (id:", CANVAS_ID, ")");
    return;
  }
  canvas.width = width;
  canvas.height = height;
  ctx = canvas.getContext("2d");

  canvas.addEventListener("click", onCanvasClick);
  window.requestAnimationFrame(draw);

  buildUI();
  createSampleGalaxy();
  attachGalaxyToBackend();
}

// -----------------------------
// UI
// -----------------------------
function buildUI() {
  const panel = document.getElementById(UI_PANEL_ID);
  panel.innerHTML = "";

  // Buttons
  const attackBtn = document.createElement("button");
  attackBtn.textContent = "Attack";
  attackBtn.onclick = onAttackClicked;
  attackBtn.className = "ui-btn";

  const negotiateBtn = document.createElement("button");
  negotiateBtn.textContent = "Negotiate";
  negotiateBtn.onclick = onNegotiateClicked;
  negotiateBtn.className = "ui-btn";

  const expandBtn = document.createElement("button");
  expandBtn.textContent = "Expand";
  expandBtn.onclick = onExpandClicked;
  expandBtn.className = "ui-btn";

  const info = document.createElement("div");
  info.id = "selectedInfo";
  info.style.marginTop = "10px";
  info.style.color = "#eee";

  panel.appendChild(attackBtn);
  panel.appendChild(negotiateBtn);
  panel.appendChild(expandBtn);
  panel.appendChild(info);

  const log = document.getElementById(LOG_ID);
  log.innerHTML = "<b>Event Log</b><br>";
}

// -----------------------------
// Logging
// -----------------------------
function logEvent(msg) {
  const log = document.getElementById(LOG_ID);
  const time = new Date().toLocaleTimeString();
  log.innerHTML = `<div>[${time}] ${escapeHtml(msg)}</div>` + log.innerHTML;
}

// tiny escape to avoid injecting content
function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

// -----------------------------
// Sample Galaxy generation
// -----------------------------
function createSampleGalaxy() {
  // small deterministic sample (you may replace by dynamic generation)
  // we'll place 12 systems across the canvas
  galaxies = {};
  adjacency = {};
  planets = [];

  const seedPositions = [
    [80, 80],[240,60],[420,100],[640,80],[820,120],[120,200],
    [320,200],[520,200],[720,220],[200,360],[480,360],[760,360]
  ];

  for (let i = 0; i < seedPositions.length; i++) {
    const id = String(i);
    const pos = seedPositions[i];
    const owner = (i % 3 === 0) ? 0 : ((i % 3 === 1) ? 1 : null); // some owned
    const resources = 80 + Math.floor(Math.random() * 220);
    galaxies[id] = { pos: pos, owner: owner, resources: resources, population: 10 + Math.floor(Math.random() * 40) };
    planets.push(id);
  }

  // adjacency: connect neighbors roughly by x-distance
  for (let i = 0; i < planets.length; i++) {
    const id = planets[i];
    adjacency[id] = [];
    for (let j = 0; j < planets.length; j++) {
      if (i === j) continue;
      // connect if distance less than threshold
      const d = dist(galaxies[id].pos, galaxies[String(j)].pos);
      if (d < 260) adjacency[id].push(String(j));
    }
  }
}

// -----------------------------
// Attach galaxy to backend
// -----------------------------
async function attachGalaxyToBackend() {
  // shape payload to match backend expectation
  const systems = {};
  for (const id of planets) {
    const s = galaxies[id];
    systems[id] = { pos: s.pos, owner: s.owner, resources: s.resources };
  }
  const payload = { systems: systems, adj: adjacency, max_dist: Math.max(width, height) };
  try {
    const resp = await fetch(`${API_BASE}/attach_galaxy`, {
      method: "POST",
      headers: { "Content-Type":"application/json" },
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    if (data.error) {
      logEvent("Attach failed: " + data.error);
    } else {
      logEvent("Galaxy attached to AI engine successfully.");
    }
  } catch (err) {
    console.error("Attach error:", err);
    logEvent("Failed to attach galaxy to backend. Is server running?");
  }
}

// -----------------------------
// Canvas interactions
// -----------------------------
function draw() {
  // background
  ctx.fillStyle = "#050814";
  ctx.fillRect(0,0,width,height);

  // draw links
  ctx.strokeStyle = "rgba(255,255,255,0.06)";
  ctx.lineWidth = 1;
  for (const a of planets) {
    const pa = galaxies[a].pos;
    for (const b of adjacency[a]) {
      const pb = galaxies[b].pos;
      // draw once (only if a < b)
      if (Number(a) < Number(b)) {
        ctx.beginPath();
        ctx.moveTo(pa[0], pa[1]);
        ctx.lineTo(pb[0], pb[1]);
        ctx.stroke();
      }
    }
  }

  // draw planets
  for (const id of planets) {
    const s = galaxies[id];
    drawPlanet(id, s);
  }

  // draw animations
  updateAnimations();

  // draw HUD selection
  drawHUD();

  if (!animating) {
    // request next frame
    window.requestAnimationFrame(draw);
  } else {
    // while animating we still loop via animation frame calls inside updateAnimations
    window.requestAnimationFrame(draw);
  }
}

function drawPlanet(id, s) {
  const [x,y] = s.pos;
  // glow
  ctx.beginPath();
  const gradient = ctx.createRadialGradient(x, y, 2, x, y, PLANET_RADIUS*3);
  const color = s.owner === null ? "#666" : COLORS[s.owner % COLORS.length];
  gradient.addColorStop(0, hexToRGBA(color, 0.35));
  gradient.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = gradient;
  ctx.arc(x, y, PLANET_RADIUS*2.2, 0, Math.PI*2);
  ctx.fill();

  // planet body
  ctx.beginPath();
  ctx.fillStyle = color;
  ctx.arc(x, y, PLANET_RADIUS, 0, Math.PI*2);
  ctx.fill();

  // ring for owned by player
  if (s.owner === playerId) {
    ctx.beginPath();
    ctx.lineWidth = 3;
    ctx.strokeStyle = "rgba(255,255,255,0.8)";
    ctx.arc(x, y, PLANET_RADIUS + 4, 0, Math.PI*2);
    ctx.stroke();
  }

  // label
  ctx.fillStyle = "#fff";
  ctx.font = "12px Inter, Arial";
  ctx.fillText(id, x-6, y+4);

  // resource marker
  ctx.fillStyle = "rgba(255,255,255,0.12)";
  ctx.fillText("R:" + s.resources, x-18, y+26);
}

function drawHUD() {
  const info = document.getElementById("selectedInfo");
  if (!info) return;
  if (selectedPlanet == null) {
    info.innerHTML = "Selected: none";
  } else {
    const s = galaxies[selectedPlanet];
    info.innerHTML = `Selected: ${selectedPlanet} | owner: ${s.owner === null ? "none" : s.owner} | res: ${s.resources}`;
  }
}

function onCanvasClick(e) {
  const rect = canvas.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  // find nearest planet within radius
  let found = null;
  for (const id of planets) {
    const p = galaxies[id].pos;
    const d = dist([x,y], p);
    if (d <= PLANET_RADIUS + 6) {
      found = id;
      break;
    }
  }
  if (found !== null) {
    selectedPlanet = found;
    logEvent("Selected planet " + found);
    drawHUD();
  } else {
    // click on empty space: if there is a selected planet and we click on another area, maybe deselect
    // nothing for now
  }
}

// -----------------------------
// Player actions
// -----------------------------
async function onAttackClicked() {
  if (!selectedPlanet) {
    alert("Select a planet to attack from (your owned planet).");
    return;
  }
  // choose a target (simple: prompt for id)
  const target = prompt("Enter target planet id to attack:");
  if (!target || !(target in galaxies)) {
    alert("Invalid target id.");
    return;
  }
  // call backend
  const payload = { type: "attack", from: selectedPlanet, to: target, player_id: playerId };
  logEvent(`Player Attack: ${selectedPlanet} -> ${target}`);
  await sendPlayerMove(payload);
}

async function onNegotiateClicked() {
  if (!selectedPlanet) {
    alert("Select a planet (to negotiate from).");
    return;
  }
  const target = prompt("Enter empire id to negotiate with (0 or 1 or 2...):");
  if (target === null) return;
  const trustOffer = prompt("Offer trust value (0.0 .. 1.0) [default 0.5]:", "0.5");
  const rel_power = prompt("Relative power estimate (e.g. 1.0):", "1.0");
  const distance = prompt("Distance heuristic (number):", "10");
  const payload = {
    type: "negotiate",
    player_id: playerId,
    with: Number(target),
    offer: { trust: Number(trustOffer), rel_power: Number(rel_power), distance: Number(distance) }
  };
  logEvent(`Player Negotiates with empire ${target}`);
  await sendPlayerMove(payload);
}

async function onExpandClicked() {
  const payload = { type: "expand", player_id: playerId, slots: 1 };
  logEvent("Player requests expand.");
  await sendPlayerMove(payload);
}

// -----------------------------
// Networking: player move -> backend
// -----------------------------
async function sendPlayerMove(payload) {
  try {
    const resp = await fetch(`${API_BASE}/player_move`, {
      method: "POST",
      headers: { "Content-Type":"application/json" },
      body: JSON.stringify(payload)
    });
    const data = await resp.json();
    handleBackendResponse(data);
  } catch (err) {
    console.error("player_move error:", err);
    logEvent("Error communicating with backend.");
  }
}

function handleBackendResponse(data) {
  if (!data) return;
  if (data.error) {
    logEvent("Backend error: " + data.error);
    return;
  }
  if (data.result === "attack_path" && data.path) {
    logEvent("Backend returned path: " + data.path.join(" -> "));
    // animate fleet along path
    animatePath(data.path);
    // if target_owner exists, show message
    if (data.target_owner !== undefined && data.target_owner !== null) {
      logEvent("Target owned by empire: " + data.target_owner);
    } else {
      logEvent("Target unowned.");
    }
  } else if (data.result === "negotiation") {
    const decision = data.decision || "unknown";
    logEvent("Negotiation result: " + decision + " (cooperation=" + (data.fuzzy ? data.fuzzy.cooperation.toFixed(2) : "?") + ")");
  } else if (data.result === "expand_requested") {
    logEvent("Expand requested: " + (data.message || ""));
  } else {
    // general printout
    logEvent("AI Response: " + JSON.stringify(data));
  }
}

// -----------------------------
// Animation utilities
// -----------------------------
function animatePath(path) {
  // path is array of node ids; create animation between consecutive node positions
  if (!path || path.length < 2) return;
  const legs = [];
  for (let i = 0; i < path.length - 1; i++) {
    const a = galaxies[path[i]].pos;
    const b = galaxies[path[i+1]].pos;
    legs.push({ from: a.slice(), to: b.slice() });
  }
  // start at the first planet slightly offset
  const ship = { x: legs[0].from[0], y: legs[0].from[1], size: 8, color: "#fff" };
  animationQueue.push({ ship: ship, legs: legs, legIndex: 0, progress: 0, speed: 0.012 + Math.random()*0.02 });
  animating = true;
}

function updateAnimations() {
  if (animationQueue.length === 0) {
    animating = false;
    return;
  }
  animating = true;
  // draw each animated ship
  for (let i = animationQueue.length - 1; i >= 0; i--) {
    const anim = animationQueue[i];
    const leg = anim.legs[anim.legIndex];
    // progress increment
    anim.progress += anim.speed;
    if (anim.progress >= 1.0) {
      // move to next leg
      anim.ship.x = leg.to[0];
      anim.ship.y = leg.to[1];
      anim.legIndex += 1;
      anim.progress = 0;
      if (anim.legIndex >= anim.legs.length) {
        // finished
        logEvent("Fleet arrived at destination.");
        animationQueue.splice(i, 1);
        continue;
      }
    } else {
      // interpolate on current leg
      const sx = leg.from[0], sy = leg.from[1];
      const tx = leg.to[0], ty = leg.to[1];
      anim.ship.x = sx + (tx - sx) * anim.progress;
      anim.ship.y = sy + (ty - sy) * anim.progress;
    }
    // draw ship
    ctx.beginPath();
    ctx.fillStyle = anim.ship.color;
    ctx.arc(anim.ship.x, anim.ship.y, anim.ship.size, 0, Math.PI*2);
    ctx.fill();

    // trail
    ctx.beginPath();
    ctx.fillStyle = "rgba(255,255,255,0.08)";
    ctx.arc(anim.ship.x, anim.ship.y, anim.ship.size*2.5, 0, Math.PI*2);
    ctx.fill();
  }
}

// -----------------------------
// Helpers
// -----------------------------
function dist(a,b) {
  const dx = a[0]-b[0], dy = a[1]-b[1];
  return Math.sqrt(dx*dx + dy*dy);
}

function hexToRGBA(hex, alpha) {
  // accepts #rrggbb
  const h = hex.replace("#","");
  const r = parseInt(h.substring(0,2),16);
  const g = parseInt(h.substring(2,4),16);
  const b = parseInt(h.substring(4,6),16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// -----------------------------
// Startup
// -----------------------------
window.addEventListener("load", () => {
  init();
  logEvent("Frontend loaded. Click planets to select, then use buttons to act.");
});
