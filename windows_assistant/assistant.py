"""Always-on, offline voice command listener for Windows."""
import json
import logging
from logging.handlers import RotatingFileHandler
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
AUDIO_QUEUE = queue.Queue(maxsize=100)
LAST_COMMAND = ""
LAST_COMMAND_AT = 0.0
COMMAND_COOLDOWN_SECONDS = 3.0

def build_command_grammar():
    """Build a finite grammar for common browser commands."""
    phrases = set()
    open_verbs = ("open", "please open", "launch", "go to", "visit")
    for aliases in __import__("commands").ALIASES:
        for alias in aliases[1]:
            for verb in open_verbs:
                phrases.add(f"{verb} {alias}")

    phrases.update({
        "close tab", "close the tab", "close current tab", "close the current tab",
        "remove tab", "remove the tab", "remove current tab",
        "next tab", "switch to next tab", "previous tab", "switch to previous tab",
        "last tab", "search", "search for", "search google for",
        "google search for", "[unk]",
    })
    return json.dumps(sorted(phrases))

APP_DIR.mkdir(parents=True, exist_ok=True)
_file_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
)
_file_handler.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)s %(message)s"
))
_root_logger = logging.getLogger()
_root_logger.setLevel(logging.INFO)
_root_logger.addHandler(_file_handler)

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
    try:
        AUDIO_QUEUE.put_nowait(bytes(indata))
    except queue.Full:
        logging.warning("Audio queue full; dropped one audio block.")

def main():
    if sys.platform != "win32":
        raise RuntimeError("This assistant is designed for Windows 10/11.")
    if not MODEL_DIR.is_dir():
        raise FileNotFoundError(f"Speech model not found: {MODEL_DIR}. Run setup_windows.ps1 first.")

    logging.info("Starting continuous voice assistant.")
    model = Model(str(MODEL_DIR))
    # The constrained recognizer improves accuracy for known browser commands.
    # Keep a second unrestricted recognizer so free-form Google searches still work.
    command_recognizer = KaldiRecognizer(model, SAMPLE_RATE, build_command_grammar())
    general_recognizer = KaldiRecognizer(model, SAMPLE_RATE)
    command_recognizer.SetWords(False)
    general_recognizer.SetWords(False)
    print("Browser Assist is listening continuously. Press Ctrl+C to stop.")

    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000, dtype="int16",
                           channels=1, callback=audio_callback):
        while True:
            audio = AUDIO_QUEUE.get()
            command = None
            command_transcript = ""
            general_transcript = ""

            if command_recognizer.AcceptWaveform(audio):
                command_transcript = (
                    json.loads(command_recognizer.Result()).get("text") or ""
                ).strip()
                if command_transcript:
                    logging.info("RECOGNIZED [command-grammar]: %s", command_transcript)
                    command = parse_command(command_transcript)

            if general_recognizer.AcceptWaveform(audio):
                general_transcript = (
                    json.loads(general_recognizer.Result()).get("text") or ""
                ).strip()
                if general_transcript:
                    logging.info("RECOGNIZED [general]: %s", general_transcript)
                    fallback = parse_command(general_transcript)
                    if fallback and (command is None or fallback.get("action") == "search"):
                        command = fallback

            # Prevent likely "vessel" -> "WhatsApp" grammar substitutions.
            if command and "whatsapp" in command.get("sites", []):
                general_words = " ".join(general_transcript.lower().split())
                if not any(phrase in general_words for phrase in ("whatsapp", "whats app")):
                    logging.warning(
                        "IGNORED possible WhatsApp false positive; grammar heard=%r, general heard=%r",
                        command_transcript, general_transcript
                    )
                    command = None

            if not command:
                if command_transcript or general_transcript:
                    logging.info("No browser command executed for this speech.")
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
