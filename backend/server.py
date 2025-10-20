from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import subprocess
import pty
import os
import select
import termios
import tempfile

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")


def run_command(cmd, shell=False):
    try:
        if shell:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return str(e)

def create_terminal_session(resource_params):
    """Create a new terminal session with salloc"""
    # Build salloc command from parameters
    salloc_cmd = ["salloc"]
    if resource_params.get("nodes"):
        salloc_cmd.extend(["--nodes", str(resource_params["nodes"])])
    if resource_params.get("memory"):
        salloc_cmd.extend(["--mem", f"{resource_params['memory']}G"])
    if resource_params.get("time"):
        salloc_cmd.extend(["--time", f"{resource_params['time']}:00:00"])
    
    # Add interactive shell
    salloc_cmd.extend(["--pty", "/bin/bash"])
    
    # Create pseudo-terminal
    master_fd, slave_fd = pty.openpty()
    
    # Start salloc process
    process = subprocess.Popen(
        salloc_cmd,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        preexec_fn=os.setsid
    )
    
    # Close slave fd, we'll use master to communicate
    os.close(slave_fd)
    
    return master_fd, process


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


@app.route("/api/submit/sbatch", methods=["POST"])
def submit_sbatch():
    """Handle sbatch script submission"""
    print("Received sbatch submission request")
    
    # Accept username from form data

    username = request.form.get('username')
    if not username or not username.strip():
        print("No username provided in form data.")
        return jsonify({"error": "Username is required in form data."}), 400

    username = username.strip()
    if '/' in username or '\\' in username:
        print(f"Invalid username: {username}")
        return jsonify({"error": "Invalid username."}), 400

    if 'file' not in request.files:
        print("No file in request.files")
        print("Files received:", list(request.files.keys()))
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        print("Empty filename")
        return jsonify({"error": "No file selected"}), 400

    print(f"Received file: {file.filename} from user: {username}")

    # Create user directory in files/<username>/
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files')
    user_dir = os.path.join(base_dir, username)
    try:
        os.makedirs(user_dir, exist_ok=True)
    except Exception as e:
        print(f"Failed to create user directory {user_dir}: {e}")
        return jsonify({"error": f"Failed to create user directory: {e}"}), 500

    # Save uploaded file in user directory
    script_path = os.path.join(user_dir, file.filename)
    try:
        content = file.read().decode('utf-8')
    except Exception as e:
        print(f"Failed to read uploaded file: {e}")
        return jsonify({"error": f"Failed to read uploaded file: {e}"}), 400
    print(f"Original script content:\n{content}")

    # Convert DOS line endings to UNIX
    content = content.replace('\r\n', '\n')

    # Ensure script has shebang
    if not content.startswith('#!/bin'):
        content = '#!/bin/bash\n' + content

    # Ensure basic SLURM directives are present
    slurm_directives = []
    if not any(line.startswith('#SBATCH') for line in content.split('\n')):
        slurm_directives.extend([
            '#SBATCH --job-name=default_job',
            f'#SBATCH --output={file.filename}-%j.out',  # output in user dir
            f'#SBATCH --error={file.filename}-%j.err',
            '#SBATCH --time=01:00:00',
            '#SBATCH --ntasks=1'
        ])
    if slurm_directives:
        content = '\n'.join([content.split('\n')[0]] + slurm_directives + content.split('\n')[1:])

    print(f"Processed script content:\n{content}")

    with open(script_path, 'w') as f:
        f.write(content)

    # Make script executable
    os.chmod(script_path, 0o755)

    # First check if sbatch is available
    sbatch_check = run_command(["which", "sbatch"])
    print(f"sbatch location: {sbatch_check}")

    # Verify script is valid
    verify_cmd = ["sbatch", "--test-only", script_path]
    print(f"Verifying script: {' '.join(verify_cmd)}")
    verify_output = run_command(verify_cmd)
    print(f"Verification output: {verify_output}")

    if "error" in verify_output.lower():
        return jsonify({"error": f"Invalid script: {verify_output}"}), 400

    # Submit the job from user directory
    cmd = ["sbatch", script_path]
    print(f"Running command: {' '.join(cmd)} in {user_dir}")
    output = run_command(cmd)
    print(f"sbatch output: {output}")

    # Try to parse job ID from output
    job_id = None
    output_file = None
    if "Submitted batch job" in output:
        try:
            job_id = output.split()[-1]
            print(f"Parsed job ID: {job_id}")

            # Output file path (as set above)
            output_file = os.path.join(user_dir, f"{file.filename}-{job_id}.out")
            print(f"Expected output file: {output_file}")

        except Exception as e:
            print(f"Error parsing job ID: {e}")
            pass
    else:
        print("No job ID found in output")

    # If output file exists, send it as download, else return job info
    import time
    wait_time = 0
    job_output = None
    # Wait up to 10 seconds for output file (for short jobs)
    while output_file and wait_time < 10:
        if os.path.exists(output_file):
            with open(output_file, 'rb') as f:
                from flask import send_file
                return send_file(
                    output_file,
                    as_attachment=True,
                    download_name=os.path.basename(output_file),
                    mimetype='text/plain'
                )
        time.sleep(1)
        wait_time += 1

    # If not ready, return job info and let frontend poll for download
    return jsonify({
        "message": "Job submitted",
        "output": output,
        "job_id": job_id,
        "output_file": os.path.basename(output_file) if output_file else None,
        "user": username
    })

@app.route("/api/submit/salloc", methods=["POST"])
def submit_salloc():
    """Start an interactive salloc session"""
    try:
        params = request.get_json()
        if not params:
            return jsonify({"error": "No parameters provided"}), 400
            
        # Create terminal session
        master_fd, process = create_terminal_session(params)
        
        # Store session info (you might want to use Redis or similar for production)
        session_id = os.urandom(16).hex()
        app.terminal_sessions[session_id] = {
            "fd": master_fd,
            "process": process
        }
        
        return jsonify({
            "message": "Session created",
            "session_id": session_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cancel/<job_id>", methods=["DELETE"])
def cancel_job(job_id):
    output = run_command(["scancel", str(job_id)])
    return jsonify({"result": output})


# WebSocket handlers for terminal interaction
@socketio.on('connect')
def connect():
    """Handle new WebSocket connections"""
    print("Client connected")

@socketio.on('disconnect')
def disconnect():
    """Handle WebSocket disconnections"""
    print("Client disconnected")
    # Cleanup any associated terminal session

@socketio.on('terminal_input')
def handle_terminal_input(data):
    """Handle input from the frontend terminal"""
    session_id = data.get('session_id')
    input_data = data.get('input')
    
    if not session_id or not input_data:
        return
        
    session = app.terminal_sessions.get(session_id)
    if not session:
        emit('terminal_error', {'error': 'Session not found'})
        return
        
    try:
        os.write(session['fd'], input_data.encode())
    except Exception as e:
        emit('terminal_error', {'error': str(e)})

def read_terminal_output(session_id):
    """Read and emit terminal output"""
    session = app.terminal_sessions.get(session_id)
    if not session:
        return
        
    while True:
        r, _, _ = select.select([session['fd']], [], [], 0.1)
        if session['fd'] in r:
            try:
                data = os.read(session['fd'], 1024)
                if data:
                    socketio.emit('terminal_output', {
                        'session_id': session_id,
                        'output': data.decode()
                    })
            except Exception:
                break

# Initialize terminal sessions storage
app.terminal_sessions = {}

if __name__ == '__main__':
    try:
        # Test SLURM commands availability
        print("Testing SLURM commands...")
        sbatch_path = run_command(["which", "sbatch"])
        if not sbatch_path:
            print("WARNING: sbatch not found in PATH")
        else:
            print(f"sbatch found at: {sbatch_path}")
            
        salloc_path = run_command(["which", "salloc"])
        if not salloc_path:
            print("WARNING: salloc not found in PATH")
        else:
            print(f"salloc found at: {salloc_path}")
            
        sinfo_test = run_command(["sinfo", "--version"])
        print(f"sinfo version check: {sinfo_test}")
        
        print("\nStarting server on http://0.0.0.0:8000")
        socketio.run(app, host='0.0.0.0', port=8000, debug=True)
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()

