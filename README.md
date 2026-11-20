# Voice Browser Assistant

Voice-controlled browser automation with two ways to run it:

1. **Windows background assistant (recommended):** starts when you sign in to Windows, continuously listens without a wake word, and opens websites directly in Chrome. No extension panel or button is needed.
2. **Chrome extension:** an optional side-panel version for users who prefer to start voice control from Chrome.

The Windows listener uses offline Vosk speech recognition. Audio is processed locally; recognised commands are matched against a fixed local allowlist.

## Windows background assistant (recommended)

### What it does

- Starts automatically when you sign in to Windows.
- Continuously listens through your selected microphone.
- No wake word and no manual start button.
- Say **"Open ChatGPT"**, **"Open GitHub and YouTube"**, or **"Search Python async tutorial"**.
- Opens URLs in Google Chrome directly.
- Supports close-tab and next/previous-tab commands when Chrome is the foreground window.
- Uses offline speech recognition; no speech API key or hosted backend is required.

### Requirements

- Windows 10 or Windows 11.
- Python 3.11 (64-bit) with the Python Launcher (py).
- Google Chrome installed.
- A working microphone and permission for desktop apps to use it.
- Internet access for the one-time Vosk model download and for opening websites.

### Install

1. Download or clone this repository to a permanent folder. Do not move the folder after setup.
2. Install Python 3.11 from https://www.python.org/downloads/release/python-3119/. Enable the Python Launcher during installation.
3. Open PowerShell in the windows_assistant folder.
4. Run:

   ~~~powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\setup_windows.ps1
   ~~~

5. The setup script creates a virtual environment, installs dependencies, downloads the small English Vosk model, and adds a shortcut to your Windows Startup folder.
6. Sign out and sign in again, or start it immediately with:

   ~~~powershell
   .\.venv\Scripts\python.exe .\assistant.py
   ~~~

   This foreground command is useful for the first microphone test. Normal startup uses pythonw.exe and does not open a console window.

### Voice commands

- "Open ChatGPT"
- "Open GitHub"
- "Open GitHub and YouTube"
- "Open Gmail, Calendar and Drive"
- "Search Python async tutorial"
- "Close current tab"
- "Switch to next tab"
- "Switch to previous tab"

Website destinations are defined in windows_assistant/commands.py. Update the SITES mapping to customise them.

### Stop or remove startup

Run this from PowerShell:

~~~powershell
.\stop_assistant.ps1
~~~

It stops the assistant process and removes its Windows Startup shortcut. It does not uninstall Python packages or delete the downloaded speech model.

### Logs and troubleshooting

- Log file: %LOCALAPPDATA%\BrowserAssist\assistant.log
- If the microphone is not detected, check Windows Settings → Privacy & security → Microphone and allow desktop apps to access it.
- If no commands are recognised, test in a quiet environment and speak a complete command in English.
- The first launch can take a little longer while the speech model loads.
- The assistant only executes recognised commands. It does not transmit microphone audio to a speech-recognition server.
- Tab shortcuts are ignored unless Chrome is the active foreground application, preventing them from closing or switching tabs in another app.

## Chrome extension (optional)

The Manifest V3 extension provides a side panel with voice recognition, local command parsing, and optional Gemini interpretation.

### Install locally

1. Open chrome://extensions in Chrome.
2. Turn on Developer mode.
3. Click Load unpacked and select the repository folder.
4. Open the extension side panel and grant microphone permission.

The extension is independent of the Windows background listener. You do not need to open the extension panel when using the Windows assistant.

### Optional Gemini setup

The extension can optionally use Gemini for flexible command interpretation. Create an API key in Google AI Studio, enable the optional host permission in the side panel, and save the key in extension storage. Do not commit API keys to Git or share a folder containing a saved key.

## Project structure

~~~text
browser-assist/
├── manifest.json
├── background.js
├── commands.js
├── sidepanel.html
├── sidepanel.css
├── sidepanel.js
├── permission.html
├── permission.js
├── windows_assistant/
│   ├── assistant.py
│   ├── commands.py
│   ├── requirements.txt
│   ├── setup_windows.ps1
│   └── stop_assistant.ps1
└── icons/
~~~

## Privacy and limitations

- The Windows assistant continuously accesses the microphone while it is running. Use the stop script or disable its Startup shortcut whenever you do not want it listening.
- Vosk performs speech recognition locally using the downloaded model. The assistant logs recognised text and command execution details locally; it does not save raw microphone audio.
- Commands are limited to the built-in site allowlist and supported browser actions.
- English recognition is configured by the included small English model. Other languages require a compatible Vosk model and configuration changes.
- This is a local desktop application. It does not require Vercel, Render, or paid hosting.
