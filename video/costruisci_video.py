#!/usr/bin/env python3
"""Video di submission: 7 slide (PNG 1920x1080) + voce fuori campo + ffmpeg.

    python costruisci_video.py            # anteprima muta, durate stimate dal testo (150 parole/min)
    python costruisci_video.py --voce     # voce con ElevenLabs (serve ELEVENLABS_API_KEY nell'ambiente)

Chiave: variabile ELEVENLABS_API_KEY oppure file video/elevenlabs.key (una riga). Altre variabili, ELEVENLABS_VOICE_ID (default: voce premade «Rachel»),
ELEVENLABS_MODEL (default eleven_multilingual_v2).  La chiave non viene mai scritta su disco né stampata.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

QUI = Path(__file__).resolve().parent
OUT = QUI / "out"
W, H = 1920, 1080
BG, FG, MUTE, ACC, ACC2, BAR = "#0b1220", "#f3f6fb", "#93a1b8", "#ed1c24", "#38bdf8", "#223049"
PAUSA = 0.7  # secondi di respiro dopo ogni frase finale di slide

SLIDE = [
    {"titolo": "Reading industrial time series\nwith one call",
     "righe": ["Wavelet-TSLM on AMD Instinct MI300X", "", "Track: Intelligent Industry", "Team PoliMi · Jacopo D'Abundo"],
     "voce": "Industrial plants record hundreds of thousands of sensor readings every day. Finding the few seconds where "
             "something goes wrong is a needle-in-a-haystack problem. We built a model that reads those recordings "
             "directly, in a single call, and runs on AMD Instinct MI300X."},
    {"titolo": "A language model cannot read\n100,000 numbers",
     "righe": ["Usual workaround: an agent that plots, zooms and calls tools, turn after turn",
               "", "On MetroPT-3 windows the agent needed", "about 7 turns and 5 minutes per window",
               "", "Our model reads the whole window at once: 1 call"],
     "voce": "Language models can't read a hundred thousand numbers. The usual workaround is an agent that plots, zooms and "
             "calls tools, turn after turn. On MetroPT-3 we measured about seven turns and five minutes per window. "
             "Our model reads the whole window at once: one call."},
    {"titolo": "Wavelet-TSLM",
     "righe": ["Haar-wavelet encoder  →  Qwen3.5-4B backbone (LoRA)  →  localization head",
               "", "Output: where the anomaly starts and ends, per channel",
               "Trained only on synthetic anomalies (AnomalyXL benchmark)",
               "Runs under ROCm on a single MI300X"],
     "voce": "The model, Wavelet-TSLM, feeds a Haar-wavelet encoder into a Qwen 3.5 four-billion-parameter backbone, "
             "fine-tuned with LoRA, with a head that outputs where the anomaly starts and ends. It was trained only on "
             "synthetic anomalies from the AnomalyXL benchmark, and it runs under ROCm on an MI300X."},
    {"titolo": "Zero-shot on a real plant: HAI 21.03",
     "righe": ["Industrial control testbed · 50 documented attacks · no training on it",
               "38 windows of 9 hours × 16 channels · one call per window"],
     "grafico": True,
     "voce": "Then we asked the hard question: does it transfer to a real plant, with no training on it? We used HAI "
             "twenty-one point oh three, an industrial control testbed with fifty documented attacks. Thirty-eight windows, "
             "each nine hours and sixteen channels, one call each. The model touched thirty-four of the fifty attacks. "
             "Placing the same intervals at random would touch about seven. And sixty percent of its intervals land on an "
             "attack, against four and a half percent by chance."},
    {"titolo": "What it is not (yet)",
     "righe": ["It also flags windows with no attack: 18 of 18 clean windows",
               "→ not an alarm: a ranking of the most anomalous stretches",
               "", "MetroPT-3 (4 slow air-leak failures): did not transfer",
               "", "Next step: adaptation on labelled industrial data"],
     "voce": "We want to be honest about the limit. The model also flags windows with no attack, so it is not an alarm: "
             "it is a ranking of the most anomalous stretches. On a second dataset, MetroPT-3, with four slow air-leak "
             "failures, it did not transfer. Closing that gap needs adaptation on labelled industrial data."},
    {"titolo": "Built and measured on AMD",
     "righe": ["AMD Developer Cloud · 4 MI300X droplets · under $10 in total",
               "Same checkpoint, no retraining, ROCm / PyTorch", "",
               "A tool that ranks suspicious stretches for an engineer to review", "is what Intelligent Industry needs first"],
     "voce": "Everything ran on the AMD Developer Cloud: four MI300X droplets, under ten dollars in total, with the same "
             "checkpoint and no retraining. A tool that ranks suspicious stretches for an engineer to review is what "
             "Intelligent Industry needs first."},
    {"titolo": "Wavelet-TSLM",
     "righe": ["One call · 9 hours · 16 channels", "on AMD Instinct MI300X", "", "Thank you"],
     "voce": "Wavelet-TSLM: one call, nine hours, sixteen channels, on AMD. Thank you."},
]


def font(px: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for nome in (("segoeuib.ttf" if bold else "segoeui.ttf"), "arial.ttf"):
        try:
            return ImageFont.truetype(nome, px)
        except OSError:
            pass
    return ImageFont.load_default()


PROG = 1.0  # avanzamento dell'animazione delle barre (0..1)


def barre(d: ImageDraw.ImageDraw, y: int, titolo: str, a: tuple[float, str], b: tuple[float, str], massimo: float) -> None:
    d.text((160, y), titolo, font=font(40, True), fill=FG)
    for k, (val, etich, col) in enumerate(((a[0], a[1], ACC), (b[0], b[1], MUTE))):
        yy = y + 80 + k * 90
        lung = int(1300 * val / massimo * PROG)
        d.rounded_rectangle((160, yy, 160 + 1300, yy + 64), 12, fill=BAR)
        d.rounded_rectangle((160, yy, 160 + max(lung, 8), yy + 64), 12, fill=col)
        d.text((160 + 1300 + 30, yy + 6), etich, font=font(40, True), fill=FG)


def disegna(i: int, s: dict, p: Path) -> None:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 24, H), fill=ACC)
    titolo = s["titolo"]
    grande = i in (0, 6)
    d.multiline_text((160, 110 if not grande else 260), titolo, font=font(96 if grande else 72, True), fill=FG, spacing=14)
    y0 = 520 if grande else 300
    if s.get("grafico"):
        y = 260
        for riga in s["righe"]:
            d.text((160, y), riga, font=font(38), fill=MUTE)
            y += 56
        barre(d, 440, "Attacks touched by an interval (out of 50)", (34, "34", ACC), (6.6, "6.6 by chance", MUTE), 50)
        barre(d, 740, "Intervals that land on an attack", (60, "60 %", ACC), (4.5, "4.5 % by chance", MUTE), 100)
    else:
        y = y0
        for riga in s["righe"]:
            col = FG if not riga.startswith("→") else ACC2
            d.text((160, y), riga, font=font(46 if not grande else 52), fill=col)
            y += 74 if riga else 34
    d.text((160, H - 70), "Wavelet-TSLM · AMD Developer Hackathon: ACT III · Intelligent Industry", font=font(28), fill=MUTE)
    d.text((W - 160 - 70, H - 70), f"{i + 1}/{len(SLIDE)}", font=font(28), fill=MUTE)
    im.save(p)


def durata(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(p)],
                       capture_output=True, text=True, check=True)
    return float(json.loads(r.stdout)["format"]["duration"])


def eleven(testo: str, p: Path) -> None:
    chiave = os.environ.get("ELEVENLABS_API_KEY")
    if not chiave and (QUI / "elevenlabs.key").exists():
        chiave = (QUI / "elevenlabs.key").read_text(encoding="utf-8").strip()
    if not chiave:
        raise SystemExit("manca la chiave: mettila nel file video/elevenlabs.key (una riga) oppure in ELEVENLABS_API_KEY")
    voce = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    corpo = json.dumps({"text": testo, "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
                        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}).encode()
    rq = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{voce}?output_format=mp3_44100_128",
                                data=corpo, headers={"xi-api-key": chiave, "Content-Type": "application/json",
                                                     "Accept": "audio/mpeg"})
    try:
        with urllib.request.urlopen(rq, timeout=120) as r:
            p.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"ElevenLabs: HTTP {e.code} {e.read()[:300].decode(errors='replace')}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voce", action="store_true")
    ap.add_argument("--anima", action="store_true", help="dissolvenze e barre animate (con --voce)")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    clip = []
    for i, s in enumerate(SLIDE):
        png = OUT / f"slide{i + 1}.png"
        disegna(i, s, png)
        (OUT / f"slide{i + 1}.txt").write_text(s["voce"] + "\n", encoding="utf-8")
        mp4 = OUT / f"clip{i + 1}.mp4"
        if a.voce:
            mp3 = OUT / f"voce{i + 1}.mp3"
            if not mp3.exists():
                eleven(s["voce"], mp3)
            tot = durata(mp3) + PAUSA
            vf = f"fade=t=in:d=0.4,fade=t=out:st={tot - 0.4:.2f}:d=0.4" if a.anima else "null"
            ingresso = ["-loop", "1", "-framerate", "30", "-i", str(png)]
            if a.anima and i == 3:  # barre che crescono nei primi 2,5 s
                global PROG
                fr = OUT / "frame"
                fr.mkdir(exist_ok=True)
                for k in range(75):
                    PROG = min(1.0, (k + 1) / 75) ** 0.6
                    disegna(i, s, fr / f"f{k:03d}.png")
                PROG = 1.0
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "30", "-i", str(fr / "f%03d.png"), "-c:v", "libx264",
                                "-pix_fmt", "yuv420p", str(OUT / "a4.mp4")], check=True)
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(png), "-t",
                                f"{tot - 2.5:.2f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(OUT / "b4.mp4")], check=True)
                (OUT / "c4.txt").write_text("file 'a4.mp4'\nfile 'b4.mp4'\n", encoding="utf-8")
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(OUT / "c4.txt"), "-c", "copy",
                                str(OUT / "v4.mp4")], check=True)
                ingresso = ["-i", str(OUT / "v4.mp4")]
            cmd = ["ffmpeg", "-y", "-loglevel", "error", *ingresso, "-i", str(mp3), "-vf", vf,
                   "-af", f"apad=pad_dur={PAUSA}", "-t", f"{tot:.2f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                   "-b:a", "192k", "-ar", "44100", "-ac", "2", str(mp4)]
        else:
            tot = len(s["voce"].split()) / 150 * 60 + PAUSA
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(png), "-f", "lavfi", "-i",
                   "anullsrc=r=44100:cl=stereo", "-t", f"{tot:.2f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                   "-shortest", str(mp4)]
        subprocess.run(cmd, check=True)
        clip.append(mp4)
        print(f"slide {i + 1}: {tot:.1f} s")
    lista = OUT / "clip.txt"
    lista.write_text("".join(f"file '{c.name}'\n" for c in clip), encoding="utf-8")
    nome = ("video_animato.mp4" if a.anima else "video_submission.mp4") if a.voce else "anteprima_muta.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy",
                    str(OUT / nome)], check=True)
    print("scritto", OUT / nome, f"({durata(OUT / nome):.0f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
