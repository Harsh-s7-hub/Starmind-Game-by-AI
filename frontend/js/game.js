// frontend/js/game.js

const GameUI = (function () {
  const canvas = document.getElementById("space-background");
  const ctx = canvas.getContext("2d");
  let state = null;
  let stars = [];
  let animFrame = null;

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    generateStars();
  }

  function generateStars() {
    stars = [];
    const count = 300;
    for (let i = 0; i < count; i++) {
      stars.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        size: Math.random() * 1.8 + 0.2,
        alpha: 0.2 + Math.random() * 0.8
      });
    }
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    // background
    ctx.fillStyle = "rgba(0,0,0,0.7)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // stars
    for (const s of stars) {
      ctx.beginPath();
      ctx.fillStyle = `rgba(255,255,255,${s.alpha})`;
      ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
      ctx.fill();
    }

    if (state && state.civilizations) {
      for (const civ of state.civilizations) {
        drawCiv(civ);
      }
    }
    animFrame = requestAnimationFrame(draw);
  }

  function drawCiv(civ) {
    // convert percentage coordinates to canvas pixels
    const cx = (civ.x / 100) * canvas.width;
    const cy = (civ.y / 100) * canvas.height;
    const radius = 18 + (civ.territory / 2);

    // color by relation/trust
    let color = "#888";
    if (civ.relation === "friendly") color = "#0ff";
    else if (civ.relation === "hostile") color = "#f55";
    else if (civ.relation === "neutral") color = "#ffb";

    // planet glow
    const grad = ctx.createRadialGradient(cx, cy, 2, cx, cy, radius * 2);
    grad.addColorStop(0, color);
    grad.addColorStop(0.3, "rgba(0,0,0,0)");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(cx, cy, radius * 1.6, 0, Math.PI * 2);
    ctx.fill();

    // planet body
    ctx.beginPath();
    ctx.fillStyle = color;
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fill();

    // name label
    ctx.font = "12px Courier New";
    ctx.fillStyle = "#fff";
    ctx.textAlign = "center";
    ctx.fillText(civ.name, cx, cy + radius + 14);
  }

  function start(stateObj) {
    state = stateObj;
    resize();
    cancelAnimationFrame(animFrame);
    animFrame = requestAnimationFrame(draw);
    // update HUD (create simple HUD if not present)
    renderHUD(state.player);
    // click handler
    canvas.onclick = (e) => {
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      handleCanvasClick(mx, my);
    };
    window.addEventListener("resize", resize);
  }

  function renderHUD(player) {
    // create a simple HUD top-left if not present
    let hud = document.getElementById("simple-hud");
    if (!hud) {
      hud = document.createElement("div");
      hud.id = "simple-hud";
      hud.style.position = "fixed";
      hud.style.left = "16px";
      hud.style.top = "16px";
      hud.style.zIndex = 4000;
      hud.style.background = "rgba(0,0,0,0.4)";
      hud.style.border = "2px solid rgba(0,255,255,0.2)";
      hud.style.color = "#0ff";
      hud.style.padding = "10px 14px";
      hud.style.fontFamily = "'Courier New', monospace";
      hud.style.fontSize = "14px";
      hud.style.borderRadius = "6px";
      document.body.appendChild(hud);
    }
    hud.innerHTML = `
      <div><strong>COMMANDER:</strong> ${player.name}</div>
      <div>💰 Credits: <span id="hud-credits">${player.credits}</span></div>
      <div>⚡ Power: <span id="hud-power">${player.power}</span></div>
      <div>🌍 Systems: <span id="hud-systems">${player.systems}</span></div>
      <div>🤝 Allies: <span id="hud-allies">${player.allies || 0}</span></div>  
      <div style="margin-top:6px"><small>Click a planet to interact (negotiate/trade/attack)</small></div>
    `;
  }

  function handleCanvasClick(mx, my) {
    if (!state) return;
    // find nearest civ within a threshold
    let nearest = null;
    let distMin = Infinity;
    for (const civ of state.civilizations) {
      const cx = (civ.x / 100) * canvas.width;
      const cy = (civ.y / 100) * canvas.height;
      const dx = mx - cx;
      const dy = my - cy;
      const d = Math.sqrt(dx * dx + dy * dy);
      if (d < distMin) {
        distMin = d;
        nearest = civ;
      }
    }
    if (nearest && distMin < 60) {
      // open simple action dialog (native prompt to keep things short)
      const action = prompt(
        `Interact with ${nearest.name} (type: ${nearest.type})\nChoose action: negotiate / trade / attack`,
        "negotiate"
      );
      if (!action) return;
      // call API
      window.apiAction(action.toLowerCase(), nearest.id)
        .then(resp => {
          if (resp.ok) {
            alert(resp.message || "Action completed");
            // update local state and HUD from server state
            state = resp.state;
            updateHUD(resp.state.player);
          } else {
            alert("Action failed: " + (resp.message || "unknown"));
          }
        })
        .catch(err => {
          console.error(err);
          alert("Network or server error");
        });
    }
  }

  function updateHUD(player) {
    const credits = document.getElementById("hud-credits");
    const power = document.getElementById("hud-power");
    const systems = document.getElementById("hud-systems");
    const allies = document.getElementById("hud-allies");
    if (credits) credits.textContent = player.credits;
    if (power) power.textContent = player.power;
    if (systems) systems.textContent = player.systems;
    if (allies) allies.textContent = player.allies || 0;
  }

  return {
    start,
    updateHUD
  };
})();
