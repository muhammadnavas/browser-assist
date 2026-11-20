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
    "drive": "https://drive.google.com/",
    "docs": "https://docs.google.com/",
    "calendar": "https://calendar.google.com/",
    "linkedin": "https://www.linkedin.com/",
    "twitter": "https://x.com/",
    "stackoverflow": "https://stackoverflow.com/",
    "vercel": "https://vercel.com/",
    "portfolio": "https://navas.vercel.app/",
}
ALIASES = [
    ("stackoverflow", ("stack overflow", "stackoverflow")),
    ("calendar", ("google calendar", "calendar")),
    ("chatgpt", ("chat g p t", "chat gpt", "chatgpt")),
    ("linkedin", ("linked in", "linkedin")),
    ("youtube", ("you tube", "youtube")),
    ("github", ("git hub", "github")),
    ("drive", ("google drive", "drive")),
    ("docs", ("google docs", "docs")),
    ("gmail", ("g mail", "gmail")),
    ("twitter", ("twitter", "x")),
    ("portfolio", ("my portfolio", "portfolio")),
    ("vercel", ("vercel",)),
    ("google", ("google",)),
    ("openai", ("open ai", "openai")),
]

def normalize(text):
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()

def parse_command(transcript):
    text = normalize(transcript)
    if not text:
        return None
    if re.search(r"\b(close|remove)\s+(the\s+)?(current\s+)?tab\b", text):
        return {"action": "close_tab"}
    if re.search(r"\b(next|switch to next)\s+tab\b", text):
        return {"action": "next_tab"}
    if re.search(r"\b(previous|last|switch to previous)\s+tab\b", text):
        return {"action": "previous_tab"}
    search = re.match(r"^(?:please )?(?:search(?: google)? for|google search for|search)\s+(.+)$", text)
    if search:
        return {"action": "search", "query": search.group(1).strip()}
    opening = re.match(r"^(?:please )?(?:open|launch|go to|visit)\s+(?:tabs?\s+)?(.+)$", text)
    if not opening:
        return None
    target_text = opening.group(1)
    found = []
    for site, aliases in ALIASES:
        for alias in aliases:
            if re.search(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", target_text):
                if site not in found:
                    found.append(site)
                break
    if found:
        return {"action": "open_sites", "sites": found[:8]}
    return None
