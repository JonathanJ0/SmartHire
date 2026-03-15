"""
tts_module.py — Text-to-Speech Python Module

Reads text aloud using available TTS engines.
Supports: pyttsx3 (offline), gTTS (Google, requires internet), and system commands.

Usage:
    python tts_module.py                        # interactive prompt
    python tts_module.py "Hello, world!"        # speak from argument
    echo "Hello" | python tts_module.py         # speak from stdin

    # As a library:
    from tts_module import speak
    speak("Hello, world!")
"""

import sys
import argparse


# ── Engine implementations ────────────────────────────────────────────────────

def speak_pyttsx3(text: str, rate: int = 175, volume: float = 1.0, voice_index: int = 0) -> None:
    """Speak using pyttsx3 (offline, cross-platform)."""
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty("rate", rate)
    engine.setProperty("volume", volume)
    voices = engine.getProperty("voices")
    if voices and voice_index < len(voices):
        engine.setProperty("voice", voices[voice_index].id)
    engine.say(text)
    engine.runAndWait()


def speak_gtts(text: str, lang: str = "en", slow: bool = False) -> None:
    """Speak using gTTS (requires internet + pygame or mpg123/afplay)."""
    import tempfile, os
    from gtts import gTTS

    tts = gTTS(text=text, lang=lang, slow=slow)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name
    tts.save(tmp_path)

    # Try playback via pygame, then system player
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.stop()
        pygame.mixer.quit()
    except ImportError:
        import subprocess, platform
        system = platform.system()
        if system == "Darwin":
            subprocess.run(["afplay", tmp_path], check=True)
        elif system == "Linux":
            subprocess.run(["mpg123", "-q", tmp_path], check=True)
        elif system == "Windows":
            subprocess.run(["start", tmp_path], shell=True, check=True)
        else:
            raise RuntimeError("No audio player found. Install pygame or mpg123.")
    finally:
        os.unlink(tmp_path)


def speak_system(text: str) -> None:
    """Speak using OS built-in tools (macOS: say, Linux: espeak/spd-say, Windows: PowerShell)."""
    import subprocess, platform, shutil

    system = platform.system()
    if system == "Darwin":
        subprocess.run(["say", text], check=True)
    elif system == "Linux":
        if shutil.which("espeak"):
            subprocess.run(["espeak", text], check=True)
        elif shutil.which("spd-say"):
            subprocess.run(["spd-say", text], check=True)
        elif shutil.which("festival"):
            proc = subprocess.Popen(["festival", "--tts"], stdin=subprocess.PIPE)
            proc.communicate(text.encode())
        else:
            raise RuntimeError("No TTS tool found. Install espeak: sudo apt install espeak")
    elif system == "Windows":
        escaped = text.replace("'", "''")
        subprocess.run(
            ["powershell", "-Command", f"Add-Type -AssemblyName System.Speech; "
             f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak('{escaped}')"],
            check=True,
        )
    else:
        raise RuntimeError(f"Unsupported OS: {system}")


# ── Auto-selecting speak() ────────────────────────────────────────────────────

def speak(
    text: str,
    engine: str = "auto",
    rate: int = 175,
    volume: float = 1.0,
    lang: str = "en",
    voice_index: int = 0,
    slow: bool = False,
) -> None:
    """
    Speak the given text aloud.

    Parameters
    ----------
    text        : str   — text to speak
    engine      : str   — 'auto' | 'pyttsx3' | 'gtts' | 'system'
    rate        : int   — words per minute (pyttsx3 only, default 175)
    volume      : float — 0.0–1.0 (pyttsx3 only, default 1.0)
    lang        : str   — BCP-47 language code (gTTS only, default 'en')
    voice_index : int   — voice index (pyttsx3 only, default 0)
    slow        : bool  — slow speech (gTTS only, default False)
    """
    if not text or not text.strip():
        print("[tts] No text to speak.")
        return

    if engine == "auto":
        for try_engine in ("pyttsx3", "system", "gtts"):
            try:
                speak(text, engine=try_engine, rate=rate, volume=volume,
                      lang=lang, voice_index=voice_index, slow=slow)
                return
            except Exception:
                continue
        raise RuntimeError("No TTS engine available. Install pyttsx3: pip install pyttsx3")

    elif engine == "pyttsx3":
        speak_pyttsx3(text, rate=rate, volume=volume, voice_index=voice_index)

    elif engine == "gtts":
        speak_gtts(text, lang=lang, slow=slow)

    elif engine == "system":
        speak_system(text)

    else:
        raise ValueError(f"Unknown engine '{engine}'. Choose: auto, pyttsx3, gtts, system")


def list_voices() -> None:
    """Print available pyttsx3 voices."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        print(f"{'Index':<6} {'ID':<50} Name")
        print("-" * 80)
        for i, v in enumerate(voices):
            print(f"{i:<6} {v.id:<50} {v.name}")
    except ImportError:
        print("pyttsx3 not installed. Run: pip install pyttsx3")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Text-to-Speech module — reads text aloud.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tts_module.py "Hello, world!"
  python tts_module.py --engine gtts --lang fr "Bonjour le monde"
  python tts_module.py --engine pyttsx3 --rate 150 --voice 1 "Slow voice"
  echo "Piped text" | python tts_module.py
  python tts_module.py --list-voices
        """,
    )
    parser.add_argument("text", nargs="?", help="Text to speak (omit to read from stdin)")
    parser.add_argument("--engine", default="auto",
                        choices=["auto", "pyttsx3", "gtts", "system"],
                        help="TTS engine (default: auto)")
    parser.add_argument("--rate", type=int, default=175,
                        help="Speech rate in WPM, pyttsx3 only (default: 175)")
    parser.add_argument("--volume", type=float, default=1.0,
                        help="Volume 0.0–1.0, pyttsx3 only (default: 1.0)")
    parser.add_argument("--lang", default="en",
                        help="Language code, gTTS only (default: en)")
    parser.add_argument("--voice", type=int, default=0, dest="voice_index",
                        help="Voice index, pyttsx3 only (default: 0)")
    parser.add_argument("--slow", action="store_true",
                        help="Slow speech, gTTS only")
    parser.add_argument("--list-voices", action="store_true",
                        help="List available pyttsx3 voices and exit")

    args = parser.parse_args()

    if args.list_voices:
        list_voices()
        return

    # Resolve text: argument → stdin → interactive
    if args.text:
        text = args.text
    elif not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    else:
        print("Enter text to speak (Ctrl+D / Ctrl+Z to finish):")
        text = sys.stdin.read().strip()

    if not text:
        print("No text provided.")
        sys.exit(1)

    print(f'[tts] Speaking ({args.engine}): "{text[:60]}{"…" if len(text) > 60 else ""}"')
    speak(
        text,
        engine=args.engine,
        rate=args.rate,
        volume=args.volume,
        lang=args.lang,
        voice_index=args.voice_index,
        slow=args.slow,
    )


if __name__ == "__main__":
    main()