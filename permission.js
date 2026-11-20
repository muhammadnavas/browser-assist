const grantBtn = document.getElementById("grantBtn");
const permStatus = document.getElementById("permStatus");
const desc = document.getElementById("desc");
const helpHint = document.getElementById("helpHint");

async function requestMic() {
  permStatus.textContent = "Requesting permission from Chrome...";
  permStatus.style.color = "#8b7cff";
  helpHint.style.display = "none";

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    // Stop tracks immediately so mic indicator turns off
    stream.getTracks().forEach(track => track.stop());

    grantBtn.style.display = "none";
    desc.textContent = "Microphone access is granted! You can now close this tab and return to the Voice Assistant in the side panel.";
    permStatus.textContent = "✓ Microphone enabled! Closing tab...";
    permStatus.style.color = "#51d6a1";

    setTimeout(() => {
      window.close();
    }, 1800);
  } catch (err) {
    permStatus.textContent = `Permission error: ${err.name || "Blocked"} (${err.message})`;
    permStatus.style.color = "#ff668b";
    helpHint.style.display = "block";
  }
}

grantBtn.addEventListener("click", requestMic);

// Automatically attempt prompt on page load
window.addEventListener("DOMContentLoaded", () => {
  requestMic();
});
