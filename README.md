# Voice Browser Assistant

A Manifest V3 Chrome extension with a persistent side panel, voice recognition, local command parsing, and optional Gemini interpretation.

## Features

- Open supported websites: GitHub, ChatGPT, YouTube, Gmail, Google Drive, Docs, Calendar, LinkedIn, X/Twitter, Stack Overflow, Vercel, and a configurable portfolio URL.
- Open multiple tabs with one command.
- Search Google by voice.
- Close the current tab.
- Switch to the next or previous tab.
- Optional Gemini API integration for more flexible phrasing.
- Recent activity shown in the side panel (session only).
- No server or paid hosting required.

## Requirements

- Desktop Google Chrome 116 or later.
- Microphone access.
- Internet connection for browser speech recognition in Chrome configurations that use Google's speech service.
- Optional: a Gemini API key for AI interpretation.

## Install locally

1. Download and extract this project.
2. Open `chrome://extensions` in Chrome.
3. Turn on **Developer mode**.
4. Click **Load unpacked**.
5. Select the extracted `voice-browser-assistant` folder.
6. Pin the extension if desired.
7. Click its toolbar icon to open the side panel.
8. Click **Start listening**, allow microphone access, and try: "Open GitHub".

## Commands

- `Open GitHub`
- `Open ChatGPT`
- `Open GitHub and YouTube`
- `Open Gmail, Calendar and Drive`
- `Search Python async tutorial`
- `Close current tab`
- `Switch to next tab`
- `Switch to previous tab`

## Optional Gemini setup

1. Create an API key in Google AI Studio.
2. Expand **AI settings** in the side panel.
3. Click **Enable Gemini access** and approve the optional host permission.
4. Paste your API key and click **Save key**.

The key is stored using `chrome.storage.local` on this browser. AI requests are sent to Google's Gemini API. Do not share the extension folder with your key saved in it, and do not commit API keys to Git.

Local commands work without Gemini. AI output is treated as untrusted input: the background worker only executes a small allowlist of actions and website names.

## Customize your portfolio URL

Edit `ALLOWED_SITES` in `background.js` and replace the `portfolio` URL with your own.

## Project structure

```text
voice-browser-assistant/
├── manifest.json
├── background.js
├── commands.js
├── sidepanel.html
├── sidepanel.css
├── sidepanel.js
├── README.md
└── icons/
    ├── icon16.png
    ├── icon32.png
    ├── icon48.png
    ├── icon128.png
    └── icon.svg
```

## Notes and limitations

- The microphone starts only after you click the button. This extension does not continuously listen in the background.
- Speech recognition availability and accuracy depend on Chrome, OS microphone permissions, language, and network conditions.
- This version is intended for desktop Chrome. Mobile Chrome does not support installing ordinary desktop extensions.
- The `portfolio` URL is a placeholder; update it before using that command.
- This is a local extension; it does not need Vercel, Render, or another hosting provider.
- Publishing to the Chrome Web Store requires a developer account and a one-time registration fee.

## Privacy

No voice recording is stored by this extension. Browser speech recognition may process audio using the browser's speech service. If Gemini is configured, recognized text is sent to Google's Gemini API for interpretation. Review the relevant provider privacy terms before enabling AI.
