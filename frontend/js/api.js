// frontend/js/api.js
const API_BASE = "http://127.0.0.1:5000/api";


// --- GET FULL GAME STATE ---
export async function getState() {
  const r = await fetch(`${API_BASE}/state`);
  return r.json();
}

// --- SET PLAYER NAME AND INIT GAME ---
export async function apiInit(name) {
  const r = await fetch(`${API_BASE}/set_name`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name })
  });
  return r.json();
}

// --- NEGOTIATE ---
export async function actionNegotiate(civ_id) {
  const r = await fetch(`${API_BASE}/negotiate/${civ_id}`, { method: "POST" });
  return r.json();
}

// --- TRADE ---
export async function actionTrade(civ_id) {
  const r = await fetch(`${API_BASE}/trade/${civ_id}`, { method: "POST" });
  return r.json();
}

// --- ATTACK ---
export async function actionAttack(civ_id) {
  const r = await fetch(`${API_BASE}/attack/${civ_id}`, { method: "POST" });
  return r.json();
}

// --- EXPOSE ONE FUNCTION FOR GAME.JS ---
window.apiAction = async function(action, civ_id) {
  if (action === "negotiate") return await actionNegotiate(civ_id);
  if (action === "trade") return await actionTrade(civ_id);
  if (action === "attack") return await actionAttack(civ_id);
  return { ok: false, message: "Unknown action" };
};

// --- EXPOSE INIT ---
window.apiInit = apiInit;
