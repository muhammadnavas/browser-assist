"""Local command parser shared by the Windows background assistant."""
import re
import unicodedata

SITES = {
    "github": "https://github.com/",
    "chatgpt": "https://chatgpt.com/",
    "openai": "https://openai.com/",
    "youtube": "https://www.youtube.com/",
    "gmail": "https://mail.google.com/",
    "google": "https://www.google.com/",
    "keep": "https://keep.google.com/",
    "drive": "https://drive.google.com/",
    "docs": "https://docs.google.com/",
    "calendar": "https://calendar.google.com/",
    "linkedin": "https://www.linkedin.com/",
    "twitter": "https://x.com/",
    "whatsapp": "https://web.whatsapp.com/",
    "stackoverflow": "https://stackoverflow.com/",
    "vercel": "https://vercel.com/",
    "render": "https://dashboard.render.com/",
    "word": "https://www.microsoft365.com/launch/word",
    "portfolio": "https://navas.vercel.app/",
}

# Keep product-specific aliases before generic brand aliases. The parser below
# resolves each spoken target as a complete phrase, not a substring.
ALIASES = [
    ("stackoverflow", ("stack overflow", "stackoverflow")),
    ("calendar", ("google calendar", "calendar")),
    ("chatgpt", ("chat g p t", "chat gpt", "chatgpt")),
    ("linkedin", ("linked in", "linkedin")),
    ("youtube", ("you tube", "youtube")),
    ("github", ("git hub", "github")),
    ("keep", ("google keep", "keep")),
    ("drive", ("google drive", "drive")),
    ("docs", ("google docs", "docs")),
    ("gmail", ("g mail", "gmail")),
    ("whatsapp", ("whats app", "whatsapp")),
    ("twitter", ("twitter", "x")),
    ("portfolio", ("my portfolio", "portfolio")),
    ("vercel", ("vercel",)),
    ("render", ("render",)),
    ("word", ("microsoft word", "ms word", "word")),
    ("google", ("google",)),
    ("openai", ("open ai", "openai")),
]

def normalize(text):
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()

def _resolve_site(segment):
    """Resolve one complete spoken app name; never match a generic substring."""
    segment = re.sub(r"^(?:the|my)\\s+", "", segment.strip())
    matches = []
    for site, aliases in ALIASES:
        for alias in aliases:
            if segment == normalize(alias):
                matches.append((len(alias.split()), len(alias), site))
    if not matches:
        return None
    # Prefer the most specific alias if two aliases normalize to the same phrase.
    return max(matches)[2]

def parse_command(transcript):
    text = normalize(transcript)
    if not text:
        return None
    if re.search(r"\\b(close|remove)\\s+(the\\s+)?(current\\s+)?tab\\b", text):
        return {"action": "close_tab"}
    if re.search(r"\\b(next|switch to next)\\s+tab\\b", text):
        return {"action": "next_tab"}
    if re.search(r"\\b(previous|last|switch to previous)\\s+tab\\b", text):
        return {"action": "previous_tab"}
    search = re.match(r"^(?:please )?(?:search(?: google)? for|google search for|search)\\s+(.+)$", text)
    if search:
        return {"action": "search", "query": search.group(1).strip()}

    opening = re.match(r"^(?:please )?(?:open|launch|go to|visit)\\s+(?:tabs?\\s+)?(.+)$", text)
    if not opening:
        return None

    # Multiple apps are supported only when the speaker explicitly separates
    # them with "and" / "also". This prevents incidental words from launching tabs.
    target_text = opening.group(1)
    segments = re.split(r"\\s+(?:and|also)\\s+", target_text)
    found = []
    for segment in segments:
        site = _resolve_site(segment)
        if site and site not in found:
            found.append(site)

    if found:
        return {"action": "open_sites", "sites": found[:8]}
    return None
