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
let isStarting = false;
let autoListen = true;
let permissionTabOpened = false;
let restartTimer = null;

function setListening(value) {
  isListening = value;
  micLabel.textContent = value ? "Listening automatically" : "Preparing microphone...";
  micIcon.textContent = value ? "◉" : "🎙";
  orb.classList.toggle("active", value);
  statusDot.classList.toggle("listening", value);
  statusDot.title = value ? "Listening" : "Connecting";
  headline.textContent = value ? "I'm listening..." : "Getting ready to listen...";
  subheadline.textContent = value
    ? "Just say a command, such as “Open ChatGPT”."
    : "Voice recognition will start automatically.";
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
    subheadline.textContent = "I'll keep listening for your next command.";
    addHistory(originalText, "Completed");
  } catch (error) {
    heardText.textContent = error.message;
    headline.textContent = "Couldn't do that";
    subheadline.textContent = "I'll keep listening. Try another command.";
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
        subheadline.textContent = "I'll keep listening for another command.";
        addHistory(text, "Not understood");
        return;
      }
    }
  }

  if (!command) {
    heardText.textContent = "I didn't recognize that. Try “Open ChatGPT” or “Search for JavaScript promises”.";
    headline.textContent = "Command not recognized";
    subheadline.textContent = "I'll keep listening for another command.";
    addHistory(text, "Not recognized");
    return;
  }
  await execute(command, text);
}

function openPermissionTab() {
  if (permissionTabOpened) return;
  permissionTabOpened = true;
  chrome.tabs.create({ url: chrome.runtime.getURL("permission.html") });
}

function scheduleRestart(delay = 700) {
  if (!autoListen || restartTimer) return;
  restartTimer = setTimeout(() => {
    restartTimer = null;
    startRecognition();
  }, delay);
}

async function startRecognition() {
  if (!autoListen || isListening || isStarting) return;
  if (!SpeechRecognition) {
    heardText.textContent = "Speech recognition isn't available here. Please use desktop Chrome.";
    headline.textContent = "Speech recognition unavailable";
    return;
  }

  isStarting = true;
  try {
    if (navigator.permissions?.query) {
      const permission = await navigator.permissions.query({ name: "microphone" });
      if (permission.state !== "granted") {
        isStarting = false;
        setListening(false);
        heardText.textContent = "Allow microphone access once in the tab Chrome opened. Listening will then start automatically.";
        openPermissionTab();
        permission.onchange = () => {
          if (permission.state === "granted") {
            permissionTabOpened = false;
            startRecognition();
          }
        };
        return;
      }
    }

    const currentRecognition = new SpeechRecognition();
    recognition = currentRecognition;
    currentRecognition.lang = "en-IN";
    currentRecognition.continuous = false;
    currentRecognition.interimResults = true;
    currentRecognition.maxAlternatives = 1;
    let finalTranscript = "";

    currentRecognition.onstart = () => {
      isStarting = false;
      setListening(true);
    };

    currentRecognition.onresult = event => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalTranscript += transcript + " ";
        else interim += transcript;
      }
      heardText.textContent = finalTranscript.trim() || interim || "Listening...";
    };

    currentRecognition.onerror = event => {
      if (recognition !== currentRecognition) return;
      isStarting = false;
      setListening(false);
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        heardText.textContent = "Microphone access was blocked. Allow it in Chrome site settings, then reopen the side panel.";
        autoListen = false;
        return;
      }
      const messages = {
        "no-speech": "I didn't hear anything. Still listening...",
        "network": "Speech recognition needs an internet connection. I'll retry when possible.",
        "audio-capture": "No microphone was found. Check your microphone connection."
      };
      heardText.textContent = messages[event.error] || `Speech recognition issue: ${event.error}. Retrying...`;
    };

    currentRecognition.onend = async () => {
      if (recognition !== currentRecognition) return;
      recognition = null;
      isStarting = false;
      setListening(false);
      if (finalTranscript.trim()) await handleTranscript(finalTranscript);
      scheduleRestart(900);
    };

    currentRecognition.start();
  } catch (error) {
    isStarting = false;
    setListening(false);
    heardText.textContent = `Couldn't start voice recognition: ${error.message}`;
    scheduleRestart(2000);
  }
}

// Start hands-free listening as soon as the side panel loads.
startRecognition();

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
