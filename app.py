from flask import Flask, request, send_file, render_template
import sys
import subprocess
import os
import uuid
import threading

app = Flask(__name__)

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def process_video():
    if "video" not in request.files:
        return "لم يتم اختيار فيديو", 400

    video = request.files["video"]

    if video.filename == "":
        return "لم يتم اختيار فيديو", 400

    option = request.form.get("option", "mp4")
    resolution = request.form.get("resolution", "تلقائي")
    fps = request.form.get("fps", "تلقائي")
    codec = request.form.get("codec", "H.264")

    file_id = str(uuid.uuid4())
    input_file = os.path.join(UPLOAD_DIR, file_id + "_input")
    output_file = os.path.join(OUTPUT_DIR, file_id + "_output.mp4")

    video.save(input_file)

    if not hasattr(app, "progress"):
        app.progress = {}

    app.progress[file_id] = {
        "status": "processing",
        "progress": 0
    }

    def run_ffmpeg():
        try:
            duration = float(subprocess.check_output([
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                input_file
            ]).decode().strip())

            if option == "audio":
                output = os.path.join(
                    OUTPUT_DIR, file_id + "_audio.m4a"
                )

                command = [
                    "ffmpeg", "-y",
                    "-i", input_file,
                    "-vn",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-progress", "pipe:1",
                    "-nostats",
                    output
                ]
            else:
                output = output_file

                command = [
                    "ffmpeg", "-y",
                    "-i", input_file
                ]

                if resolution == "4K":
                    command += ["-vf", "scale=3840:2160"]
                elif resolution == "1080p":
                    command += ["-vf", "scale=1920:1080"]
                elif resolution == "720p":
                    command += ["-vf", "scale=1280:720"]

                if fps != "تلقائي":
                    command += ["-r", fps]

                if codec == "H.265":
                    command += ["-c:v", "libx265"]
                else:
                    command += ["-c:v", "libx264"]

                command += [
                    "-crf", "23",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-movflags", "+faststart",
                    "-progress", "pipe:1",
                    "-nostats",
                    output
                ]

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
stderr=subprocess.STDOUT,
                text=True
            )

            for line in process.stdout:
                if line.startswith("out_time_ms="):
                    value = line.split("=")[1].strip();
                    if not value.isdigit():
                        continue
                    current = int(value)
                    percent = int(
                        min(99, (current / 1000000) / duration * 100)
                    )
                    app.progress[file_id]["progress"] = percent

            process.wait()

            if process.returncode != 0:
                error = process.stderr.read()
                print("FFmpeg ERROR:", error)
                raise RuntimeError("FFmpeg failed")

            app.progress[file_id] = {
                "status": "done",
                "progress": 100,
                "output": output
            }

            os.remove(input_file)

        except Exception as e:
            print("PROCESS ERROR:", repr(e))
            if os.path.exists(input_file):
                os.remove(input_file)

            app.progress[file_id] = {
                "status": "error",
                "progress": 0
            }

    threading.Thread(
        target=run_ffmpeg,
        daemon=True
    ).start()

    return {
        "job_id": file_id
    }


@app.route("/progress/<job_id>")
def video_progress(job_id):
    if not hasattr(app, "progress"):
        return {"status": "error", "progress": 0}

    return app.progress.get(
        job_id,
        {"status": "error", "progress": 0}
    )


@app.route("/download/<job_id>")
def download_video(job_id):
    job = app.progress.get(job_id)

    if not job or job.get("status") != "done":
        return "الملف غير جاهز", 404

    return send_file(
        job["output"],
        as_attachment=True
    )

@app.route("/download-url", methods=["POST"])
def download_url():
    url = request.form.get("url")

    if not url:
        return {"error": "الرابط غير موجود"}, 400

    job_id = str(uuid.uuid4())
    output = os.path.join(OUTPUT_DIR, job_id + ".mp4")

    if not hasattr(app, "url_progress"):
        app.url_progress = {}

    app.url_progress[job_id] = {"status": "processing", "progress": 0}

    def run_download():
        try:
            command = [
                sys.executable, "-m", "yt_dlp",
                "-f", "bv*+ba/b",
                "--merge-output-format", "mp4",
                "--newline",
                "--progress",
                "-o", output,
                url
            ]

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            import re

            for line in process.stdout:
                match = re.search(r'(\d+(?:\.\d+)?)%', line)
                if match:
                    app.url_progress[job_id]["progress"] = min(99, int(float(match.group(1))))

            process.wait()

            if process.returncode != 0:
                raise RuntimeError("yt-dlp failed")

            app.url_progress[job_id] = {
                "status": "done",
                "progress": 100,
                "output": output
            }

        except Exception as e:
            print("DOWNLOAD ERROR:", repr(e))
            app.url_progress[job_id] = {"status": "error", "progress": 0}

    threading.Thread(target=run_download, daemon=True).start()

    return {"job_id": job_id}

@app.route("/download-url/<job_id>")
def download_url_file(job_id):
    job = app.url_progress.get(job_id)
    if not job or job.get("status") != "done":
        return "الملف غير جاهز", 404
    return send_file(job["output"], as_attachment=True)

@app.route("/download-progress/<job_id>")
def download_progress(job_id):
    if not hasattr(app, "url_progress"):
        return {"status": "error", "progress": 0}
    return app.url_progress.get(job_id, {"status": "error", "progress": 0})

@app.route("/files")
def list_files():
    return {"files": os.listdir(OUTPUT_DIR)}

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080))
    )
