// Fast, predictable command parser. No network/API key required.
const SITE_ALIASES = [
  ["github", ["github", "git hub"]],
  ["chatgpt", ["chatgpt", "chat gpt", "chat g p t"]],
  ["youtube", ["youtube", "you tube"]],
  ["gmail", ["gmail", "g mail"]],
  ["google", ["google"]],
  ["drive", ["google drive", "drive"]],
  ["docs", ["google docs", "docs"]],
  ["calendar", ["google calendar", "calendar"]],
  ["linkedin", ["linkedin", "linked in"]],
  ["twitter", ["twitter", "x"]],
  ["stackoverflow", ["stackoverflow", "stack overflow"]],
  ["vercel", ["vercel"]],
  ["portfolio", ["my portfolio", "portfolio"]]
];

function cleanSpeech(value) {
  return String(value || "").toLowerCase().trim().replace(/[.,!?]+$/g, "");
}

function parseLocalCommand(input) {
  const text = cleanSpeech(input);
  if (!text) return null;

  if (/\b(close|remove)\s+(the\s+)?(current\s+)?tab\b/.test(text)) {
    return { action: "close_tab" };
  }
  if (/\b(next|switch to next)\s+tab\b/.test(text) || text === "next tab") {
    return { action: "next_tab" };
  }
  if (/\b(previous|last|switch to previous)\s+tab\b/.test(text) || text === "previous tab") {
    return { action: "previous_tab" };
  }

  const searchMatch = text.match(/^(?:search(?: google)? for|google search for|search)\s+(.+)$/);
  if (searchMatch) return { action: "search", query: searchMatch[1].trim() };

  // "open X and Y", "open tabs X, Y and Z", and "launch X".
  const openMatch = text.match(/^(?:please\s+)?(?:open|launch|go to|visit)\s+(?:tabs?\s+)?(.+)$/);
  if (openMatch) {
    const requested = openMatch[1]
      .replace(/\band\b/g, ",")
      .split(",")
      .map(part => part.trim().replace(/^(the|website)\s+/i, ""))
      .filter(Boolean);

    const found = [];
    for (const phrase of requested) {
      const match = SITE_ALIASES.find(([, aliases]) =>
        aliases.some(alias => phrase === alias || phrase.includes(alias))
      );
      if (match && !found.includes(match[0])) found.push(match[0]);
    }
    if (found.length) return { action: "open_sites", sites: found };
  }

  return null;
}