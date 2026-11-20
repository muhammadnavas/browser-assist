"""Always-on, offline voice command listener for Windows."""
import json
import logging
import os
import queue
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

import sounddevice as sd
from vosk import Model, KaldiRecognizer

from commands import SITES, parse_command

APP_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "BrowserAssist"
LOG_FILE = APP_DIR / "assistant.log"
MODEL_DIR = Path(__file__).resolve().parent / "models" / "vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000
AUDIO_QUEUE = queue.Queue()
LAST_COMMAND = ""
LAST_COMMAND_AT = 0.0
COMMAND_COOLDOWN_SECONDS = 3.0

APP_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(LOG_FILE), level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

def find_chrome():
    candidates = [
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None

def open_chrome(url):
    chrome = find_chrome()
    if chrome:
        subprocess.Popen([chrome, "--new-tab", url],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        logging.warning("Chrome executable not found; using default browser.")
        webbrowser.open_new_tab(url)

def chrome_is_foreground():
    try:
        import pygetwindow
        title = pygetwindow.getActiveWindowTitle() or ""
        return "chrome" in title.lower()
    except Exception:
        return False

def execute(command):
    action = command["action"]
    if action == "open_sites":
        sites = command.get("sites", [])
        for site in sites[:8]:
            url = SITES.get(site)
            if url:
                open_chrome(url)
                time.sleep(0.25)
        logging.info("Opened sites: %s", ", ".join(sites))
        return
    if action == "search":
        query = command.get("query", "").strip()
        if query:
            open_chrome("https://www.google.com/search?q=" + quote_plus(query))
            logging.info("Google search: %s", query)
        return
    if action in ("close_tab", "next_tab", "previous_tab"):
        if not chrome_is_foreground():
            logging.info("Ignored tab shortcut because Chrome is not foreground.")
            return
        import pyautogui
        shortcuts = {
            "close_tab": ("ctrl", "w"),
            "next_tab": ("ctrl", "tab"),
            "previous_tab": ("ctrl", "shift", "tab"),
        }
        pyautogui.hotkey(*shortcuts[action])
        logging.info("Executed Chrome shortcut: %s", action)

def audio_callback(indata, frames, callback_time, status):
    if status:
        logging.debug("Audio input status: %s", status)
    AUDIO_QUEUE.put(bytes(indata))

def main():
    if sys.platform != "win32":
        raise RuntimeError("This assistant is designed for Windows 10/11.")
    if not MODEL_DIR.is_dir():
        raise FileNotFoundError(f"Speech model not found: {MODEL_DIR}. Run setup_windows.ps1 first.")

    logging.info("Starting continuous voice assistant.")
    model = Model(str(MODEL_DIR))
    recognizer = KaldiRecognizer(model, SAMPLE_RATE)
    recognizer.SetWords(False)
    print("Browser Assist is listening continuously. Press Ctrl+C to stop.")

    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000, dtype="int16",
                           channels=1, callback=audio_callback):
        while True:
            audio = AUDIO_QUEUE.get()
            if not recognizer.AcceptWaveform(audio):
                continue
            transcript = (json.loads(recognizer.Result()).get("text") or "").strip()
            if not transcript:
                continue
            command = parse_command(transcript)
            if not command:
                continue

            global LAST_COMMAND, LAST_COMMAND_AT
            signature = json.dumps(command, sort_keys=True)
            now = time.monotonic()
            if signature == LAST_COMMAND and now - LAST_COMMAND_AT < COMMAND_COOLDOWN_SECONDS:
                continue
            LAST_COMMAND, LAST_COMMAND_AT = signature, now
            try:
                execute(command)
            except Exception:
                logging.exception("Command execution failed: %s", command)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Assistant stopped by keyboard interrupt.")
    except Exception:
        logging.exception("Assistant exited unexpectedly.")
        raise
