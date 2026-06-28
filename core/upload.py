"""Stage 7 — Upload. Live: YouTube Data API v3. Dry-run: writes the exact upload payload.

First-time auth (live):  python run.py auth   (needs client_secret.json from Google Cloud,
YouTube Data API v3 enabled, OAuth desktop client). Produces token.json.
"""
import os

from . import util


def build_payload(meta, video_path):
    return {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": meta["tags"],
            "categoryId": meta["category_id"],
        },
        "status": {
            "privacyStatus": meta["privacy_status"],
            "selfDeclaredMadeForKids": meta["made_for_kids"],
            "containsSyntheticMedia": meta.get("ai_disclosure", False),
        },
        "media_file": video_path or "<<final.mp4 — render first>>",
    }


def upload(meta, video_path, odir):
    payload = build_payload(meta, video_path)
    util.write_json(odir / "upload_payload.json", payload)

    token = os.environ.get("YOUTUBE_TOKEN_FILE", "token.json")
    can_upload = video_path and os.path.exists(token) and os.path.exists(str(video_path))
    if not can_upload:
        util.log("upload", "DRY-RUN payload written (no token.json or no rendered video)")
        return {"status": "dry-run", "payload": str(odir / "upload_payload.json")}

    # --- Live upload (requires google-api-python-client) ---
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials.from_authorized_user_file(token)
    yt = build("youtube", "v3", credentials=creds)
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    req = yt.videos().insert(part="snippet,status",
                             body={"snippet": payload["snippet"], "status": payload["status"]},
                             media_body=media)
    resp = req.execute()
    vid = resp.get("id")
    util.log("upload", f"uploaded: https://youtu.be/{vid}")
    return {"status": "uploaded", "video_id": vid, "url": f"https://youtu.be/{vid}"}
