"""
Speech Monitor – Powered by OpenAI Whisper
============================================
High-accuracy real-time speech-to-text with:
  • OpenAI Whisper (local) or faster-whisper for transcription
  • Filler word detection  (um, uh, like, you know, basically, …)
  • Pause detection        (silence gaps > threshold)
  • Words-per-minute tracking
  • Live confidence score
  • Session report + JSON export

Model options (--model flag):
  tiny   – fastest,  ~32MB,  lower accuracy
  base   – fast,     ~74MB,  decent accuracy
  small  – medium,  ~244MB,  good accuracy       ← default
  medium – slower,  ~769MB,  great accuracy
  large  – slowest, ~1550MB, best accuracy

Dependencies:
    pip install faster-whisper sounddevice numpy scipy rich

On macOS:
    brew install portaudio

Usage:
    python speech_monitor.py
    python speech_monitor.py --model medium
    python speech_monitor.py --duration 120 --save
    python speech_monitor.py --language es        # Spanish, fr, de, etc.
"""

import os
import sys
import json
import time
import queue
import threading
import argparse
import re
import tempfile
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

# ── Whisper ────────────────────────────────────────────────────────────────────
try:
    from faster_whisper import WhisperModel
    WHISPER_BACKEND = "faster-whisper"
except ImportError:
    try:
        import whisper as openai_whisper
        WHISPER_BACKEND = "openai-whisper"
    except ImportError:
        sys.exit(
            "No Whisper backend found. Install one:\n"
            "  pip install faster-whisper          (recommended – faster)\n"
            "  pip install openai-whisper           (alternative)"
        )

# ── Audio ──────────────────────────────────────────────────────────────────────
try:
    import sounddevice as sd
    import numpy as np
    from scipy.io import wavfile
except ImportError:
    sys.exit(
        "Audio libraries not found. Install:\n"
        "  pip install sounddevice numpy scipy"
    )

# ── Rich UI ────────────────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.rule import Rule
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    print("[INFO] Install 'rich' for a nicer UI:  pip install rich")

console = Console() if HAS_RICH else None


# ─────────────────────────────────────────────────────────────────────────────
# Constants & Config
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_RATE   = 16000   # Whisper expects 16 kHz
CHUNK_SECONDS = 5       # record this many seconds per chunk
SILENCE_DB    = -40     # dBFS below which = silence

FILLER_WORDS = {
    "um", "uh", "er", "ah", "uhh", "umm", "hmm", "mhm",
    "like", "basically", "literally", "actually", "honestly",
    "you know", "you know what i mean", "i mean",
    "kind of", "sort of", "kinda", "sorta",
    "right", "okay so", "so yeah", "and stuff",
    "at the end of the day", "to be honest",
    "in terms of", "the thing is",
    "and um", "and uh", "so um", "so uh",
    "well um", "well uh",
}

MULTI_WORD_FILLERS  = {p for p in FILLER_WORDS if " " in p}
SINGLE_WORD_FILLERS = {p for p in FILLER_WORDS if " " not in p}

SCORE_WEIGHTS = {
    "filler_rate_penalty":  -3,
    "long_pause_penalty":   -5,
    "medium_pause_penalty": -2,
    "wpm_fast_penalty":     -0.1,
    "wpm_slow_penalty":     -0.1,
    "pause_ratio_penalty":  -30,
}


# ─────────────────────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FillerEvent:
    word:       str
    timestamp:  float
    context:    str
    confidence: float = 1.0

@dataclass
class PauseEvent:
    duration:  float
    timestamp: float
    label:     str   # short | medium | long

@dataclass
class TranscriptChunk:
    text:       str
    timestamp:  float
    word_count: int
    confidence: float

@dataclass
class SessionStats:
    total_words:        int   = 0
    total_fillers:      int   = 0
    total_pauses:       int   = 0
    long_pauses:        int   = 0
    medium_pauses:      int   = 0
    short_pauses:       int   = 0
    total_pause_time:   float = 0.0
    speaking_time:      float = 0.0
    session_duration:   float = 0.0
    avg_confidence:     float = 0.0
    confidence_samples: int   = 0
    filler_breakdown:   dict  = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Whisper Loader
# ─────────────────────────────────────────────────────────────────────────────

def load_whisper_model(model_size: str):
    if WHISPER_BACKEND == "faster-whisper":
        compute = "int8"
        device  = "cpu"
        try:
            import torch
            device  = "cuda" if torch.cuda.is_available() else "cpu"
            compute = "float16" if device == "cuda" else "int8"
        except ImportError:
            pass
        print(f"[Whisper] Loading faster-whisper '{model_size}' on {device} …")
        model = WhisperModel(model_size, device=device, compute_type=compute)
    else:
        print(f"[Whisper] Loading openai-whisper '{model_size}' …")
        model = openai_whisper.load_model(model_size)
    print(f"[Whisper] Model ready  ({WHISPER_BACKEND}).\n")
    return model


# ─────────────────────────────────────────────────────────────────────────────
# Transcription
# ─────────────────────────────────────────────────────────────────────────────

def transcribe_audio(model, audio_np: np.ndarray,
                     language: Optional[str]) -> tuple[str, float]:
    """Returns (text, avg_confidence)."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        audio_int16 = (audio_np * 32767).astype(np.int16)
        wavfile.write(tmp_path, SAMPLE_RATE, audio_int16)

        if WHISPER_BACKEND == "faster-whisper":
            segments, _ = model.transcribe(
                tmp_path,
                language       = language,
                beam_size      = 5,
                vad_filter     = True,
                vad_parameters = {"min_silence_duration_ms": 300},
            )
            texts, confs = [], []
            for seg in segments:
                texts.append(seg.text.strip())
                confs.append(min(1.0, max(0.0, seg.avg_logprob + 1.0)))
            text     = " ".join(texts).strip()
            avg_conf = float(np.mean(confs)) if confs else 0.0
        else:
            opts   = {"language": language} if language else {}
            result = model.transcribe(tmp_path, **opts)
            text   = result["text"].strip()
            segs   = result.get("segments", [])
            avg_conf = (float(np.mean([
                min(1.0, max(0.0, s.get("avg_logprob", -1) + 1))
                for s in segs])) if segs else 0.5)
    finally:
        os.unlink(tmp_path)

    return text, avg_conf


# ─────────────────────────────────────────────────────────────────────────────
# Filler Detection
# ─────────────────────────────────────────────────────────────────────────────

def detect_fillers(text: str) -> list[tuple[str, int]]:
    text_lower   = text.lower()
    found        = []
    used_spans: set[tuple[int,int]] = set()

    for phrase in MULTI_WORD_FILLERS:
        for m in re.finditer(r'\b' + re.escape(phrase) + r'\b', text_lower):
            span = (m.start(), m.end())
            if not any(s[0] < span[1] and span[0] < s[1] for s in used_spans):
                found.append((phrase, m.start()))
                used_spans.add(span)

    for word in SINGLE_WORD_FILLERS:
        for m in re.finditer(r'\b' + re.escape(word) + r'\b', text_lower):
            span = (m.start(), m.end())
            if not any(s[0] < span[1] and span[0] < s[1] for s in used_spans):
                found.append((word, m.start()))
                used_spans.add(span)

    return found


def highlight_fillers(text: str):
    if not HAS_RICH:
        return text
    rt           = Text()
    text_lower   = text.lower()
    filler_spans = []

    for phrase in MULTI_WORD_FILLERS:
        for m in re.finditer(r'\b' + re.escape(phrase) + r'\b', text_lower):
            filler_spans.append((m.start(), m.end()))
    for word in SINGLE_WORD_FILLERS:
        for m in re.finditer(r'\b' + re.escape(word) + r'\b', text_lower):
            if not any(s[0] <= m.start() and m.end() <= s[1] for s in filler_spans):
                filler_spans.append((m.start(), m.end()))

    filler_spans.sort()
    cursor = 0
    for start, end in filler_spans:
        if start > cursor:
            rt.append(text[cursor:start])
        rt.append(text[start:end], style="bold red on default")
        cursor = end
    if cursor < len(text):
        rt.append(text[cursor:])
    return rt


# ─────────────────────────────────────────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────────────────────────────────────────

def calculate_score(stats: SessionStats) -> tuple[int, str, dict]:
    score        = 100.0
    breakdown    = {}
    duration_min = max(stats.session_duration / 60, 0.01)
    speaking_min = max(stats.speaking_time    / 60, 0.01)
    wpm          = round(stats.total_words / speaking_min, 1)

    # Filler penalty
    filler_rate = stats.total_fillers / duration_min
    filler_pen  = filler_rate * abs(SCORE_WEIGHTS["filler_rate_penalty"])
    score      -= filler_pen
    breakdown["filler_penalty"]   = round(-filler_pen, 1)
    breakdown["filler_rate/min"]  = round(filler_rate, 2)

    # Pause penalties
    lp_pen = stats.long_pauses   * abs(SCORE_WEIGHTS["long_pause_penalty"])
    mp_pen = stats.medium_pauses * abs(SCORE_WEIGHTS["medium_pause_penalty"])
    score -= lp_pen + mp_pen
    breakdown["long_pause_penalty"]   = round(-lp_pen, 1)
    breakdown["medium_pause_penalty"] = round(-mp_pen, 1)

    # WPM
    wpm_pen = 0.0
    if wpm > 180:
        wpm_pen = (wpm - 180) * abs(SCORE_WEIGHTS["wpm_fast_penalty"])
    elif wpm < 100 and stats.total_words > 20:
        wpm_pen = (100 - wpm) * abs(SCORE_WEIGHTS["wpm_slow_penalty"])
    score -= wpm_pen
    breakdown["wpm"]         = wpm
    breakdown["wpm_penalty"] = round(-wpm_pen, 1)

    # Pause ratio
    total_time = stats.speaking_time + stats.total_pause_time
    if total_time > 0:
        pause_ratio = stats.total_pause_time / total_time
        if pause_ratio > 0.25:
            pr_pen = (pause_ratio - 0.25) * abs(SCORE_WEIGHTS["pause_ratio_penalty"])
            score -= pr_pen
            breakdown["pause_ratio_penalty"] = round(-pr_pen, 1)
            breakdown["pause_ratio"]         = round(pause_ratio, 2)

    # Whisper confidence bonus/penalty
    if stats.avg_confidence > 0:
        conf_adj = (stats.avg_confidence - 0.7) * 10
        score   += conf_adj
        breakdown["confidence_adjustment"] = round(conf_adj, 1)
        breakdown["avg_confidence"]        = round(stats.avg_confidence, 2)

    score = max(0, min(100, round(score)))
    if   score >= 90: grade = "A  – Excellent"
    elif score >= 80: grade = "B  – Good"
    elif score >= 70: grade = "C  – Fair"
    elif score >= 55: grade = "D  – Needs Work"
    else:             grade = "F  – Poor"

    return score, grade, breakdown


# ─────────────────────────────────────────────────────────────────────────────
# Live Dashboard
# ─────────────────────────────────────────────────────────────────────────────

def build_dashboard(stats: SessionStats, full_text: str,
                    last_filler: str, last_pause: Optional[PauseEvent],
                    elapsed: float, model_name: str):
    score, grade, breakdown = calculate_score(stats)
    score_color = "green" if score >= 80 else ("yellow" if score >= 60 else "red")
    wpm  = breakdown.get("wpm", 0)
    conf = stats.avg_confidence

    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)

    # Stats panel
    st = Table(show_header=False, box=None, padding=(0, 1))
    st.add_column(style="dim", width=24)
    st.add_column(style="white")
    m, s = divmod(int(elapsed), 60)
    st.add_row("⏱  Elapsed",      f"{m:02d}:{s:02d}")
    st.add_row("🤖  Model",        f"[cyan]{model_name} ({WHISPER_BACKEND})[/cyan]")
    st.add_row("📝  Words",        str(stats.total_words))
    st.add_row("🚀  WPM",          str(wpm))
    st.add_row("🎯  Confidence",   f"{conf*100:.1f}%" if conf > 0 else "—")
    st.add_row("🔴  Fillers",      str(stats.total_fillers))
    st.add_row("⏸  Pauses",
               f"{stats.total_pauses}  "
               f"(S {stats.short_pauses} | M {stats.medium_pauses} | L {stats.long_pauses})")
    st.add_row("😮‍💨  Pause time",   f"{stats.total_pause_time:.1f}s")
    st.add_row(f"[{score_color}]🏆  Score[/{score_color}]",
               f"[bold {score_color}]{score}/100  {grade}[/bold {score_color}]")
    if last_filler:
        st.add_row("[red]⚠  Last filler[/red]", f"[bold red]{last_filler}[/bold red]")
    if last_pause:
        c = "red" if last_pause.label == "long" else "yellow"
        st.add_row(f"[{c}]⏸  Last pause[/{c}]",
                   f"[{c}]{last_pause.duration:.1f}s ({last_pause.label})[/{c}]")

    # Filler leaderboard
    ft = Table("Filler", "Count", "Rate/min",
               show_header=True, header_style="bold red", box=None, padding=(0, 1))
    dur_min = max(elapsed / 60, 0.01)
    for word, count in sorted(stats.filler_breakdown.items(), key=lambda x: -x[1])[:8]:
        ft.add_row(f"[red]{word}[/red]", str(count), f"{count/dur_min:.2f}")

    grid.add_row(
        Panel(st, title="[bold cyan]Live Stats[/bold cyan]",   border_style="cyan"),
        Panel(ft if stats.filler_breakdown
              else "[dim]No fillers detected yet[/dim]",
              title="[bold red]Filler Leaderboard[/bold red]", border_style="red"),
    )

    rt = highlight_fillers(full_text[-400:]) if full_text else Text("[dim]Listening…[/dim]")
    outer = Table.grid(expand=True)
    outer.add_column()
    outer.add_row(grid)
    outer.add_row(Panel(rt,
                        title="[bold white]Transcript  (fillers in red)[/bold white]",
                        border_style="white"))
    return outer


# ─────────────────────────────────────────────────────────────────────────────
# Silence Helper
# ─────────────────────────────────────────────────────────────────────────────

def is_silent(audio_np: np.ndarray, threshold_db: float = SILENCE_DB) -> bool:
    rms = np.sqrt(np.mean(audio_np ** 2))
    if rms == 0:
        return True
    return 20 * np.log10(rms) < threshold_db


# ─────────────────────────────────────────────────────────────────────────────
# Speech Monitor
# ─────────────────────────────────────────────────────────────────────────────

class SpeechMonitor:

    def __init__(self, model_size="small", language=None,
                 pause_threshold=1.5, long_pause_threshold=3.0,
                 max_duration=None, save_report=False):

        self.model_size           = model_size
        self.language             = language
        self.pause_threshold      = pause_threshold
        self.long_pause_threshold = long_pause_threshold
        self.max_duration         = max_duration
        self.save_report          = save_report

        self.stats         = SessionStats()
        self.transcript    = []
        self.filler_events = []
        self.pause_events  = []

        self.last_speech_end:  Optional[float] = None
        self.session_start:    Optional[float] = None
        self.running           = False
        self.last_filler       = ""
        self.last_pause_event: Optional[PauseEvent] = None
        self.full_text         = ""
        self.audio_queue: queue.Queue = queue.Queue()

        self.model = load_whisper_model(model_size)

    # ── Pause ──────────────────────────────────────────────────────────────────

    def _record_pause(self, duration: float):
        if duration < self.pause_threshold:
            return
        label = ("long"   if duration >= self.long_pause_threshold else
                 "medium" if duration >= 1.5 else "short")
        evt = PauseEvent(round(duration, 2), time.time() - self.session_start, label)
        self.pause_events.append(evt)
        self.last_pause_event       = evt
        self.stats.total_pauses    += 1
        self.stats.total_pause_time += duration
        if label == "long":    self.stats.long_pauses   += 1
        elif label == "medium": self.stats.medium_pauses += 1
        else:                  self.stats.short_pauses  += 1

    # ── Chunk ──────────────────────────────────────────────────────────────────

    def _process_chunk(self, text: str, chunk_start: float, confidence: float):
        text = text.strip()
        if not text:
            return
        now = time.time()
        if self.last_speech_end is not None:
            self._record_pause(chunk_start - self.last_speech_end)

        words = text.split()
        self.transcript.append(
            TranscriptChunk(text, now - self.session_start, len(words), confidence))
        self.full_text           += " " + text
        self.stats.total_words   += len(words)
        self.stats.speaking_time += CHUNK_SECONDS

        n = self.stats.confidence_samples
        self.stats.avg_confidence    = (self.stats.avg_confidence * n + confidence) / (n + 1)
        self.stats.confidence_samples += 1

        for filler, _ in detect_fillers(text):
            self.filler_events.append(
                FillerEvent(filler, now - self.session_start, text, confidence))
            self.stats.total_fillers += 1
            self.stats.filler_breakdown[filler] = (
                self.stats.filler_breakdown.get(filler, 0) + 1)
            self.last_filler = filler

        self.last_speech_end = now

    # ── Recording thread ───────────────────────────────────────────────────────

    def _recording_thread(self):
        while self.running:
            try:
                audio = sd.rec(int(CHUNK_SECONDS * SAMPLE_RATE),
                               samplerate=SAMPLE_RATE, channels=1, dtype="float32")
                chunk_start = time.time()
                sd.wait()
                audio_np = audio.flatten()
                self.audio_queue.put((None if is_silent(audio_np) else audio_np,
                                      chunk_start))
            except Exception as e:
                if self.running:
                    print(f"[Recording error] {e}")

    # ── Transcription thread ───────────────────────────────────────────────────

    def _transcription_thread(self):
        while self.running:
            try:
                audio_np, chunk_start = self.audio_queue.get(timeout=1)
                if audio_np is None:
                    if self.last_speech_end is not None:
                        self._record_pause(chunk_start - self.last_speech_end)
                    continue
                text, confidence = transcribe_audio(self.model, audio_np, self.language)
                if text:
                    self._process_chunk(text, chunk_start, confidence)
            except queue.Empty:
                continue
            except Exception as e:
                if self.running:
                    print(f"[Transcription error] {e}")

    # ── Run ────────────────────────────────────────────────────────────────────

    def run(self):
        self.running       = True
        self.session_start = time.time()

        threading.Thread(target=self._recording_thread,    daemon=True).start()
        threading.Thread(target=self._transcription_thread, daemon=True).start()

        if HAS_RICH:
            console.print(Panel.fit(
                f"[bold cyan]Speech Monitor[/bold cyan]  –  "
                f"[dim]Whisper {self.model_size} · {WHISPER_BACKEND}[/dim]\n"
                f"[dim]Press Ctrl+C to stop[/dim]",
                border_style="cyan",
            ))
            with Live(console=console, refresh_per_second=2) as live:
                while self.running:
                    elapsed = time.time() - self.session_start
                    self.stats.session_duration = elapsed
                    live.update(build_dashboard(
                        self.stats, self.full_text,
                        self.last_filler, self.last_pause_event,
                        elapsed, self.model_size))
                    if self.max_duration and elapsed >= self.max_duration:
                        self.running = False
                        break
                    time.sleep(0.5)
        else:
            print("Recording… (Ctrl+C to stop)")
            while self.running:
                elapsed = time.time() - self.session_start
                self.stats.session_duration = elapsed
                print(f"\r[{elapsed:.0f}s] Words:{self.stats.total_words}  "
                      f"Fillers:{self.stats.total_fillers}  "
                      f"Pauses:{self.stats.total_pauses}", end="")
                if self.max_duration and elapsed >= self.max_duration:
                    self.running = False
                time.sleep(0.5)

        self.running = False
        self.stats.session_duration = time.time() - self.session_start
        self._final_report()

    # ── Final report ───────────────────────────────────────────────────────────

    def _final_report(self):
        score, grade, breakdown = calculate_score(self.stats)
        score_color = "green" if score >= 80 else ("yellow" if score >= 60 else "red")
        wpm = breakdown.get("wpm", 0)

        if HAS_RICH:
            console.rule("[bold white]SESSION COMPLETE[/bold white]")

            st = Table("Metric", "Value", show_header=True,
                       header_style="bold cyan", box=None, padding=(0,2))
            m, s = divmod(int(self.stats.session_duration), 60)
            st.add_row("Duration",           f"{m:02d}:{s:02d}")
            st.add_row("Model",              f"{self.model_size} ({WHISPER_BACKEND})")
            st.add_row("Total words",        str(self.stats.total_words))
            st.add_row("Words per minute",   str(wpm))
            st.add_row("Avg confidence",     f"{self.stats.avg_confidence*100:.1f}%")
            st.add_row("Total fillers",      str(self.stats.total_fillers))
            st.add_row("  Filler rate",      f"{breakdown.get('filler_rate/min',0)}/min")
            st.add_row("Total pauses",       str(self.stats.total_pauses))
            st.add_row("  Short (< 1.5s)",   str(self.stats.short_pauses))
            st.add_row("  Medium (1.5–3s)",  str(self.stats.medium_pauses))
            st.add_row("  Long (> 3s)",      f"[red]{self.stats.long_pauses}[/red]")
            st.add_row("Total pause time",   f"{self.stats.total_pause_time:.1f}s")
            st.add_row(f"[{score_color}]FINAL SCORE[/{score_color}]",
                       f"[bold {score_color}]{score}/100  –  {grade}[/bold {score_color}]")
            console.print(Panel(st, title="[bold]Summary[/bold]", border_style="cyan"))

            bd = Table("Component", "Adjustment", show_header=True,
                       header_style="bold", box=None, padding=(0,2))
            for k, v in breakdown.items():
                if k in ("wpm", "filler_rate/min", "avg_confidence", "pause_ratio"):
                    bd.add_row(k.replace("_"," ").title(), str(v))
                else:
                    c = "green" if v >= 0 else "red"
                    bd.add_row(k.replace("_"," ").title(), f"[{c}]{v:+.1f}[/{c}]")
            console.print(Panel(bd, title="[bold]Score Breakdown[/bold]",
                                border_style="yellow"))

            if self.stats.filler_breakdown:
                dur_min = max(self.stats.session_duration / 60, 0.01)
                ft = Table("Filler", "Count", "Rate/min", show_header=True,
                           header_style="bold red", box=None, padding=(0,2))
                for word, count in sorted(self.stats.filler_breakdown.items(),
                                           key=lambda x: -x[1]):
                    ft.add_row(f"[red]{word}[/red]", str(count),
                               f"{count/dur_min:.2f}")
                console.print(Panel(ft, title="[bold red]Filler Breakdown[/bold red]",
                                    border_style="red"))

            console.print(Panel(
                highlight_fillers(self.full_text.strip())
                if self.full_text.strip() else Text("[dim]No speech detected[/dim]"),
                title="[bold]Full Transcript  (fillers in red)[/bold]",
                border_style="white"))
        else:
            print(f"\n\n=== SESSION COMPLETE ===")
            print(f"Score: {score}/100 – {grade}")
            print(f"Words: {self.stats.total_words}  WPM: {wpm}")
            print(f"Confidence: {self.stats.avg_confidence*100:.1f}%")
            print(f"Fillers: {self.stats.total_fillers}  Long pauses: {self.stats.long_pauses}")
            if self.full_text:
                print(f"\nTranscript:\n{self.full_text.strip()}")

        if self.save_report:
            self._save_json(score, grade, breakdown, wpm)

    def _save_json(self, score, grade, breakdown, wpm):
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"speech_report_{ts}.json"
        data = {
            "generated_at":     datetime.now().isoformat(),
            "model":            f"{self.model_size} ({WHISPER_BACKEND})",
            "duration_seconds": round(self.stats.session_duration, 2),
            "score":            score,
            "grade":            grade,
            "score_breakdown":  breakdown,
            "stats": {
                "total_words":         self.stats.total_words,
                "wpm":                 wpm,
                "avg_confidence":      round(self.stats.avg_confidence, 3),
                "filler_rate_per_min": breakdown.get("filler_rate/min", 0),
                "total_fillers":       self.stats.total_fillers,
                "filler_breakdown":    self.stats.filler_breakdown,
                "total_pauses":        self.stats.total_pauses,
                "short_pauses":        self.stats.short_pauses,
                "medium_pauses":       self.stats.medium_pauses,
                "long_pauses":         self.stats.long_pauses,
                "total_pause_time":    round(self.stats.total_pause_time, 2),
            },
            "full_transcript": self.full_text.strip(),
            "filler_events": [
                {"word": e.word, "time": round(e.timestamp, 2),
                 "context": e.context, "confidence": round(e.confidence, 3)}
                for e in self.filler_events
            ],
            "pause_events": [
                {"duration": e.duration, "time": round(e.timestamp, 2),
                 "label": e.label}
                for e in self.pause_events
            ],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        msg = f"\n✅  Report saved → {path}"
        console.print(msg) if HAS_RICH else print(msg)


# ─────────────────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="High-accuracy speech monitor using OpenAI Whisper"
    )
    parser.add_argument("--model", "-m", default="small",
                        choices=["tiny","base","small","medium","large",
                                 "large-v2","large-v3"],
                        help="Whisper model size (default: small)")
    parser.add_argument("--language", "-l", default=None,
                        help="Language code e.g. en, es, fr (auto-detect if omitted)")
    parser.add_argument("--duration", "-d", type=int, default=None,
                        help="Auto-stop after N seconds")
    parser.add_argument("--pause-threshold", "-p", type=float, default=1.5,
                        help="Min silence (s) counted as pause (default: 1.5)")
    parser.add_argument("--long-pause", type=float, default=3.0,
                        help="Silence (s) counted as long pause (default: 3.0)")
    parser.add_argument("--save", "-s", action="store_true",
                        help="Save session report as JSON")
    args = parser.parse_args()

    monitor = SpeechMonitor(
        model_size           = args.model,
        language             = args.language,
        pause_threshold      = args.pause_threshold,
        long_pause_threshold = args.long_pause,
        max_duration         = args.duration,
        save_report          = args.save,
    )

    try:
        monitor.run()
    except KeyboardInterrupt:
        monitor.running = False
        time.sleep(1)
        print("\n[Stopped by user]")


if __name__ == "__main__":
    main()