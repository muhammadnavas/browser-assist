// Service worker: owns browser actions. AI is optional and only returns a proposed command.
chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
});

const ALLOWED_SITES = {
  github: "https://github.com/",
  chatgpt: "https://chatgpt.com/",
  openai: "https://openai.com/",
  youtube: "https://www.youtube.com/",
  gmail: "https://mail.google.com/",
  google: "https://www.google.com/",
  drive: "https://drive.google.com/",
  docs: "https://docs.google.com/",
  calendar: "https://calendar.google.com/",
  linkedin: "https://www.linkedin.com/",
  twitter: "https://x.com/",
  x: "https://x.com/",
  stackoverflow: "https://stackoverflow.com/",
  "stack overflow": "https://stackoverflow.com/",
  vercel: "https://vercel.com/",
  portfolio: "https://navas.vercel.app/"
};

function normalizeSiteName(name) {
  return String(name || "").trim().toLowerCase().replace(/\s+/g, " ");
}

async function executeCommand(command) {
  const action = command?.action;

  if (action === "open_sites") {
    const sites = Array.isArray(command.sites) ? command.sites : [];
    const urls = sites
      .map(normalizeSiteName)
      .map(name => ALLOWED_SITES[name])
      .filter(Boolean);

    if (!urls.length) throw new Error("I couldn't identify a supported website.");
    if (urls.length > 8) throw new Error("Please open no more than 8 tabs at once.");

    const createdTabs = [];
    for (const url of urls) {
      createdTabs.push(await chrome.tabs.create({ url, active: false }));
    }
    if (createdTabs[0]?.id) await chrome.tabs.update(createdTabs[0].id, { active: true });
    return { message: `Opened ${urls.length} website${urls.length === 1 ? "" : "s"}.` };
  }

  if (action === "search") {
    const query = String(command.query || "").trim();
    if (!query) throw new Error("What should I search for?");
    await chrome.tabs.create({
      url: `https://www.google.com/search?q=${encodeURIComponent(query)}`
    });
    return { message: `Searching Google for ${query}.` };
  }

  if (action === "close_tab") {
    const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    if (!tab?.id) throw new Error("I couldn't find the active tab.");
    await chrome.tabs.remove(tab.id);
    return { message: "Closed the current tab." };
  }

  if (action === "next_tab" || action === "previous_tab") {
    const tabs = await chrome.tabs.query({ currentWindow: true });
    if (tabs.length < 2) throw new Error("There isn't another tab to switch to.");
    const activeIndex = Math.max(0, tabs.findIndex(tab => tab.active));
    const delta = action === "next_tab" ? 1 : -1;
    const nextIndex = (activeIndex + delta + tabs.length) % tabs.length;
    await chrome.tabs.update(tabs[nextIndex].id, { active: true });
    return { message: action === "next_tab" ? "Switched to the next tab." : "Switched to the previous tab." };
  }

  throw new Error("That action isn't supported yet.");
}

async function interpretWithGemini(text, apiKey) {
  const permitted = await chrome.permissions.contains({
    origins: ["https://generativelanguage.googleapis.com/*"]
  });
  if (!permitted) throw new Error("Enable the optional Gemini connection in Settings first.");

  const prompt = `Convert the user's browser request into exactly one JSON object.
Allowed schemas:
{"action":"open_sites","sites":["github","chatgpt","youtube","gmail","google","drive","docs","calendar","linkedin","twitter","stackoverflow","vercel","portfolio"]}
{"action":"search","query":"search terms"}
{"action":"close_tab"}
{"action":"next_tab"}
{"action":"previous_tab"}
Only use supported site names. Never invent URLs. If unsupported, return {"action":"unsupported"}.
User request: ${JSON.stringify(text)}
Return JSON only.`;

  const response = await fetch(
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + encodeURIComponent(apiKey),
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { temperature: 0.1, responseMimeType: "application/json" }
      })
    }
  );
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Gemini request failed (${response.status}). ${detail.slice(0, 180)}`);
  }
  const data = await response.json();
  const raw = data?.candidates?.[0]?.content?.parts?.[0]?.text || "";
  let parsed;
  try { parsed = JSON.parse(raw); } catch { throw new Error("Gemini returned an invalid command."); }
  if (!parsed || typeof parsed !== "object") throw new Error("Gemini returned an invalid command.");
  return parsed;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    try {
      if (message?.type === "EXECUTE_COMMAND") {
        const result = await executeCommand(message.command);
        sendResponse({ ok: true, ...result });
        return;
      }
      if (message?.type === "AI_INTERPRET") {
        const command = await interpretWithGemini(message.text, message.apiKey);
        sendResponse({ ok: true, command });
        return;
      }
      sendResponse({ ok: false, error: "Unknown request." });
    } catch (error) {
      sendResponse({ ok: false, error: error.message || "Something went wrong." });
    }
  })();
  return true;
});