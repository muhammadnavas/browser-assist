const micButton = document.getElementById("micButton");
const micLabel = document.getElementById("micLabel");
const micIcon = document.getElementById("micIcon");
const heardText = document.getElementById("heardText");
const headline = document.getElementById("headline");
const subheadline = document.getElementById("subheadline");
const orb = document.getElementById("orb");
const statusDot = document.getElementById("statusDot");
const historyEl = document.getElementById("history");
const apiKeyInput = document.getElementById("apiKey");
const settingsStatus = document.getElementById("settingsStatus");

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let isListening = false;

function setListening(value) {
  isListening = value;
  micButton.disabled = false;
  micLabel.textContent = value ? "Listening..." : "Start listening";
  micIcon.textContent = value ? "◉" : "🎙";
  orb.classList.toggle("active", value);
  statusDot.classList.toggle("listening", value);
  statusDot.title = value ? "Listening" : "Ready";
  headline.textContent = value ? "I'm listening..." : "What can I do for you?";
  subheadline.textContent = value ? "Speak clearly. I'm ready." : "Tap the microphone and tell me what to open.";
}

function addHistory(command, result) {
  const empty = historyEl.querySelector(".empty");
  if (empty) empty.remove();
  const item = document.createElement("div");
  item.className = "history-item";
  const left = document.createElement("span");
  const right = document.createElement("span");
  left.textContent = command;
  right.textContent = result;
  item.append(left, right);
  historyEl.prepend(item);
  while (historyEl.children.length > 6) historyEl.lastElementChild.remove();
}

async function execute(command, originalText) {
  headline.textContent = "Working on it...";
  subheadline.textContent = "Executing your browser command.";
  try {
    const response = await chrome.runtime.sendMessage({ type: "EXECUTE_COMMAND", command });
    if (!response?.ok) throw new Error(response?.error || "Command failed.");
    heardText.textContent = response.message;
    headline.textContent = "Done!";
    subheadline.textContent = "Ready for your next command.";
    addHistory(originalText, "Completed");
  } catch (error) {
    heardText.textContent = error.message;
    headline.textContent = "Couldn't do that";
    subheadline.textContent = "Try another command.";
    addHistory(originalText, "Failed");
  }
}

async function handleTranscript(transcript) {
  const text = transcript.trim();
  if (!text) return;
  heardText.textContent = `“${text}”`;
  let command = parseLocalCommand(text);

  if (!command) {
    const { geminiApiKey } = await chrome.storage.local.get("geminiApiKey");
    if (geminiApiKey) {
      try {
        const response = await chrome.runtime.sendMessage({
          type: "AI_INTERPRET", text, apiKey: geminiApiKey
        });
        if (!response?.ok) throw new Error(response?.error || "AI interpretation failed.");
        command = response.command;
        if (command.action === "unsupported") throw new Error("I don't support that command yet.");
      } catch (error) {
        heardText.textContent = error.message;
        headline.textContent = "Couldn't understand";
        subheadline.textContent = "Try a simpler command or check AI settings.";
        addHistory(text, "Not understood");
        return;
      }
    }
  }

  if (!command) {
    heardText.textContent = "I didn't recognize that. Try “Open GitHub” or “Search for JavaScript promises”.";
    headline.textContent = "Command not recognized";
    subheadline.textContent = "You can enable Gemini for more flexible requests.";
    addHistory(text, "Not recognized");
    return;
  }
  await execute(command, text);
}

function openPermissionTab() {
  chrome.tabs.create({ url: chrome.runtime.getURL("permission.html") });
}

// Watch for microphone permission changes
if (navigator.permissions && navigator.permissions.query) {
  navigator.permissions.query({ name: "microphone" }).then(status => {
    status.onchange = () => {
      if (status.state === "granted") {
        heardText.textContent = "Microphone access enabled! Click 'Start listening' to speak.";
        headline.textContent = "What can I do for you?";
        subheadline.textContent = "Tap the microphone and tell me what to open.";
      }
    };
  }).catch(() => {});
}

async function startRecognition() {
  if (!SpeechRecognition) {
    heardText.textContent = "Speech recognition isn't available in this Chrome environment. Try the supported desktop Chrome browser.";
    return;
  }
  if (isListening) {
    recognition?.stop();
    return;
  }

  // Chrome Side Panel does not display permission prompts. If not granted, open permission tab.
  if (navigator.permissions && navigator.permissions.query) {
    try {
      const perm = await navigator.permissions.query({ name: "microphone" });
      if (perm.state !== "granted") {
        heardText.innerHTML = 'Microphone permission needed. Opening permission tab...<br><a href="#" id="permLink" style="color:#58d6d0;text-decoration:underline;margin-top:6px;display:inline-block;">Click here if tab didn\'t open</a>';
        document.getElementById("permLink")?.addEventListener("click", (e) => {
          e.preventDefault();
          openPermissionTab();
        });
        openPermissionTab();
        return;
      }
    } catch (e) {
      // Continue to try start() if permissions query fails
    }
  }

  recognition = new SpeechRecognition();
  recognition.lang = "en-IN";
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;
  let finalTranscript = "";

  recognition.onstart = () => setListening(true);
  recognition.onresult = event => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) finalTranscript += transcript;
      else interim += transcript;
    }
    heardText.textContent = finalTranscript || interim || "Listening...";
  };
  recognition.onerror = event => {
    setListening(false);
    if (event.error === "not-allowed") {
      heardText.innerHTML = 'Microphone permission was blocked. <a href="#" id="permLink" style="color:#58d6d0;text-decoration:underline;">Click here to grant access in a new tab</a>.';
      document.getElementById("permLink")?.addEventListener("click", (e) => {
        e.preventDefault();
        openPermissionTab();
      });
      openPermissionTab();
      return;
    }
    const messages = {
      "no-speech": "I didn't hear anything. Please try again.",
      "network": "Speech recognition needs a network connection in this browser."
    };
    heardText.textContent = messages[event.error] || `Speech recognition error: ${event.error}`;
  };
  recognition.onend = async () => {
    setListening(false);
    if (finalTranscript.trim()) await handleTranscript(finalTranscript);
  };

  try { recognition.start(); }
  catch (error) { setListening(false); heardText.textContent = error.message; }
}

micButton.addEventListener("click", startRecognition);
document.querySelectorAll("[data-command]").forEach(button => {
  button.addEventListener("click", () => {
    const text = button.dataset.command;
    heardText.textContent = `“${text}”`;
    const command = parseLocalCommand(text);
    if (command) execute(command, text);
  });
});

document.getElementById("clearHistory").addEventListener("click", () => {
  historyEl.innerHTML = '<p class="empty">Your commands will show up here.</p>';
});

async function loadSettings() {
  const { geminiApiKey } = await chrome.storage.local.get("geminiApiKey");
  apiKeyInput.value = geminiApiKey || "";
}
document.getElementById("saveKey").addEventListener("click", async () => {
  await chrome.storage.local.set({ geminiApiKey: apiKeyInput.value.trim() });
  settingsStatus.textContent = apiKeyInput.value.trim() ? "API key saved on this browser." : "API key cleared.";
});
document.getElementById("enableGemini").addEventListener("click", async () => {
  const granted = await chrome.permissions.request({
    origins: ["https://generativelanguage.googleapis.com/*"]
  });
  settingsStatus.textContent = granted
    ? "Gemini access enabled. Save your API key to use it."
    : "Permission was not granted. Local commands still work.";
});
loadSettings();