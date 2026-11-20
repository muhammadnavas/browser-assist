// Fast, predictable command parser. No network/API key required.
const SITE_ALIASES = [
  ["github", ["github", "git hub"]],
  ["chatgpt", ["chatgpt", "chat gpt", "chat g p t"]],
  ["youtube", ["youtube", "you tube"]],
  ["gmail", ["gmail", "g mail"]],
  ["drive", ["google drive", "drive"]],
  ["docs", ["google docs", "docs"]],
  ["calendar", ["google calendar", "calendar"]],
  ["google", ["google"]],
  ["linkedin", ["linkedin", "linked in"]],
  ["twitter", ["twitter", "x"]],
  ["stackoverflow", ["stackoverflow", "stack overflow"]],
  ["vercel", ["vercel"]],
  ["portfolio", ["my portfolio", "portfolio"]]
];

function normalizeSpeech(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[’']/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

function containsPhrase(text, phrase) {
  // Match whole words/phrases so the alias "x" cannot match unrelated words.
  return (` ${text} `).includes(` ${phrase} `);
}

function findSite(phrase) {
  const normalized = normalizeSpeech(phrase)
    .replace(/^(?:the|website|site|app)\s+/, "")
    .replace(/\s+(?:website|site|app)$/, "");

  // Prefer the most specific alias: "google drive" before "google".
  const aliases = SITE_ALIASES
    .flatMap(([site, names]) => names.map(name => ({ site, name: normalizeSpeech(name) })))
    .sort((a, b) => b.name.length - a.name.length);

  const match = aliases.find(({ name }) => containsPhrase(normalized, name));
  return match?.site || null;
}

function parseLocalCommand(input) {
  const text = normalizeSpeech(input);
  if (!text) return null;

  if (/\b(close|remove)\s+(the\s+)?(current\s+)?tab\b/.test(text)) {
    return { action: "close_tab" };
  }
  if (/\b(next|switch to next)\s+tab\b/.test(text)) {
    return { action: "next_tab" };
  }
  if (/\b(previous|last|switch to previous)\s+tab\b/.test(text)) {
    return { action: "previous_tab" };
  }

  const searchMatch = text.match(/^(?:please\s+)?(?:search(?: google)? for|google search for|search)\s+(.+)$/);
  if (searchMatch) return { action: "search", query: searchMatch[1].trim() };

  // Supports: "open X and Y", "open tabs X, Y and Z", "go to X", etc.
  const openMatch = text.match(/^(?:please\s+)?(?:open|launch|go to|visit)\s+(?:tabs?\s+)?(.+)$/);
  if (openMatch) {
    const requested = openMatch[1]
      .replace(/\band\b/g, ",")
      .split(",")
      .map(part => part.trim())
      .filter(Boolean);

    const found = [];
    for (const phrase of requested) {
      const site = findSite(phrase);
      if (site && !found.includes(site)) found.push(site);
    }

    if (found.length) return { action: "open_sites", sites: found };
  }

  return null;
}
