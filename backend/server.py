from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import subprocess
import pty
import os
import select
import termios
import tempfile
import struct
import fcntl
import getpass

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5173", "http://localhost:8080", "http://localhost:8001"],
        "methods": ["GET", "POST", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"]
    }
})
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:5173", "http://localhost:8080", "http://localhost:8001"])


def run_command(cmd, shell=False):
    try:
        # `capture_output` and `text` keywords were added in Python 3.7+.
        # For Python 3.6 compatibility we explicitly capture stdout/stderr
        # and use `universal_newlines=True` to get text output.
        if shell:
            result = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
        else:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
        stdout = result.stdout or ''
        stderr = result.stderr or ''
        return stdout if result.returncode == 0 else stderr
    except Exception as e:
        return str(e)

def create_terminal_session(resource_params):
    """Create a new terminal session with salloc using simplest working approach"""
    print(f"Creating terminal session with params: {resource_params}")
    
    # Build salloc command with minimal parameters and add bash directly
    salloc_cmd = ["salloc"]
    if resource_params.get("nodes"):
        salloc_cmd.extend(["--nodes", str(resource_params["nodes"])])
    if resource_params.get("memory"):
        salloc_cmd.extend(["--mem", f"{resource_params['memory']}G"])
    if resource_params.get("time"):
        salloc_cmd.extend(["--time", f"{resource_params['time']}:00:00"])
    
    # Add bash at the end to start shell immediately
    salloc_cmd.append("/bin/bash")

    print(f"Running salloc command: {' '.join(salloc_cmd)}")

    # Create pseudo-terminal
    master_fd, slave_fd = pty.openpty()

    try:
        # Set terminal size on the slave PTY (master_fd is for reading/writing)
        rows, cols = 24, 80  # Default size
        winsize = struct.pack('HHHH', rows, cols, 0, 0)
        try:
            fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)
        except Exception as ex:
            print(f"Warning: could not set window size on slave PTY: {ex}")
        
        # Start salloc process with PTY
        # Use pty.fork() so the child has the PTY as its controlling terminal.
        pid, master_fd = pty.fork()
        if pid == 0:
            # Child: replace process with salloc + /bin/bash
            try:
                # set session env
                os.environ['TERM'] = 'xterm'
                # Execute salloc command
                os.execvp(salloc_cmd[0], salloc_cmd)
            except Exception as e:
                print(f"Failed to exec salloc: {e}")
                os._exit(1)

        # Parent: pid is child pid, master_fd is file descriptor for IO
        print(f"Started child salloc pid={pid} with master_fd={master_fd}")
        return master_fd, {'pid': pid}

        # Close slave fd, we'll use master to communicate
        os.close(slave_fd)
        print("Started salloc process with PTY")
        
        return master_fd, process
        
    except Exception as e:
        print(f"Error in create_terminal_session: {str(e)}")
        os.close(master_fd)
        os.close(slave_fd)
        if 'process' in locals():
            process.terminate()
        raise
        print(f"salloc stdout: {stdout}")
        print(f"salloc stderr: {stderr}")
        
        if salloc_process.returncode != 0:
            raise Exception(f"salloc failed: {stderr}")

        # Parse the job ID from salloc output
        import re
        job_id_match = re.search(r"Granted job allocation (\d+)", stdout)
        if not job_id_match:
            raise Exception(f"Could not find job ID in salloc output. Output was: {stdout}")

        job_id = job_id_match.group(1)
        print(f"Got job ID: {job_id}")

        # Now start an interactive shell using srun
        srun_cmd = ["srun", "--jobid", job_id, "/bin/bash"]
        print(f"Starting srun with command: {' '.join(srun_cmd)}")
        
        process = subprocess.Popen(
            srun_cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            preexec_fn=os.setsid
        )

        # Close slave fd, we'll use master to communicate
        os.close(slave_fd)
        print("Interactive shell started successfully")
        
        return master_fd, process

    except subprocess.TimeoutExpired:
        print("salloc timed out after 10 seconds")
        if 'salloc_process' in locals():
            salloc_process.terminate()
        os.close(master_fd)
        os.close(slave_fd)
        raise Exception("Resource allocation timed out. No resources may be immediately available.")
        
    except Exception as e:
        print(f"Error in create_terminal_session: {str(e)}")
        if 'salloc_process' in locals():
            salloc_process.terminate()
        os.close(master_fd)
        os.close(slave_fd)
        raise


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


def parse_memory_value(memory_str):
    """Convert memory string (e.g., '16G', '1024M') to GB value"""
    try:
        if not memory_str:
            print(f"Warning: Empty memory string")
            return 0
        
        memory_str = str(memory_str).strip().upper()
        print(f"Parsing memory value: {memory_str}")
        
        # Handle 'N/A' or similar
        if memory_str in ['N/A', 'NONE', '(NULL)']:
            print(f"Warning: Invalid memory string: {memory_str}")
            return 0
            
        # Extract numeric part
        numeric_part = ''.join(c for c in memory_str if c.isdigit() or c == '.')
        if not numeric_part:
            print(f"Warning: No numeric value in memory string: {memory_str}")
            return 0
            
        value = float(numeric_part)
        
        # Convert to GB
        if 'T' in memory_str:
            return value * 1024
        elif 'G' in memory_str:
            return value
        elif 'M' in memory_str:
            return value / 1024
        elif 'K' in memory_str:
            return value / (1024 * 1024)
            
        print(f"Warning: No unit in memory string: {memory_str}, assuming GB")
        return value
        
    except Exception as e:
        print(f"Error parsing memory value '{memory_str}': {str(e)}")
        return 0

@app.route("/api/debug/sample-resources", methods=["GET"])
def get_sample_resources():
    """Return sample resource data for testing the UI"""
    return jsonify({
        "total_nodes": 4,
        "allocated_nodes": 2,
        "total_cpus": 64,
        "allocated_cpus": 32,
        "total_memory": 256,
        "allocated_memory": 128,
        "partitions": [
            {
                "name": "compute",
                "total_nodes": 2,
                "allocated_nodes": 1,
                "total_cpus": 32,
                "allocated_cpus": 16,
                "total_memory": 128,
                "allocated_memory": 64
            },
            {
                "name": "gpu",
                "total_nodes": 2,
                "allocated_nodes": 1,
                "total_cpus": 32,
                "allocated_cpus": 16,
                "total_memory": 128,
                "allocated_memory": 64
            }
        ],
        "nodes": [
            {
                "name": "node1",
                "state": "allocated",
                "partition": "compute",
                "cpus_allocated": 16,
                "cpus_idle": 0,
                "cpus_total": 16,
                "memory_total": 64,
                "memory_free": 0,
                "memory_used": 64
            },
            {
                "name": "node2",
                "state": "idle",
                "partition": "compute",
                "cpus_allocated": 0,
                "cpus_idle": 16,
                "cpus_total": 16,
                "memory_total": 64,
                "memory_free": 64,
                "memory_used": 0
            }
        ],
        "gpu_nodes": {
            "node3": "Tesla V100",
            "node4": "Tesla V100"
        }
    })
def run_command(command, cwd=None, timeout=5):
    """
    Executes a shell command and returns its stdout or an error string.
    Accepts optional `cwd` to run the command in a specific working directory and
    an optional `timeout` (seconds) to override the default timeout.
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
            cwd=cwd,
        )
        return result.stdout.strip()
    except FileNotFoundError:
        return f"error: command not found: {command[0]}"
    except subprocess.CalledProcessError as e:
        # Return stderr if command fails (include returncode for debugging)
        stderr = e.stderr.strip() if e.stderr else ''
        return f"error: command failed (rc={e.returncode}): {stderr}"
    except subprocess.TimeoutExpired as e:
        # Include partial output if available
        out = getattr(e, 'output', '') or ''
        return f"error: command timed out after {timeout}s. partial_output: {out}"
    except Exception as e:
        return f"error: unknown: {str(e)}"

def parse_memory_value(mem_str):
    """
    Parses memory string (sinfo -o '%m' and '%e' report in MB).
    """
    try:
        # sinfo reports in Megabytes, just convert to integer
        return int(mem_str.strip())
    except ValueError:
        # Handle non-integer values like 'N/A'
        return 0


def get_node_info():
    """Return a list of node dicts with cpu/memory/partition/state info.

    Uses `sinfo -N -h -o "%N|%t|%C|%m|%e|%P"` and falls back to an empty list on error.
    """
    try:
        out = run_command(["sinfo", "-N", "-h", "-o", "%N|%t|%C|%m|%e|%P"])
        if not out or "error" in out.lower():
            return []

        nodes = []
        for line in [ln for ln in out.strip().splitlines() if ln.strip()]:
            parts = line.split("|")
            if len(parts) < 6:
                continue
            name, state, cpu_field, total_mem_str, free_mem_str, partition = [p.strip() for p in parts[:6]]
            # CPU format allocated/idle/other/total
            cpu_parts = cpu_field.split('/')
            try:
                if len(cpu_parts) == 4:
                    cpus_allocated = int(cpu_parts[0])
                    cpus_idle = int(cpu_parts[1])
                    cpus_total = int(cpu_parts[3])
                else:
                    cpus_allocated = cpus_idle = cpus_total = 0
            except Exception:
                cpus_allocated = cpus_idle = cpus_total = 0

            try:
                total_mem_mb = parse_memory_value(total_mem_str)
            except Exception:
                total_mem_mb = 0
            try:
                free_mem_mb = parse_memory_value(free_mem_str)
            except Exception:
                free_mem_mb = 0

            used_mem_mb = 0
            if total_mem_mb > 0:
                if not any(s in state for s in ("down", "drain", "fail")):
                    used_mem_mb = max(0, total_mem_mb - free_mem_mb)

            nodes.append({
                'name': name,
                'state': state,
                'partition': partition,
                'cpus_allocated': cpus_allocated,
                'cpus_idle': cpus_idle,
                'cpus_total': cpus_total,
                'memory_total_mb': total_mem_mb,
                'memory_free_mb': free_mem_mb,
                'memory_used_mb': used_mem_mb
            })

        return nodes
    except Exception as e:
        print(f"get_node_info error: {e}")
        return []


def get_partition_info():
    """Aggregate partition statistics from nodes (best-effort).

    Returns a list of partition dicts similar to the UI's expected shape.
    """
    try:
        nodes = get_node_info()
        partitions: dict = {}
        for n in nodes:
            p = n.get('partition') or 'unknown'
            if p not in partitions:
                partitions[p] = {
                    'name': p,
                    'total_nodes': 0,
                    'allocated_nodes': 0,
                    'total_cpus': 0,
                    'allocated_cpus': 0,
                    'total_memory_mb': 0,
                    'allocated_memory_mb': 0
                }
            ps = partitions[p]
            ps['total_nodes'] += 1
            if n.get('cpus_allocated', 0) > 0:
                ps['allocated_nodes'] += 1
            ps['total_cpus'] += int(n.get('cpus_total', 0) or 0)
            ps['allocated_cpus'] += int(n.get('cpus_allocated', 0) or 0)
            ps['total_memory_mb'] += int(n.get('memory_total_mb', 0) or 0)
            ps['allocated_memory_mb'] += int(n.get('memory_used_mb', 0) or 0)

        return list(partitions.values())
    except Exception as e:
        print(f"get_partition_info error: {e}")
        return []

@app.route("/api/resources", methods=["GET"])
def get_resources():
    """Get comprehensive cluster resource information using sinfo"""
    raw_node_output = ""
    raw_gpu_output = ""
    try:
        debug_info = {}  # Store command outputs for debugging
        
        # Check if sinfo is available
        sinfo_check = run_command(["which", "sinfo"])
        if "error" in sinfo_check or not sinfo_check:
            print("SLURM sinfo command not found in PATH")
            debug_info["error"] = "sinfo not found in PATH"
            debug_info["path"] = os.environ.get("PATH", "")
            return jsonify({
                "error": "SLURM commands not available",
                "debug": debug_info,
                "total_nodes": 0,
                "allocated_nodes": 0,
                "total_cpus": 0,
                "allocated_cpus": 0,
                "total_memory_mb": 0,
                "allocated_memory_mb": 0,
                "partitions": [],
                "nodes": [],
                "gpu_nodes": {}
            })
    
        # Get node information with detailed CPU, memory, and state
        # -h skips the header line
        node_output = run_command([
            "sinfo",
            "-N",       # Node-oriented view
            "-h",       # Skip header
            "-o",       # Format
            "%N|%t|%C|%m|%e|%P" # name|state|CPUs(A/I/O/T)|memory|free_mem|partition
        ])

        raw_node_output = node_output # Keep raw output for debugging

        if "error" in node_output:
            raise Exception(f"Failed to get node information: {node_output}")
        if not node_output:
            raise Exception("Got empty node information from sinfo")

        nodes = []
        total_cpus = total_allocated_cpus = 0
        total_memory_mb = total_allocated_memory_mb = 0
        partitions = {}

        lines = [line for line in node_output.strip().split("\n") if line.strip()]
        
        # Loop is now correctly inside the try block
        for line in lines:
            parts = line.split("|")
            if len(parts) < 6:
                continue
                
            # Unpack just the first 6 parts, ignoring any extra
            # (like the empty string from a trailing pipe)
            name, state, cpu_field, total_mem_str, free_mem_str, partition = [p.strip() for p in parts[:6]]
            
            # Parse CPU information (format: allocated/idle/other/total)
            cpu_parts = cpu_field.split("/")
            if len(cpu_parts) == 4:
                cpus_allocated = int(cpu_parts[0])
                cpus_idle = int(cpu_parts[1])
                cpus_total = int(cpu_parts[3])
            else:
                cpus_allocated = cpus_idle = cpus_total = 0
                
            # Parse memory values (sinfo reports in MB)
            total_mem_mb = parse_memory_value(total_mem_str)
            free_mem_mb = parse_memory_value(free_mem_str)
            
            # Calculate used memory
            used_mem_mb = 0
            if total_mem_mb > 0:
                # If node is down, free_mem might be 'N/A' (parsed as 0)
                # Only calculate used mem if state is not down/drained
                if not any(s in state for s in ("down", "drain", "fail")):
                    used_mem_mb = total_mem_mb - free_mem_mb
                elif "alloc" in state or "mix" in state:
                    # If it's allocated but free_mem is 0 (e.g., 'N/A'),
                    # we can assume it's fully used.
                    used_mem_mb = total_mem_mb

            # Clamp used memory between 0 and total
            used_mem_mb = max(0, min(used_mem_mb, total_mem_mb))
            
            # Update totals
            total_cpus += cpus_total
            total_allocated_cpus += cpus_allocated
            total_memory_mb += total_mem_mb
            total_allocated_memory_mb += used_mem_mb
            
            # Track partition statistics
            if partition not in partitions:
                partitions[partition] = {
                    "name": partition,
                    "total_nodes": 0,
                    "allocated_nodes": 0,
                    "total_cpus": 0,
                    "allocated_cpus": 0,
                    "total_memory_mb": 0,
                    "allocated_memory_mb": 0
                }
            
            p_stats = partitions[partition]
            p_stats["total_nodes"] += 1
            if state.startswith(("alloc", "mix")):
                p_stats["allocated_nodes"] += 1
            p_stats["total_cpus"] += cpus_total
            p_stats["allocated_cpus"] += cpus_allocated
            p_stats["total_memory_mb"] += total_mem_mb
            p_stats["allocated_memory_mb"] += used_mem_mb
            
            nodes.append({
                "name": name,
                "state": state,
                "partition": partition,
                "cpus_allocated": cpus_allocated,
                "cpus_idle": cpus_idle,
                "cpus_total": cpus_total,
                "memory_total_mb": total_mem_mb,
                "memory_free_mb": free_mem_mb,
                "memory_used_mb": used_mem_mb
            })
    
        # Get GPU information if available
        gpu_nodes = {}
        gpu_output = run_command(["sinfo", "-N", "-h", "-o", "%N|%G"])
        # Assign to raw_gpu_output AFTER the command is run
        raw_gpu_output = gpu_output
        
        if "error" not in gpu_output and gpu_output:
            lines = gpu_output.strip().split("\n")
            if len(lines) > 0:
                for line in lines:
                    parts = line.split("|")
                    if len(parts) == 2:
                        node, gpu = parts[0].strip(), parts[1].strip()
                        if gpu not in ('N/A', '(null)', ''):
                            gpu_nodes[node] = gpu
    
        # Combine all information
        cluster_stats = {
            "total_nodes": len(nodes),
            "allocated_nodes": sum(1 for n in nodes if n["state"].startswith(("alloc", "mix"))),
            "total_cpus": total_cpus,
            "allocated_cpus": total_allocated_cpus,
            "total_memory_mb": total_memory_mb,
            "allocated_memory_mb": total_allocated_memory_mb,
            "partitions": list(partitions.values()),
            "nodes": nodes,
            "gpu_nodes": gpu_nodes
        }
        
        # Attach raw outputs for debugging
        cluster_stats["debug"] = {
            "raw_node_output": raw_node_output,
            "raw_gpu_output": raw_gpu_output
        }
        
        return jsonify(cluster_stats)
    
    # This is the corrected except block
    except Exception as e:
        print(f"Error in get_resources: {str(e)}")
        return jsonify({
            "error": str(e),
            "debug": {
                "raw_node_output": raw_node_output,
                "raw_gpu_output": raw_gpu_output
            },
            "total_nodes": 0,
            "allocated_nodes": 0,
            "total_cpus": 0,
            "allocated_cpus": 0,
            "total_memory_mb": 0,
            "allocated_memory_mb": 0,
            "partitions": [],
            "nodes": [],
            "gpu_nodes": {}
        }), 500
# @app.route("/api/resources", methods=["GET"])
# def get_resources():
#     """Get comprehensive cluster resource information"""
#     try:
#         debug_info = {}  # Store command outputs for debugging
        
#         # Check if sinfo is available
#         sinfo_check = run_command(["which", "sinfo"])
#         if not sinfo_check:
#             print("SLURM sinfo command not found in PATH")
#             debug_info["error"] = "sinfo not found in PATH"
#             debug_info["path"] = os.environ.get("PATH", "")
#             return jsonify({
#                 "error": "SLURM commands not available",
#                 "debug": debug_info,
#                 "total_nodes": 0,
#                 "allocated_nodes": 0,
#                 "total_cpus": 0,
#                 "allocated_cpus": 0,
#                 "total_memory": 0,
#                 "allocated_memory": 0,
#                 "partitions": [],
#                 "nodes": [],
#                 "gpu_nodes": {}
#             })
    
#         # Get node information with detailed CPU, memory, and state
#         node_output = run_command([
#             "sinfo",
#             "-N",
#             "-o",
#             "%N|%t|%C|%m|%e|%P"
#         ])  # name|state|CPUs|memory|free_mem|partition

#         # Keep raw output for debugging (useful inside Docker)
#         raw_node_output = node_output

#         if not node_output or "error" in node_output.lower():
#             raise Exception(f"Failed to get node information: {node_output}")

#         nodes = []
#         total_cpus = total_allocated_cpus = 0
#         total_memory = total_allocated_memory = 0
#         partitions = {}

#         lines = [line for line in node_output.strip().split("\n") if line.strip()]
#         if len(lines) > 1:  # Skip header
#             lines = lines[1:]
#     except Exception as e:
#         print(f"Error in get_resources: {str(e)}")
#         return jsonify({
#             "error": str(e),
#             "total_nodes": 0,
#             "allocated_nodes": 0,
#             "total_cpus": 0,
#             "allocated_cpus": 0,
#             "total_memory": 0,
#             "allocated_memory": 0,
#             "partitions": [],
#             "nodes": [],
#             "gpu_nodes": {}
#         }), 500
            
#         for line in lines:
#             parts = line.split("|")
#             if len(parts) < 6:
#                 continue
                
#             name, state, cpu_field, total_mem, free_mem, partition = [p.strip() for p in parts]
            
#             # Parse CPU information (format: allocated/idle/other/total)
#             cpu_parts = cpu_field.split("/")
#             if len(cpu_parts) == 4:
#                 cpus_allocated = int(cpu_parts[0])
#                 cpus_idle = int(cpu_parts[1])
#                 cpus_total = int(cpu_parts[3])
#             else:
#                 cpus_allocated = cpus_idle = cpus_total = 0
                
#             # Parse memory values
#             total_mem_gb = parse_memory_value(total_mem)
#             free_mem_gb = parse_memory_value(free_mem)
#             used_mem_gb = total_mem_gb - free_mem_gb
            
#             # Update totals
#             total_cpus += cpus_total
#             total_allocated_cpus += cpus_allocated
#             total_memory += total_mem_gb
#             total_allocated_memory += used_mem_gb
            
#             # Track partition statistics
#             if partition not in partitions:
#                 partitions[partition] = {
#                     "name": partition,
#                     "total_nodes": 0,
#                     "allocated_nodes": 0,
#                     "total_cpus": 0,
#                     "allocated_cpus": 0,
#                     "total_memory": 0,
#                     "allocated_memory": 0
#                 }
            
#             p_stats = partitions[partition]
#             p_stats["total_nodes"] += 1
#             if state.startswith(("alloc", "mix")):
#                 p_stats["allocated_nodes"] += 1
#             p_stats["total_cpus"] += cpus_total
#             p_stats["allocated_cpus"] += cpus_allocated
#             p_stats["total_memory"] += total_mem_gb
#             p_stats["allocated_memory"] += used_mem_gb
            
#             nodes.append({
#                 "name": name,
#                 "state": state,
#                 "partition": partition,
#                 "cpus_allocated": cpus_allocated,
#                 "cpus_idle": cpus_idle,
#                 "cpus_total": cpus_total,
#                 "memory_total": total_mem_gb,
#                 "memory_free": free_mem_gb,
#                 "memory_used": used_mem_gb
#             })
    
#     # Get GPU information if available
#     gpu_nodes = {}
#     gpu_output = run_command(["sinfo", "-N", "-o", "%N|%G"]) if 'sinfo' in locals() or True else ''
#     raw_gpu_output = gpu_output
#     if gpu_output:
#         lines = gpu_output.strip().split("\n")
#         if len(lines) > 1:
#             for line in lines[1:]:
#                 parts = line.split("|")
#                 if len(parts) == 2:
#                     node, gpu = parts
#                     if gpu.strip() not in ('N/A', '(null)'):
#                         gpu_nodes[node.strip()] = gpu.strip()
    
#     # Combine all information
#     cluster_stats = {
#         "total_nodes": len(nodes),
#         "allocated_nodes": sum(1 for n in nodes if n["state"].startswith(("alloc", "mix"))),
#         "total_cpus": total_cpus,
#         "allocated_cpus": total_allocated_cpus,
#         "total_memory": total_memory,
#         "allocated_memory": total_allocated_memory,
#         "partitions": list(partitions.values()),
#         "nodes": nodes,
#         "gpu_nodes": gpu_nodes
#     }
#     # Attach raw outputs for debugging in dev environments
#     try:
#         cluster_stats["debug"] = {
#             "raw_node_output": raw_node_output,
#             "raw_gpu_output": raw_gpu_output
#         }
#     except Exception:
#         pass
    
#     return jsonify(cluster_stats)

@app.route("/api/usage", methods=["GET"])
def get_usage():
    """Legacy endpoint that redirects to /api/resources"""
    return get_resources()


@app.route("/api/submit/sbatch", methods=["POST"])
def submit_sbatch():
    # ... (all the setup code from the beginning) ...
    # ... (file.read(), content.replace(), shebang check) ...

    lines = content.splitlines()
    has_any_sbatch = any(line.strip().startswith('#SBATCH') for line in lines)

    # *** FIX: Store the output path pattern here ***
    expected_output_pattern = None 
    output_rewritten = False

    # Case 3: Rewrite existing --output
    for idx, line in enumerate(lines):
        s = line.strip()
        if s.startswith('#SBATCH') and '--output' in s:
            parts = line.split('=', 1)
            if len(parts) == 2:
                out_val = parts[1].strip().strip('"')
                abs_out = os.path.join(user_dir, out_val)
                lines[idx] = f"#SBATCH --output={abs_out}"
                
                # *** FIX: Store the rewritten pattern ***
                expected_output_pattern = abs_out 
                
                output_rewritten = True
                print(f"Rewrote existing --output to absolute path: {lines[idx]}", flush=True)
                break

    # Case 1: No SBATCH directives at all
    if not has_any_sbatch:
        # *** FIX: Store the default .out pattern ***
        expected_output_pattern = os.path.join(user_dir, f'{file.filename}-%j.out')
        
        slurm_directives = [
            '#SBATCH --job-name=default_job',
            f'#SBATCH --output={expected_output_pattern}', # Use the variable
            f'#SBATCH --error={os.path.join(user_dir, file.filename)}-%j.err',
            '#SBATCH --time=01:00:00',
            '#SBATCH --ntasks=1'
        ]
        lines = [lines[0]] + slurm_directives + lines[1:]

    # Case 2: SBATCH directives but no --output
    if has_any_sbatch and not output_rewritten:
        # *** FIX: Store the default .log pattern ***
        expected_output_pattern = os.path.join(user_dir, f'{file.filename}-%j.log')
        
        insert_at = 1
        lines = lines[:insert_at] + [f'#SBATCH --output={expected_output_pattern}'] + lines[insert_at:]

    content = '\n'.join(lines)
    
    # ... (write file, chmod, run sbatch) ...

    output = run_command(cmd, cwd=user_dir, timeout=30)
    print(f"sbatch output: {output}", flush=True)

    job_id = None
    
    # *** FIX: This will hold the *final* file path ***
    final_output_file_path = None 

    if "Submitted batch job" in output:
        try:
            job_id = output.split()[-1]
            print(f"Parsed job ID: {job_id}")

            if expected_output_pattern:
                # *** FIX: Create the final path by replacing %j ***
                final_output_file_path = expected_output_pattern.replace('%j', job_id)
                # Note: This only handles %j. A full solution would
                # also handle %x (job name), %u (user), etc.
                print(f"Expected output file: {final_output_file_path}")
            else:
                print("Error: expected_output_pattern was not set!")

        except Exception as e:
            print(f"Error parsing job ID: {e}")
            pass
    else:
        print("No job ID found in output")

    # ...
    wait_time = 0
    
    # *** FIX: Poll using the correct, final file path ***
    while final_output_file_path and wait_time < 10:
        if os.path.exists(final_output_file_path):
            print(f"Output file found: {final_output_file_path}")
            from flask import send_file
            return send_file(
                final_output_file_path,
                as_attachment=True,
                download_name=os.path.basename(final_output_file_path),
                mimetype='text/plain'
            )
        print(f"Waiting for file: {final_output_file_path} ({wait_time+1}s)")
        time.sleep(1)
        wait_time += 1

    print("File not found after 10s, returning JSON.")
    # If not ready, return job info
    return jsonify({
        "message": "Job submitted",
        "output": output,
        "job_id": job_id,
        # *** FIX: Use the correct variable here too ***
        "output_file": os.path.basename(final_output_file_path) if final_output_file_path else None,
        "user": username
    })


@app.route('/api/job-status/<job_id>', methods=['GET'])
def job_status(job_id):
    """Return job state and whether an output file exists for the given job id."""
    try:
        # First, check squeue for running/pending state
        squeue_out = run_command(["squeue", "-j", str(job_id), "-h", "-o", "%T"], timeout=5)
        state = None
        if squeue_out and "error" not in squeue_out.lower() and squeue_out.strip():
            state = squeue_out.strip()
        else:
            # Fallback to sacct (may not be available on all clusters)
            sacct_out = run_command(["sacct", "-j", str(job_id), "-n", "-o", "State"], timeout=10)
            if sacct_out and "error" not in sacct_out.lower() and sacct_out.strip():
                # sacct can return multiple lines; take the first non-empty
                state = sacct_out.strip().splitlines()[0].strip()
            else:
                state = "UNKNOWN"

        # Look for output file under files/ by scanning for job id in filenames
        files_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files')
        found = None
        for root, dirs, filenames in os.walk(files_root):
            for fn in filenames:
                if f"{job_id}" in fn:
                    found = os.path.join(root, fn)
                    break
            if found:
                break

        return jsonify({
            'job_id': job_id,
            'state': state,
            'output_exists': bool(found and os.path.exists(found)),
            'output_path': os.path.relpath(found, start=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')) if found else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
        # process may be a Popen or a dict {'pid': pid}
        try:
            pid_info = process.pid
        except Exception:
            pid_info = process.get('pid') if isinstance(process, dict) else None
        print(f"Session created: {session_id}, fd={master_fd}, pid={pid_info}")
        
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


@app.route('/debug/sessions', methods=['GET'])
def debug_sessions():
    # Return a lightweight view of current sessions and session->sid mapping
    sessions = {}
    for sid, info in app.terminal_sessions.items():
        proc = info.get('process')
        if isinstance(proc, dict):
            pid = proc.get('pid')
        else:
            pid = getattr(proc, 'pid', None)
        sessions[sid] = {
            'fd': info.get('fd'),
            'pid': pid
        }

    return jsonify({
        'sessions': sessions,
        'session_sids': app.session_sids
    })


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


@socketio.on('terminal_connect')
def handle_terminal_connect(data):
    """Associate a Socket.IO connection with a terminal session_id and start output reader."""
    session_id = data.get('session_id')
    if not session_id:
        emit('terminal_error', {'error': 'No session_id provided'})
        return

    # Store mapping from session_id to Socket.IO sid
    sid = request.sid
    app.session_sids[session_id] = sid
    print(f"Terminal connect: session {session_id} -> sid {sid}")

    # Start a background reader to emit terminal output to this client
    import threading
    reader_thread = threading.Thread(target=read_terminal_output, args=(session_id,), daemon=True)
    reader_thread.start()

    emit('terminal_connected', {'session_id': session_id})

@socketio.on('terminal_input')
def handle_terminal_input(data):
    """Handle input from the frontend terminal"""
    session_id = data.get('session_id')
    input_data = data.get('input')
    
    if not session_id or not input_data:
        return
        
    session = app.terminal_sessions.get(session_id)
    if not session:
        # try to emit to the requesting client if sid provided
        sid = request.sid
        if sid:
            socketio.emit('terminal_error', {'error': 'Session not found'}, to=sid)
        else:
            emit('terminal_error', {'error': 'Session not found'})
        return
        
    try:
        print(f"Received terminal input for session {session_id}: {repr(input_data)}")
        os.write(session['fd'], input_data.encode())
    except Exception as e:
        sid = request.sid
        if sid:
            socketio.emit('terminal_error', {'error': str(e)}, to=sid)
        else:
            emit('terminal_error', {'error': str(e)})

def read_terminal_output(session_id):
    """Read and emit terminal output"""
    session = app.terminal_sessions.get(session_id)
    if not session:
        return
        
    # emit only to the connected websocket client for this session, if known
    sid = app.session_sids.get(session_id)
    proc = session.get('process')
    while True:
        # If the process has exited, notify client and stop
        try:
            # If proc is a Popen, use poll(); if it's a dict from pty.fork, use waitpid with WNOHANG
            if isinstance(proc, dict) and proc.get('pid'):
                pid = proc.get('pid')
                try:
                    waited = os.waitpid(pid, os.WNOHANG)
                    if waited[0] == pid:
                        exit_code = waited[1]
                        print(f"Child pid {pid} exited with status {exit_code}")
                        if sid:
                            socketio.emit('terminal_error', {'error': 'Terminal process exited'}, to=sid)
                        else:
                            socketio.emit('terminal_error', {'error': 'Terminal process exited'})
                        break
                except ChildProcessError:
                    # Already reaped
                    break
            elif hasattr(proc, 'poll'):
                if proc.poll() is not None:
                    exit_code = proc.returncode
                    print(f"Process for session {session_id} exited with code {exit_code}")
                    if sid:
                        socketio.emit('terminal_error', {'error': 'Terminal process exited'}, to=sid)
                    else:
                        socketio.emit('terminal_error', {'error': 'Terminal process exited'})
                    break

            r, _, _ = select.select([session['fd']], [], [], 0.1)
            if session['fd'] in r:
                try:
                    data = os.read(session['fd'], 4096)
                except OSError as e:
                    print(f"OS read error for session {session_id}: {e}")
                    break

                if not data:
                    # No data; loop again and check process
                    continue

                try:
                    text = data.decode(errors='replace')
                except Exception as e:
                    print(f"Decode error for session {session_id}: {e}")
                    text = repr(data)

                payload = {
                    'session_id': session_id,
                    'output': text
                }
                print(f"Emitting terminal output for session {session_id}: {repr(payload['output'])}")
                if sid:
                    socketio.emit('terminal_output', payload, to=sid)
                else:
                    socketio.emit('terminal_output', payload)
        except Exception as e:
            print(f"Unexpected error in read_terminal_output for {session_id}: {e}")
            break

# Initialize terminal sessions storage
app.terminal_sessions = {}
app.session_sids = {}

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
        
        print("\nStarting server on http://0.0.0.0:8001")
        socketio.run(app, host='0.0.0.0', port=8001, debug=True)
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()

