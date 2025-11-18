// =========================
//  frontend/js/main.js
// =========================

import { apiInit, getState } from "./api.js";
window.apiInit = apiInit;

const gameState = { player: { name: "Commander" } };

function initAudio() {}
function startMusic() {}
function initCivilizations() {}
function renderGalaxy() {}
function updateHUD() {}
function updateControlPanel() {}
function showNotification(m, type) { console.log("[NOTIF]", type, m); }
function speak(m) { console.log("[SPEECH]", m); }


// -----------------------------------------------------
// 1. START GAME — TITLE SCREEN → TRANSITION VIDEO
// -----------------------------------------------------
function startGame() {

  const bg = document.getElementById("bg-music");
  bg.volume = 1.0;
  bg.play().catch(e => console.log("Autoplay was blocked:", e));

  const name = document.getElementById("commander-name").value.trim() || "Commander";
  gameState.player.name = name;

  const intro = document.getElementById("intro-video");
  const transition = document.getElementById("transition-video");
  const flash = document.getElementById("white-flash");
  const opening = document.getElementById("opening-screen");

  intro.style.opacity = "0";
  opening.style.opacity = "0";

  setTimeout(() => opening.style.display = "none", 1000);

  transition.style.display = "block";
  transition.currentTime = 0;
  transition.play();

  setTimeout(() => transition.style.opacity = "1", 200);

  transition.onended = () => {
    flash.style.opacity = "1";

    setTimeout(() => {
      transition.style.opacity = "0";

      setTimeout(() => {
        transition.style.display = "none";
        flash.style.opacity = "0";
        showInitSequence(name);
      }, 1000);

    }, 1000);
  };
}


// -----------------------------------------------------
// 2. TYPING INITIALIZATION SEQUENCE
// -----------------------------------------------------
function showInitSequence(name) {

  const overlay = document.getElementById("init-sequence");
  const textElem = document.getElementById("terminal-text");
  const typeSound = document.getElementById("type-sound");
  const awaitBlock = document.getElementById("await-block");
  const okBtn = document.getElementById("ok-btn");

  overlay.style.display = "flex";
  overlay.style.opacity = "1";

  const lines = [
    "SYSTEM BOOTING...",
    "AI CORE CALIBRATION SEQUENCE INITIATED...",
    "LOADING INTERSTELLAR DATABASES...",
    "SYNCHRONIZING STAR NETWORK PROTOCOLS...",
    "ENERGY CORES AT 98% CAPACITY...",
    "COMMANDER AUTHENTICATION SUCCESSFUL...",
    `WELCOME COMMANDER ${name.toUpperCase()}...`,
    "INITIALIZATION COMPLETE."
  ];

  let i = 0;

  function typeLine() {

    if (i >= lines.length) {
      typeSound.pause();
      typeSound.currentTime = 0;

      awaitBlock.style.display = "flex";
      setTimeout(() => {
        awaitBlock.style.opacity = "1";
        awaitBlock.style.transform = "translateY(0)";
      }, 100);
      return;
    }

    let line = lines[i];
    let j = 0;
    let deleting = false;

    function type() {

      if (!deleting) {
        if (j < line.length) {
          textElem.textContent = line.substring(0, j + 1);

          if (j % 2 === 0) {
            typeSound.currentTime = 0;
            typeSound.play().catch(_=>{});
          }

          j++;
          setTimeout(type, 45);

        } else {
          setTimeout(() => { deleting = true; type(); }, 600);
        }

      } else {

        if (j > 0) {
          textElem.textContent = line.substring(0, j - 1);
          j--;
          setTimeout(type, 25);

        } else {
          typeSound.pause();
          typeSound.currentTime = 0;
          i++;
          setTimeout(typeLine, 400);
        }

      }
    }
    type();
  }

  typeLine();

  okBtn.onclick = () => {
    awaitBlock.style.opacity = "0";
    overlay.style.transition = "opacity 1.5s ease";
    overlay.style.opacity = "0";

    setTimeout(() => {
      overlay.style.display = "none";
      playCinemaVideo(name);
    }, 1500);
  };
}


// -----------------------------------------------------
// 3. CINEMA VIDEO → then LOADING VIDEO → start simulation
// -----------------------------------------------------
async function playCinemaVideo(name) {

  const cinema = document.getElementById("cinema-video");
  const loadingVideo = document.getElementById("loading-video");
  const flash = document.getElementById("white-flash");
  const bgMusic = document.getElementById("bg-music");

  cinema.muted = false;
  cinema.style.display = "block";
  cinema.currentTime = 0;
  cinema.play();
  setTimeout(() => cinema.style.opacity = "1", 200);

  let fadeDown = setInterval(() => {
    if (bgMusic.volume > 0.1) bgMusic.volume -= 0.02;
    else clearInterval(fadeDown);
  }, 100);

  cinema.onended = async () => {

  // No flash screen here (removed the white blink)
  cinema.style.opacity = "0";

  setTimeout(async () => {

    cinema.style.display = "none";

    // ---------------------------
    // SHOW LOADING VIDEO (NO FLASH)
    // ---------------------------
    const loadingVideo = document.getElementById("loading-video");
    loadingVideo.style.display = "block";
    loadingVideo.currentTime = 0;
    loadingVideo.play();

    setTimeout(() => loadingVideo.style.opacity = "1", 50);

    // FORCE LOADING TO LAST EXACTLY 5 SECONDS
    setTimeout(async () => {

      // Fade out loading video
      loadingVideo.style.opacity = "0";

      setTimeout(async () => {
        loadingVideo.style.display = "none";

        // Start backend + simulation
        try {
          await apiInit(name);
          const state = await getState();
          GameUI.start(state);
        } catch (err) {
          alert("Could not reach backend server.");
        }

      }, 600);

    }, 5000); // <-- 5 seconds loading time

  }, 600);
};

}


// -----------------------------------------------------
// Event Listeners
// -----------------------------------------------------
document.getElementById("start-btn").addEventListener("click", startGame);
document.getElementById("commander-name").addEventListener("keypress", e => {
  if (e.key === "Enter") startGame();
});
