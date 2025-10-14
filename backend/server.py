from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import tempfile
import os

app = Flask(__name__)
CORS(app)


def run_command(cmd, shell=False):
    try:
        if shell:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return str(e)


@app.route("/api/queue", methods=["GET"])
def get_queue():
    # Use squeue with a pipe-delimited format and return a JSON object with a 'jobs' array
    output = run_command(["squeue", "-o", "%i|%u|%j|%t|%M|%D|%R"])  # list: jobid|user|name|state|time|nodes|reason
    jobs = []
    if not output:
        return jsonify({"jobs": jobs})

    lines = output.strip().split("\n")
    # skip header if present
    if len(lines) > 0 and "JOBID" in lines[0].upper():
        lines = lines[1:]

    for line in lines:
        parts = line.split("|")
        if len(parts) < 7:
            continue
        jobs.append({
            "job_id": parts[0].strip(),
            "user": parts[1].strip(),
            "name": parts[2].strip(),
            "state": parts[3].strip(),
            "time": parts[4].strip(),
            "nodes": parts[5].strip(),
            "reason": parts[6].strip()
        })
    return jsonify({"jobs": jobs})


@app.route("/api/usage", methods=["GET"])
def get_usage():
    # Try to get node-level usage using sinfo. The format below attempts to return
    # a small set of fields the frontend expects. This will vary per-cluster.
    output = run_command(["sinfo", "-N", "-o", "%N|%t|%C|%m"])  # name|state|CPUs(alloc/idle/other/total)|memory
    nodes = []
    if not output:
        return jsonify({"nodes": nodes})

    lines = output.strip().split("\n")
    # skip header if present
    if len(lines) > 0 and ("NODELIST" in lines[0].upper() or "%N" in lines[0]):
        lines = lines[1:]

    for line in lines:
        parts = line.split("|")
        if len(parts) < 4:
            continue
        name = parts[0].strip()
        state = parts[1].strip()
        cpu_field = parts[2].strip()
        mem_field = parts[3].strip()

        # cpu_field is usually like '0/16/0/16' (alloc/idle/other/total)
        cpus_allocated = cpus_idle = cpus_offline = cpus_total = 0
        try:
            cpu_parts = cpu_field.split("/")
            if len(cpu_parts) == 4:
                cpus_allocated = int(cpu_parts[0])
                cpus_idle = int(cpu_parts[1])
                cpus_offline = int(cpu_parts[2])
                cpus_total = int(cpu_parts[3])
        except Exception:
            pass

        # mem_field may contain units; try to normalize to MB if possible, otherwise keep raw
        memory = mem_field

        nodes.append({
            "name": name,
            "state": state,
            "cpus_allocated": cpus_allocated,
            "cpus_idle": cpus_idle,
            "cpus_offline": cpus_offline,
            "cpus": cpus_total,
            "memory_allocated": None,
            "memory": memory
        })

    return jsonify({"nodes": nodes})


@app.route("/api/submit", methods=["POST"])
def submit_job():
    # Accept either form-data (frontend uses FormData) or JSON
    script = None
    if request.form and "script" in request.form:
        script = request.form.get("script")
    else:
        try:
            script = request.get_json(force=True).get("script")
        except Exception:
            script = None

    if not script:
        return jsonify({"error": "No script provided"}), 400

    # write script to a temp file and call sbatch
    fd, path = tempfile.mkstemp(suffix=".sh", text=True)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(script)
        output = run_command(["sbatch", path])
    finally:
        try:
            os.remove(path)
        except Exception:
            pass

    return jsonify({"message": "submitted", "output": output})


@app.route("/api/cancel/<job_id>", methods=["DELETE"])
def cancel_job(job_id):
    output = run_command(["scancel", str(job_id)])
    return jsonify({"result": output})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

