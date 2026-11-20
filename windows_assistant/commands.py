"""Local command parser shared by the Windows background assistant."""
import re
import unicodedata

SITES = {
    # Core Google services
    "google": "https://www.google.com/",
    "gmail": "https://mail.google.com/",
    "youtube": "https://www.youtube.com/",
    "drive": "https://drive.google.com/",
    "docs": "https://docs.google.com/",
    "sheets": "https://sheets.google.com/",
    "slides": "https://slides.google.com/",
    "calendar": "https://calendar.google.com/",
    "keep": "https://keep.google.com/",
    "meet": "https://meet.google.com/",
    "photos": "https://photos.google.com/",
    "cloud_console": "https://console.cloud.google.com/",
    "firebase": "https://console.firebase.google.com/",
    # Development and deployment
    "github": "https://github.com/",
    "gitlab": "https://gitlab.com/",
    "bitbucket": "https://bitbucket.org/",
    "stackoverflow": "https://stackoverflow.com/",
    "leetcode": "https://leetcode.com/",
    "vercel": "https://vercel.com/",
    "render": "https://dashboard.render.com/",
    "netlify": "https://app.netlify.com/",
    "railway": "https://railway.app/",
    "replit": "https://replit.com/",
    "codepen": "https://codepen.io/",
    "npm": "https://www.npmjs.com/",
    "docker": "https://hub.docker.com/",
    "postman": "https://www.postman.com/",
    "figma": "https://www.figma.com/",
    "cloudflare": "https://dash.cloudflare.com/",
    "digitalocean": "https://cloud.digitalocean.com/",
    "supabase": "https://supabase.com/dashboard",
    "mongodb": "https://cloud.mongodb.com/",
    "neon": "https://console.neon.tech/",
    # Cloud providers
    "aws": "https://console.aws.amazon.com/",
    "azure": "https://portal.azure.com/",
    # AI tools
    "chatgpt": "https://chatgpt.com/",
    "openai": "https://openai.com/",
    "claude": "https://claude.ai/",
    "gemini": "https://gemini.google.com/",
    "perplexity": "https://www.perplexity.ai/",
    "huggingface": "https://huggingface.co/",
    "groq": "https://console.groq.com/",
    "openrouter": "https://openrouter.ai/",
    # Communication and productivity
    "linkedin": "https://www.linkedin.com/",
    "whatsapp": "https://web.whatsapp.com/",
    "slack": "https://slack.com/",
    "discord": "https://discord.com/app",
    "telegram": "https://web.telegram.org/",
    "twitter": "https://x.com/",
    "notion": "https://www.notion.so/",
    "trello": "https://trello.com/",
    "jira": "https://www.atlassian.com/software/jira",
    "outlook": "https://outlook.live.com/",
    "onedrive": "https://onedrive.live.com/",
    "teams": "https://teams.microsoft.com/",
    "word": "https://www.microsoft365.com/launch/word",
    "excel": "https://www.microsoft365.com/launch/excel",
    "powerpoint": "https://www.microsoft365.com/launch/powerpoint",
    # Personal
    "portfolio": "https://navas.vercel.app/",
}

# Keep aliases specific and phrase-based. Add common pronunciation variants only
# when they map unambiguously to one product.
ALIASES = [
    ("cloud_console", ("google cloud console", "gcp console", "google cloud", "cloud console")),
    ("firebase", ("firebase console", "firebase")),
    ("stackoverflow", ("stack overflow", "stackoverflow")),
    ("calendar", ("google calendar", "calendar")),
    ("chatgpt", ("chat g p t", "chat gpt", "chatgpt")),
    ("linkedin", ("linkedin",)),
    ("leetcode", ("leet code", "leetcode", "lead code")),
    ("youtube", ("you tube", "youtube")),
    ("github", ("git hub", "github")),
    ("keep", ("google keep", "keep")),
    ("drive", ("google drive", "drive")),
    ("docs", ("google docs", "docs")),
    ("sheets", ("google sheets", "sheets", "spreadsheet")),
    ("slides", ("google slides", "slides")),
    ("meet", ("google meet", "meet")),
    ("photos", ("google photos", "photos")),
    ("gmail", ("g mail", "gmail")),
    ("whatsapp", ("whats app", "whatsapp")),
    ("twitter", ("twitter", "x")),
    ("portfolio", ("my portfolio", "portfolio")),
    # "vessel" is a common local-accent rendering of Vercel.
    ("vercel", ("vercel", "ver cell", "vessel")),
    ("render", ("render",)),
    ("netlify", ("netlify", "net lift")),
    ("railway", ("railway", "rail way")),
    ("replit", ("replit", "replit")),
    ("codepen", ("code pen", "codepen")),
    ("npm", ("npm", "node package manager")),
    ("docker", ("docker", "docker hub")),
    ("postman", ("postman",)),
    ("figma", ("figma",)),
    ("cloudflare", ("cloudflare", "cloud flare")),
    ("digitalocean", ("digital ocean", "digitalocean")),
    ("supabase", ("supabase", "supabase dashboard")),
    ("mongodb", ("mongo db", "mongodb", "mongodb atlas")),
    ("neon", ("neon", "neon database")),
    ("aws", ("aws console", "amazon web services", "aws")),
    ("azure", ("azure portal", "microsoft azure", "azure")),
    ("claude", ("claude", "claude ai")),
    ("gemini", ("google gemini", "gemini")),
    ("perplexity", ("perplexity",)),
    ("huggingface", ("hugging face", "huggingface")),
    ("groq", ("groq", "groq console")),
    ("openrouter", ("open router", "openrouter")),
    ("slack", ("slack",)),
    ("discord", ("discord",)),
    ("telegram", ("telegram",)),
    ("notion", ("notion",)),
    ("trello", ("trello",)),
    ("jira", ("jira",)),
    ("outlook", ("outlook", "microsoft outlook")),
    ("onedrive", ("one drive", "onedrive")),
    ("teams", ("microsoft teams", "teams")),
    ("word", ("microsoft word", "ms word", "word")),
    ("excel", ("microsoft excel", "excel")),
    ("powerpoint", ("power point", "powerpoint")),
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
            normalized_alias = normalize(alias)
            if segment == normalized_alias:
                matches.append((len(normalized_alias.split()), len(normalized_alias), site))
    if not matches:
        return None
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
