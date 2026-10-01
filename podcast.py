"""
The Sponsor's Playbook: daily PE lesson -> MP3 -> private podcast feed.

Each run:
  1. Picks the next lesson in the curriculum.
  2. Has Claude write a ~15 minute spoken script.
  3. Renders it to MP3 with the configured TTS provider.
  4. Rebuilds docs/feed.xml (subscribe to it in Apple Podcasts).

Usage:
  python podcast.py                 # produce the next lesson
  python podcast.py --lesson 12     # (re)produce lesson 12
  python podcast.py --script-only   # write the script, skip audio (for testing)
"""

import argparse
import base64
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from email.utils import format_datetime
from pathlib import Path

import requests
from anthropic import Anthropic
from mutagen.mp3 import MP3

from curriculum import COURSE_DESCRIPTION, COURSE_TITLE, LESSONS, TOTAL

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
EP_DIR = DOCS / "episodes"
TX_DIR = DOCS / "transcripts"
STATE_FILE = ROOT / "data" / "episodes.json"

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL") or "claude-sonnet-5-5"
TTS_PROVIDER = (os.getenv("TTS_PROVIDER") or "openai").lower()
TTS_VOICE = os.getenv("TTS_VOICE") or ""
TTS_MODEL = os.getenv("TTS_MODEL") or ""
LISTENER_CONTEXT = os.getenv("LISTENER_CONTEXT") or "Senior operating executive."
SITE_URL = (os.getenv("SITE_URL") or "").rstrip("/").lower()
TARGET_WORDS = int(os.getenv("TARGET_WORDS") or 2100)
CHUNK_CHARS = 3000


# ---------------------------------------------------------------- state

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"episodes": []}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def next_lesson_idx(state):
    done = {e["lesson_idx"] for e in state["episodes"]}
    for lesson in LESSONS:
        if lesson["idx"] not in done:
            return lesson["idx"]
    return None


# ---------------------------------------------------------------- script

def build_prompt(i, state):
    L = LESSONS[i]
    recent = [e for e in state["episodes"] if e["lesson_idx"] < i][-8:]
    if recent:
        covered = "\n".join(
            f"- Lesson {e['lesson_idx'] + 1}: {e['title']}. Takeaways: {' '.join(e.get('takeaways', []))}"
            for e in recent
        )
    else:
        covered = "None. This is the first lesson."
    nxt = LESSONS[i + 1]["title"] if i + 1 < TOTAL else "None. This is the final lesson of the course."

    return f"""You are writing the script for a solo-host, podcast-style audio lesson. It is part of a {TOTAL}-lesson daily course called "{COURSE_TITLE}" that takes an executive from private equity fundamentals to advanced deal and capital structures. The listener works at, or is preparing to lead, a private-equity-backed company, and listens on the morning drive.

Listener context: {LISTENER_CONTEXT}

Today: Lesson {i + 1} of {TOTAL}, "{L['title']}"
Module {L['module_num']}: {L['module']} ({L['level']} level)
Recent lessons already covered:
{covered}
Next lesson: {nxt}

Requirements:
- About {TARGET_WORDS} words, roughly 15 minutes spoken at a relaxed pace.
- Open with exactly: "Welcome to {COURSE_TITLE}. This is lesson {i + 1}: {L['title']}." Then go straight into the content.
- Written for the ear, for someone driving: conversational, short sentences, one host speaking directly to the listener. No markdown, no bullet points, no headings, no stage directions, no sound cues. Write numbers, percentages, and symbols the way a person would say them aloud. Keep worked examples simple enough to follow without seeing numbers on a page.
- Structure: a short cold open built on a concrete scenario; the core concept explained clearly with correct terminology; one worked example with realistic numbers talked through step by step; what this means for an operating executive in a PE-backed company, including how the sponsor, board, and lenders will look at it; two or three common mistakes; a brief recap; end with one question for the listener to think about today, then a one-sentence preview of the next lesson.
- Match depth to the level. Foundational lessons define terms plainly. Intermediate lessons assume the basics and focus on mechanics and trade-offs. Advanced lessons assume prior material and cover structures, negotiation dynamics, and edge cases.
- Refer back to an earlier lesson where it genuinely helps. Use examples from the listener's industry where natural, but keep the principles broadly applicable.
- Be accurate. Where market practice varies by deal size, sector, or credit cycle, say so instead of presenting one number as universal. No disclaimers beyond a single clause if genuinely needed.

Separate paragraphs with a blank line. After the script, write a line containing only ===== and then exactly three key takeaways, one per line, each starting with "- "."""


def write_script(i, state):
    client = Anthropic()
    prompt = build_prompt(i, state)
    for attempt in (1, 2):
        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        body, tail = split_output(text)
        words = len(body.split())
        if words >= TARGET_WORDS * 0.7:
            takeaways = [re.sub(r"^\s*[-*\u2022]\s*", "", t).strip() for t in tail.splitlines() if t.strip()][:3]
            return body, takeaways
        print(f"Script came back short ({words} words), attempt {attempt}.", file=sys.stderr)
    raise RuntimeError("Claude returned a script that was too short twice in a row.")


def split_output(text):
    parts = re.split(r"\n\s*=====\s*\n?", text, maxsplit=1)
    return parts[0].strip(), (parts[1] if len(parts) > 1 else "")


# ---------------------------------------------------------------- audio

def chunk_text(script, limit=CHUNK_CHARS):
    """Split on paragraph, then sentence, boundaries so no chunk exceeds the TTS limit."""
    chunks, cur = [], ""
    for para in [p.strip() for p in re.split(r"\n\s*\n", script) if p.strip()]:
        pieces = [para] if len(para) <= limit else re.findall(r"[^.!?]+[.!?]+[\"')\]]*\s*|[^.!?]+$", para)
        safe = []
        for piece in pieces:
            while len(piece) > limit:
                cut = piece.rfind(" ", 0, limit) or limit
                safe.append(piece[:cut])
                piece = piece[cut:].lstrip()
            safe.append(piece)
        pieces = [para] if len(para) <= limit else safe
        for piece in pieces:
            if cur and len(cur) + len(piece) + 2 > limit:
                chunks.append(cur.strip())
                cur = ""
            cur += piece + ("\n\n" if piece is para else "")
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


HOST_STYLE = (
    "You are an experienced, warm podcast host teaching business executives. "
    "Measured, confident pace. Natural emphasis on key terms and numbers. "
    "Conversational, never salesy. Brief pauses between ideas."
)


def tts_openai(text):
    r = requests.post(
        "https://api.openai.com/v1/audio/speech",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        json={
            "model": TTS_MODEL or "gpt-4o-mini-tts",
            "voice": TTS_VOICE or "onyx",
            "input": text,
            "instructions": HOST_STYLE,
            "response_format": "mp3",
        },
        timeout=300,
    )
    r.raise_for_status()
    return r.content


def tts_google(text):
    r = requests.post(
        "https://texttospeech.googleapis.com/v1/text:synthesize",
        params={"key": os.environ["GOOGLE_TTS_API_KEY"]},
        json={
            "input": {"text": text},
            "voice": {"languageCode": "en-US", "name": TTS_VOICE or "en-US-Chirp3-HD-Charon"},
            "audioConfig": {"audioEncoding": "MP3"},
        },
        timeout=300,
    )
    r.raise_for_status()
    return base64.b64decode(r.json()["audioContent"])


def tts_elevenlabs(text):
    voice = TTS_VOICE or "JBFqnCBsd6RMkjVDRZzb"
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
        json={"text": text, "model_id": TTS_MODEL or "eleven_flash_v2_5"},
        timeout=300,
    )
    r.raise_for_status()
    return r.content


PROVIDERS = {"openai": tts_openai, "google": tts_google, "elevenlabs": tts_elevenlabs}


def render_audio(script, out_path):
    if TTS_PROVIDER not in PROVIDERS:
        raise ValueError(f"TTS_PROVIDER must be one of {list(PROVIDERS)}")
    speak = PROVIDERS[TTS_PROVIDER]
    chunks = chunk_text(script)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        parts = []
        for n, chunk in enumerate(chunks):
            print(f"  audio chunk {n + 1}/{len(chunks)} ({len(chunk)} chars)")
            p = tmp / f"part{n:03d}.mp3"
            p.write_bytes(speak(chunk))
            parts.append(p)
        if shutil.which("ffmpeg"):
            listfile = tmp / "list.txt"
            listfile.write_text("".join(f"file '{p}'\n" for p in parts))
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listfile),
                 "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ac", "1", "-ar", "44100", "-b:a", "64k",
                 str(out_path)],
                check=True,
            )
        else:
            out_path.write_bytes(b"".join(p.read_bytes() for p in parts))


# ---------------------------------------------------------------- feed

def make_cover():
    cover = DOCS / "cover.png"
    if cover.exists():
        return
    from PIL import Image, ImageDraw, ImageFont

    def font(size, bold=False):
        for path in (
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ):
            if Path(path).exists():
                return ImageFont.truetype(path, size)
        return ImageFont.load_default(size=size)

    img = Image.new("RGB", (1400, 1400), "#1E4D3F")
    d = ImageDraw.Draw(img)
    d.rectangle([90, 90, 1310, 1310], outline="#C9A24A", width=6)
    d.text((160, 520), "The Sponsor's", font=font(130, True), fill="#F4F6F2")
    d.text((160, 670), "Playbook", font=font(130, True), fill="#F4F6F2")
    d.text((160, 880), "Private equity for operators", font=font(54), fill="#C9A24A")
    d.text((160, 960), "15 minutes a day", font=font(54), fill="#C9DCD3")
    img.save(cover)


def build_feed(state):
    base = SITE_URL
    items = []
    for e in sorted(state["episodes"], key=lambda e: e["lesson_idx"], reverse=True):
        L = LESSONS[e["lesson_idx"]]
        notes = (
            f"Module {L['module_num']}: {L['module']}.\n\nKey takeaways:\n"
            + "\n".join(f"- {t}" for t in e.get("takeaways", []))
            + f"\n\nTranscript: {base}/transcripts/{e['file'].replace('.mp3', '.txt')}"
        )
        items.append(f"""    <item>
      <title>{html.escape(f"{e['lesson_idx'] + 1}. {e['title']}")}</title>
      <description>{html.escape(notes)}</description>
      <enclosure url="{base}/episodes/{e['file']}" length="{e['bytes']}" type="audio/mpeg"/>
      <guid isPermaLink="false">sponsors-playbook-{e['lesson_idx'] + 1}-{e['generated']}</guid>
      <pubDate>{e['pub_date']}</pubDate>
      <itunes:duration>{e['duration']}</itunes:duration>
      <itunes:episode>{e['lesson_idx'] + 1}</itunes:episode>
      <itunes:season>{L['module_num']}</itunes:season>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>false</itunes:explicit>
    </item>""")

    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{html.escape(COURSE_TITLE)}</title>
    <link>{base}/</link>
    <atom:link href="{base}/feed.xml" rel="self" type="application/rss+xml"/>
    <description>{html.escape(COURSE_DESCRIPTION)}</description>
    <language>en-us</language>
    <itunes:author>{html.escape(COURSE_TITLE)}</itunes:author>
    <itunes:summary>{html.escape(COURSE_DESCRIPTION)}</itunes:summary>
    <itunes:image href="{base}/cover.png"/>
    <itunes:category text="Business"><itunes:category text="Management"/></itunes:category>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>serial</itunes:type>
    <itunes:block>Yes</itunes:block>
{chr(10).join(items)}
  </channel>
</rss>
"""
    (DOCS / "feed.xml").write_text(feed)

    rows = "\n".join(
        f'<li><strong>{e["lesson_idx"] + 1}. {html.escape(e["title"])}</strong><br>'
        f'<audio controls preload="none" src="episodes/{e["file"]}"></audio> '
        f'<a href="transcripts/{e["file"].replace(".mp3", ".txt")}">Transcript</a></li>'
        for e in sorted(state["episodes"], key=lambda e: e["lesson_idx"], reverse=True)
    )
    (DOCS / "index.html").write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>{html.escape(COURSE_TITLE)}</title>
<style>body{{font-family:Georgia,serif;max-width:680px;margin:40px auto;padding:0 20px;color:#16201C;background:#E9ECE6}}
li{{margin:0 0 22px}} audio{{width:100%;margin-top:6px}} ul{{list-style:none;padding:0}}</style></head>
<body><h1>{html.escape(COURSE_TITLE)}</h1><p>Podcast feed: <a href="feed.xml">{base}/feed.xml</a></p>
<p>{len(state["episodes"])} of {TOTAL} lessons published.</p><ul>{rows}</ul></body></html>
""")
    (DOCS / ".nojekyll").write_text("")


# ---------------------------------------------------------------- main

def fmt_duration(seconds):
    s = int(round(seconds))
    return f"{s // 3600:d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lesson", type=int, help="Lesson number (1-based) to produce or redo.")
    ap.add_argument("--script-only", action="store_true", help="Print the script; skip audio and feed.")
    ap.add_argument("--feed-only", action="store_true", help="Rebuild feed.xml and index.html only.")
    args = ap.parse_args()

    if not SITE_URL and not args.script_only:
        sys.exit("SITE_URL is not set (e.g. https://yourname.github.io/sponsors-playbook).")

    for d in (EP_DIR, TX_DIR):
        d.mkdir(parents=True, exist_ok=True)
    state = load_state()

    if args.feed_only:
        make_cover()
        build_feed(state)
        return

    i = (args.lesson - 1) if args.lesson else next_lesson_idx(state)
    if i is None:
        print("All lessons are published. Nothing to do.")
        make_cover()
        build_feed(state)
        return
    if not 0 <= i < TOTAL:
        sys.exit(f"Lesson must be between 1 and {TOTAL}.")

    L = LESSONS[i]
    print(f"Lesson {i + 1}: {L['title']}")
    script, takeaways = write_script(i, state)
    print(f"  script: {len(script.split())} words")

    if args.script_only:
        print("\n" + script + "\n\nTakeaways:\n" + "\n".join(f"- {t}" for t in takeaways))
        return

    fname = f"lesson-{i + 1:02d}.mp3"
    out = EP_DIR / fname
    render_audio(script, out)
    (TX_DIR / fname.replace(".mp3", ".txt")).write_text(
        f"{COURSE_TITLE}\nLesson {i + 1}: {L['title']}\n\n{script}\n\nKey takeaways:\n"
        + "\n".join(f"- {t}" for t in takeaways) + "\n"
    )

    now = dt.datetime.now(dt.timezone.utc)
    record = {
        "lesson_idx": i,
        "title": L["title"],
        "file": fname,
        "bytes": out.stat().st_size,
        "duration": fmt_duration(MP3(out).info.length),
        "pub_date": format_datetime(now),
        "generated": now.strftime("%Y%m%d%H%M%S"),
        "words": len(script.split()),
        "takeaways": takeaways,
        "tts": f"{TTS_PROVIDER}:{TTS_VOICE or 'default'}",
    }
    state["episodes"] = [e for e in state["episodes"] if e["lesson_idx"] != i] + [record]
    save_state(state)
    make_cover()
    build_feed(state)
    print(f"  published {fname} ({record['duration']}, {record['bytes'] / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
