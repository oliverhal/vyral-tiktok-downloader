"""
Vyral Labs — TikTok Video Downloader (MVP 1)
Backend server: accepts TikTok URLs, downloads HD videos without watermark,
organises by creator username, and serves a ZIP file.
"""

import csv
import io
import os
import re
import uuid
import shutil
import zipfile
import threading
import time
from pathlib import Path

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

import yt_dlp

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

# Auto-detect whether frontend files are in a "static/" subfolder or at root.
# (GitHub upload sometimes flattens folder structure.)
_app_dir = os.path.dirname(os.path.abspath(__file__))
_static_dir = "static" if os.path.isdir(os.path.join(_app_dir, "static")) else "."

app = Flask(__name__, static_folder=_static_dir, static_url_path="/static")
CORS(app)

DOWNLOAD_DIR = Path(os.environ.get("DOWNLOAD_DIR", "/tmp/vyral_downloads"))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_VIDEOS = int(os.environ.get("MAX_VIDEOS_PER_BATCH", 50))
JOB_EXPIRY_HOURS = 2

# Instagram cookies: prefer a file path, fall back to raw cookie content in env var.
# On Railway (no persistent filesystem), set INSTAGRAM_COOKIES to the contents of
# your cookies.txt file and leave INSTAGRAM_COOKIES_FILE unset.
_INSTAGRAM_COOKIES_FILE = os.environ.get("INSTAGRAM_COOKIES_FILE", "")
_INSTAGRAM_COOKIES_CONTENT = os.environ.get("INSTAGRAM_COOKIES", "")

if not _INSTAGRAM_COOKIES_FILE and _INSTAGRAM_COOKIES_CONTENT:
    _cookie_tmp = Path("/tmp/instagram_cookies.txt")
    _cookie_tmp.write_text(_INSTAGRAM_COOKIES_CONTENT)
    _INSTAGRAM_COOKIES_FILE = str(_cookie_tmp)

INSTAGRAM_COOKIES_FILE = _INSTAGRAM_COOKIES_FILE

# In-memory job store (fine for MVP — no database needed)
jobs: dict = {}
jobs_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def cleanup_old_jobs():
    """Delete jobs (and their ZIP files) older than JOB_EXPIRY_HOURS."""
    now = time.time()
    with jobs_lock:
        expired = [
            jid
            for jid, job in jobs.items()
            if now - job["created_at"] > JOB_EXPIRY_HOURS * 3600
        ]
        for jid in expired:
            job = jobs.pop(jid)
            zip_path = job.get("zip_path")
            if zip_path and os.path.exists(zip_path):
                os.remove(zip_path)
            job_dir = DOWNLOAD_DIR / jid
            if job_dir.exists():
                shutil.rmtree(job_dir, ignore_errors=True)


def sanitize(name: str, max_length: int = 80) -> str:
    """Make a string safe for use as a filename."""
    name = re.sub(r"[^\w\s\-]", "", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name[:max_length] if name else "untitled"


def username_from_url(url: str) -> str | None:
    """Extract @username from a full TikTok URL (won't work for short links)."""
    m = re.search(r"tiktok\.com/@([^/?#]+)", url)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Download worker (runs in a background thread)
# ---------------------------------------------------------------------------


def process_job(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return

    job["status"] = "processing"
    job_dir = DOWNLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    for video in job["videos"]:
        video["status"] = "downloading"
        url = video["url"]

        try:
            # --- Step 1: extract metadata ---------------------------------
            base_opts: dict = {"quiet": True, "no_warnings": True}
            if "instagram.com" in url and INSTAGRAM_COOKIES_FILE and os.path.exists(INSTAGRAM_COOKIES_FILE):
                base_opts["cookiefile"] = INSTAGRAM_COOKIES_FILE

            with yt_dlp.YoutubeDL(base_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            username = (
                info.get("uploader")
                or info.get("creator")
                or info.get("channel")
                or username_from_url(info.get("webpage_url", url))
                or username_from_url(url)
                or "unknown"
            )
            username = username.lstrip("@")
            username_safe = sanitize(username)

            title = info.get("title") or info.get("id") or "video"
            title_safe = sanitize(title, max_length=60)
            video_id = info.get("id", "")

            # --- Step 2: create user folder --------------------------------
            user_dir = job_dir / username_safe
            user_dir.mkdir(exist_ok=True)

            filename = f"{title_safe}_{video_id}" if video_id else title_safe
            output_tpl = str(user_dir / f"{filename}.%(ext)s")

            # --- Step 3: download video (HD, no watermark) -----------------
            ydl_opts = {
                "format": "best[ext=mp4]/best",
                "outtmpl": output_tpl,
                "quiet": True,
                "no_warnings": True,
                "socket_timeout": 30,
                "retries": 3,
            }
            if "instagram.com" in url and INSTAGRAM_COOKIES_FILE and os.path.exists(INSTAGRAM_COOKIES_FILE):
                ydl_opts["cookiefile"] = INSTAGRAM_COOKIES_FILE

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            video["status"] = "done"
            video["username"] = username
            video["caption"] = (info.get("description") or info.get("title") or "")[:500]
            video["views"] = info.get("view_count") or info.get("play_count")
            video["comments"] = info.get("comment_count")
            video["reposts"] = info.get("repost_count")
            video["duration"] = info.get("duration")  # seconds
            video["upload_date"] = info.get("upload_date") or ""  # YYYYMMDD

        except Exception as exc:
            video["status"] = "failed"
            video["error"] = str(exc)[:300]

    # --- Step 4: zip everything up -----------------------------------------
    done_count = sum(1 for v in job["videos"] if v["status"] == "done")

    if done_count > 0:
        zip_path = DOWNLOAD_DIR / f"{job_id}.zip"
        with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(str(job_dir)):
                for fname in files:
                    full = os.path.join(root, fname)
                    arcname = os.path.relpath(full, str(job_dir))
                    zf.write(full, arcname)

            # Write report.csv into the ZIP
            buf = io.StringIO()
            writer = csv.DictWriter(
                buf,
                fieldnames=["Username", "Caption", "URL", "Views", "Comments", "Reposts", "Duration (s)", "Date"],
                lineterminator="\r\n",
            )
            writer.writeheader()
            for v in job["videos"]:
                if v["status"] == "done":
                    raw_date = v.get("upload_date") or ""
                    date_str = (
                        f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
                        if len(raw_date) == 8
                        else raw_date
                    )
                    writer.writerow({
                        "Username": f"@{v.get('username', '')}",
                        "Caption": v.get("caption", ""),
                        "URL": v["url"],
                        "Views": v.get("views") if v.get("views") is not None else "",
                        "Comments": v.get("comments") if v.get("comments") is not None else "",
                        "Reposts": v.get("reposts") if v.get("reposts") is not None else "",
                        "Duration (s)": v.get("duration") if v.get("duration") is not None else "",
                        "Date": date_str,
                    })
            zf.writestr("report.csv", buf.getvalue())
        job["zip_path"] = str(zip_path)

    # clean up the unzipped folder
    shutil.rmtree(str(job_dir), ignore_errors=True)
    job["status"] = "completed"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    return send_from_directory(_static_dir, "index.html")


@app.route("/api/download", methods=["POST"])
def start_download():
    cleanup_old_jobs()

    data = request.get_json(force=True)
    raw_urls = data.get("urls", [])

    if not raw_urls:
        return jsonify({"error": "No URLs provided."}), 400

    urls = []
    for url in raw_urls:
        url = url.strip()
        if url and ("tiktok.com" in url or "instagram.com" in url or "youtube.com/shorts" in url or "youtu.be" in url):
            urls.append(url)

    if not urls:
        return (
            jsonify(
                {
                    "error": "No valid URLs found. "
                    "Make sure each URL contains tiktok.com, instagram.com, or youtube.com/shorts."
                }
            ),
            400,
        )

    if len(urls) > MAX_VIDEOS:
        return (
            jsonify({"error": f"Too many URLs. Maximum is {MAX_VIDEOS} per batch."}),
            400,
        )

    job_id = uuid.uuid4().hex[:12]
    job = {
        "id": job_id,
        "status": "pending",
        "created_at": time.time(),
        "videos": [
            {"url": u, "status": "pending", "username": None, "error": None}
            for u in urls
        ],
        "zip_path": None,
    }

    with jobs_lock:
        jobs[job_id] = job

    thread = threading.Thread(target=process_job, args=(job_id,), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def get_status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found."}), 404
    return jsonify(
        {
            "id": job["id"],
            "status": job["status"],
            "videos": job["videos"],
            "zip_ready": job["zip_path"] is not None,
        }
    )


@app.route("/api/debug")
def debug():
    cookie_file = INSTAGRAM_COOKIES_FILE
    cookie_file_exists = bool(cookie_file and os.path.exists(cookie_file))
    cookie_file_size = os.path.getsize(cookie_file) if cookie_file_exists else 0
    cookie_env_set = bool(os.environ.get("INSTAGRAM_COOKIES", ""))
    cookie_file_env_set = bool(os.environ.get("INSTAGRAM_COOKIES_FILE", ""))
    return jsonify({
        "cookie_file_path": cookie_file or None,
        "cookie_file_exists": cookie_file_exists,
        "cookie_file_size_bytes": cookie_file_size,
        "INSTAGRAM_COOKIES_env_set": cookie_env_set,
        "INSTAGRAM_COOKIES_FILE_env_set": cookie_file_env_set,
    })


@app.route("/api/download-zip/<job_id>")
def download_zip(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job or not job.get("zip_path"):
        return jsonify({"error": "ZIP not ready or job not found."}), 404
    return send_file(
        job["zip_path"],
        mimetype="application/zip",
        as_attachment=True,
        download_name="tiktok_videos.zip",
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Vyral Labs TikTok Downloader running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
