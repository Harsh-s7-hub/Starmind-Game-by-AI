document.getElementById("attackBtn").addEventListener("click", () => {
  const action = { type: "attack", from: "A1", to: "B3" };
  fetch("http://127.0.0.1:5000/api/player_move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(action)
  })
  .then(res => res.json())
  .then(data => {
    console.log("AI Response:", data);
  });
});
