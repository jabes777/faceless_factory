#!/usr/bin/env python3
"""faceless_factory — end-to-end faceless YouTube video pipeline.

USAGE
  python run.py                       # one video from the next topic in topics.txt
  python run.py "tu tema aqui"        # one video from an explicit topic
  python run.py --batch 5             # produce N videos from topics.txt
  python run.py auth                  # one-time YouTube OAuth (live mode)

Runs in DRY-RUN with zero API keys (deterministic local generation + macOS 'say' audio).
Add keys to .env to switch each stage to real APIs automatically.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import util, ideas, script, voice, visuals, assemble, thumbnail, metadata, upload  # noqa: E402

TOPICS = Path(__file__).resolve().parent / "topics.txt"
USED = Path(__file__).resolve().parent / "output" / ".used_topics"


def next_topic():
    used = set(USED.read_text().splitlines()) if USED.exists() else set()
    for line in TOPICS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and line not in used:
            return line
    return None


def mark_used(topic):
    USED.parent.mkdir(parents=True, exist_ok=True)
    with open(USED, "a", encoding="utf-8") as f:
        f.write(topic + "\n")


def compliance_gate(config, script_text):
    """Lightweight original-substance heuristic for the July-2025 inauthentic policy."""
    words = script_text.split()
    uniq_ratio = len(set(w.lower() for w in words)) / max(1, len(words))
    ok = uniq_ratio >= config["compliance"]["min_unique_substance_score"] * 0.5  # heuristic floor
    return ok, round(uniq_ratio, 3)


def make_one(config, topic):
    t0 = time.time()
    util.log("pipeline", f"=== MODE: {util.mode().upper()} | topic: {topic!r} ===")
    idea = ideas.generate(config, topic)
    odir = util.out_dir(util.slugify(idea["chosen_title"]))

    scr = script.generate(config, idea)
    ok, ratio = compliance_gate(config, scr["text"])
    util.log("comply", f"unique-substance ratio={ratio} -> {'PASS' if ok else 'REVIEW'}")
    util.write_text(odir / "script.txt", scr["text"])

    vo = voice.generate(config, scr["text"], odir)
    vis = visuals.generate(config, scr["text"], topic=topic)
    util.write_json(odir / "storyboard.json", vis)
    asm = assemble.generate(config, vis["storyboard"], vo["audio_path"], odir,
                            srt_path=vo.get("srt_path"))
    thumb = thumbnail.generate(config, idea, odir)
    meta = metadata.generate(config, idea, vis, odir)

    video_path = str(odir / "final.mp4") if (odir / "final.mp4").exists() else None
    up = upload.upload(meta, video_path, odir)

    manifest = {
        "topic": topic, "mode": util.mode(), "title": idea["chosen_title"],
        "title_candidates": idea["title_candidates"], "compliance_ratio": ratio,
        "compliance_pass": ok, "word_count": scr["word_count"],
        "audio": vo["audio_path"], "ssml": vo["ssml_path"],
        "srt": vo.get("srt_path"),
        "render": {"shotstack": asm["shotstack_plan"], "ffmpeg": asm["ffmpeg_script"],
                   "ffmpeg_available": asm["ffmpeg_available"]},
        "thumbnail_overlay": thumb["overlay_text"], "upload": up,
        "seconds": round(time.time() - t0, 1), "output_dir": str(odir),
    }
    util.write_json(odir / "manifest.json", manifest)
    util.log("pipeline", f"DONE in {manifest['seconds']}s -> {odir}")
    return manifest


def main():
    args = sys.argv[1:]
    if args and args[0] == "auth":
        print("Run OAuth: place client_secret.json here, then use google-auth-oauthlib "
              "InstalledAppFlow to create token.json. See README 'Going live'.")
        return
    config = util.load_config()

    if args and args[0] == "--batch":
        n = int(args[1]) if len(args) > 1 else 3
        made = []
        for _ in range(n):
            topic = next_topic()
            if not topic:
                util.log("pipeline", "no more unused topics in topics.txt")
                break
            made.append(make_one(config, topic))
            mark_used(topic)
        util.log("pipeline", f"batch complete: {len(made)} videos")
        return

    topic = args[0] if args else next_topic()
    if not topic:
        util.log("pipeline", "no topic given and topics.txt exhausted")
        return
    make_one(config, topic)
    if not args:
        mark_used(topic)


if __name__ == "__main__":
    main()
