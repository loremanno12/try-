from flask import Flask, jsonify
from flask_cors import CORS
import psutil
import subprocess
import time
import os

app = Flask(__name__)
CORS(app)


def get_cpu_temp():
    try:
        temp = subprocess.check_output(
            ["vcgencmd", "measure_temp"]
        ).decode()
        return temp.replace("temp=", "").replace("'C", "").strip()
    except (FileNotFoundError, subprocess.CalledProcessError, OSError):
        return "N/A"


def get_docker_containers():
    try:
        result = subprocess.check_output(
            ["docker", "ps", "-a", "--format", "{{.Names}}|{{.Image}}|{{.Status}}|{{.State}}"],
            text=True
        ).strip().split("\n")
        containers = []
        for line in result:
            if line:
                parts = line.split("|")
                containers.append({
                    "name": parts[0],
                    "image": parts[1],
                    "status": parts[3].lower(),
                    "uptime": parts[2],
                    "cpu": "N/A",
                    "memory": "N/A",
                })
        return containers
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError, IndexError):
        return []


@app.route("/api/stats")
def api_stats():
    temp = get_cpu_temp()
    uptime_seconds = time.time() - psutil.boot_time()
    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    try:
        temp_val = float(temp) if temp != "N/A" else 0
    except (ValueError, TypeError):
        temp_val = 0
    return jsonify({
        "cpu": round(psutil.cpu_percent(interval=0.5), 1),
        "memory": round(psutil.virtual_memory().percent, 1),
        "storage": round(psutil.disk_usage("/").percent, 1),
        "temperature": temp_val,
        "uptime": f"{days} giorni, {hours} ore",
    })


@app.route("/api/containers")
def api_containers():
    return jsonify(get_docker_containers())


@app.route("/api/history")
def api_history():
    history = []
    for i in range(24):
        history.append({
            "time": f"{str(i).zfill(2)}:00",
            "cpu": round(psutil.cpu_percent(interval=0.1), 1),
            "memory": round(psutil.virtual_memory().percent, 1),
            "network": round(psutil.net_io_counters().bytes_recv / (1024 * 1024), 1),
        })
    return jsonify(history)


@app.route("/")
def index():
    return jsonify({
        "service": "raspi-status",
        "description": "API per dashboard. Usa gli endpoint JSON sotto.",
        "endpoints": {
            "stats": "/api/stats",
            "containers": "/api/containers",
            "history": "/api/history",
        },
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
