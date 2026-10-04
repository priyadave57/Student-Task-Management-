document.addEventListener("DOMContentLoaded", () => {
  const el = document.getElementById("today");
  if (el) el.textContent = new Date().toLocaleDateString("en-IN", {weekday:"long", day:"numeric", month:"long", year:"numeric"});
});