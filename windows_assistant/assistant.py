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
        "google search for",
        "next one four three", "next one forty three",
        "next one hundred forty three", "next one hundred and forty three",
        "next one forty tree", "next one four tree", "next 143",
        "[unk]",
    })
    return json.dumps(sorted(phrases))


# Vosk may render the spoken digits as words rather than numerals.
WAKE_VARIANTS = {
    "143",
    "one four three",
    "one four tree",
    "one forty three",
    "one forty tree",
    "one hundred forty three",
    "one hundred and forty three",
}


def build_wake_grammar():
    """Recognize only the wake phrase while the assistant is in standby."""
    return json.dumps(sorted(WAKE_VARIANTS | {"[unk]"}))


def is_wake_phrase(transcript):
    return " ".join((transcript or "").lower().split()) in WAKE_VARIANTS


def is_close_wake_phrase(transcript):
    normalized = " ".join((transcript or "").lower().split())
    if not normalized.startswith("next "):
        return False
    return normalized[5:] in WAKE_VARIANTS

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

def acquire_single_instance():
    """Prevent multiple assistant processes from competing for the microphone."""
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    ctypes.set_last_error(0)
    handle = kernel32.CreateMutexW(None, False, "Local\\BrowserAssistVoiceAssistant")
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        logging.warning("Another Browser Assist instance is already running; exiting.")
        return None
    return handle


def main():
    if sys.platform != "win32":
        raise RuntimeError("This assistant is designed for Windows 10/11.")
    if not MODEL_DIR.is_dir():
        raise FileNotFoundError(f"Speech model not found: {MODEL_DIR}. Run setup_windows.ps1 first.")

    mutex_handle = acquire_single_instance()
    if mutex_handle is None:
        return

    logging.info("Starting Browser Assist in 143 standby mode.")
    model = Model(str(MODEL_DIR))

    # Standby uses one small, constrained recognizer. The active recognizers are
    # created only after the wake phrase is heard.
    wake_recognizer = KaldiRecognizer(model, SAMPLE_RATE, build_wake_grammar())
    wake_recognizer.SetWords(False)
    active = False
    command_recognizer = None
    general_recognizer = None

    print('Browser Assist is in standby. Say "143" to activate; say "next 143" to deactivate.')

    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000, dtype="int16",
                           channels=1, callback=audio_callback):
        while True:
            audio = AUDIO_QUEUE.get()

            if not active:
                if wake_recognizer.AcceptWaveform(audio):
                    transcript = (
                        json.loads(wake_recognizer.Result()).get("text") or ""
                    ).strip()
                    if transcript:
                        logging.info("RECOGNIZED [standby]: %s", transcript)
                    if is_wake_phrase(transcript):
                        active = True
                        command_recognizer = KaldiRecognizer(
                            model, SAMPLE_RATE, build_command_grammar()
                        )
                        general_recognizer = KaldiRecognizer(model, SAMPLE_RATE)
                        command_recognizer.SetWords(False)
                        general_recognizer.SetWords(False)
                        wake_recognizer = None
                        while not AUDIO_QUEUE.empty():
                            try:
                                AUDIO_QUEUE.get_nowait()
                            except queue.Empty:
                                break
                        logging.info('Wake phrase "143" detected; Browser Assist activated.')
                        print("Browser Assist active.")
                continue

            command = None
            grammar_command = None
            general_command = None
            command_transcript = ""
            general_transcript = ""

            if command_recognizer.AcceptWaveform(audio):
                command_transcript = (
                    json.loads(command_recognizer.Result()).get("text") or ""
                ).strip()
                if command_transcript:
                    logging.info("RECOGNIZED [command-grammar]: %s", command_transcript)
                    grammar_command = parse_command(command_transcript)

            if general_recognizer.AcceptWaveform(audio):
                general_transcript = (
                    json.loads(general_recognizer.Result()).get("text") or ""
                ).strip()
                if general_transcript:
                    logging.info("RECOGNIZED [general]: %s", general_transcript)
                    general_command = parse_command(general_transcript)

            # "next 143" returns to standby before the normal command parser runs.
            if is_close_wake_phrase(command_transcript) or is_close_wake_phrase(general_transcript):
                active = False
                command_recognizer = None
                general_recognizer = None
                wake_recognizer = KaldiRecognizer(
                    model, SAMPLE_RATE, build_wake_grammar()
                )
                wake_recognizer.SetWords(False)
                while not AUDIO_QUEUE.empty():
                    try:
                        AUDIO_QUEUE.get_nowait()
                    except queue.Empty:
                        break
                logging.info('Close phrase "next 143" detected; Browser Assist returned to standby.')
                print("Browser Assist in standby.")
                continue

            # Prefer the constrained grammar, with unrestricted recognition as
            # a fallback for free-form Google searches.
            command = grammar_command or general_command

            # Reject conflicting website names heard by the two recognizers.
            if (
                grammar_command
                and general_command
                and grammar_command.get("action") == "open_sites"
                and general_command.get("action") == "open_sites"
                and grammar_command.get("sites") != general_command.get("sites")
            ):
                logging.warning(
                    "IGNORED conflicting website commands; grammar heard=%r (%s), "
                    "general heard=%r (%s)",
                    command_transcript, grammar_command.get("sites", []),
                    general_transcript, general_command.get("sites", [])
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
