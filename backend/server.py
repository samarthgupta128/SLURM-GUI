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

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5173", "http://localhost:8001"],
        "methods": ["GET", "POST", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"]
    }
})
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:5173", "http://localhost:8001"])


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
def get_partition_info():
    """Get detailed partition information using scontrol"""
    try:
        output = subprocess.run(["scontrol", "show", "partition", "-o"])
        partitions = []
        
        if output:
            for line in output.strip().split('\n'):
                parts = dict(item.split('=', 1) for item in line.split() if '=' in item)
                partition = {
                    'name': parts.get('PartitionName', 'unknown'),
                    'nodes': parts.get('Nodes', ''),
                    'state': parts.get('State', 'unknown'),
                    'max_time': parts.get('MaxTime', 'infinite'),
                    'default': parts.get('Default', 'NO') == 'YES',
                    'total_nodes': int(parts.get('TotalNodes', '0')),
                    'available_nodes': int(parts.get('AvailableNodes', '0')),
                    'allocated_nodes': 0  # Will be calculated from node info
                }
                
                # Get detailed node information for this partition
                node_output = run_command(["sinfo", "-p", partition['name'], "-o", "%n %C %m"])
                if node_output:
                    lines = node_output.strip().split('\n')[1:]  # Skip header
                    total_cpus = allocated_cpus = total_mem = 0
                    for node_line in lines:
                        if not node_line.strip():
                            continue
                        node_parts = node_line.split()
                        if len(node_parts) >= 3:
                            cpu_info = node_parts[1].split('/')
                            if len(cpu_info) == 4:
                                allocated_cpus += int(cpu_info[0])
                                total_cpus += int(cpu_info[3])
                            mem = parse_memory_value(node_parts[2])
                            total_mem += mem
                    
                    partition['total_cpus'] = total_cpus
                    partition['allocated_cpus'] = allocated_cpus
                    partition['total_memory'] = total_mem
                
                partitions.append(partition)

        print(f"Retrieved partition info: {partitions}")  # Debug log
        return partitions
    except Exception as e:
        print(f"Error getting partition info: {e}")
        return []
@app.route("/api/partitions", methods=["GET"])
def get_partitions():
    """Get partition information"""
    try:
        # Get basic partition info
        output = run_command(["scontrol", "show", "partition", "-o"], capture_output=True, text=True, check=True)
        if not output:
            raise Exception("No output from scontrol command")

        partitions = []
        for line in output.strip().split('\n'):
            parts = dict(item.split('=', 1) for item in line.split() if '=' in item)
            
            # Get node information for this partition
            node_output = run_command([
                "sinfo", 
                "-p", parts.get('PartitionName', ''), 
                "-h", 
                "-o", "%D %C %m"
            ])
            
            node_info = node_output.strip().split()
            if len(node_info) >= 3:
                total_nodes = int(node_info[0])
                cpu_info = node_info[1].split('/')
                mem_info = parse_memory_value(node_info[2])
            else:
                total_nodes = 0
                cpu_info = ['0', '0', '0', '0']
                mem_info = 0

            partition = {
                'name': parts.get('PartitionName', 'unknown'),
                'state': parts.get('State', 'unknown'),
                'max_time': parts.get('MaxTime', 'infinite'),
                'nodes': parts.get('Nodes', ''),
                'default': parts.get('Default', 'NO') == 'YES',
                'total_nodes': total_nodes,
                'allocated_cpus': int(cpu_info[0]),
                'total_cpus': int(cpu_info[3]),
                'memory': mem_info,
                'available_nodes': int(parts.get('AvailableNodes', '0')),
                'max_nodes_per_job': int(parts.get('MaxNodes', '0'))
            }
            partitions.append(partition)

        print(f"Retrieved {len(partitions)} partitions")
        return jsonify({
            "partitions": partitions,
            "total_partitions": len(partitions),
            "default_partition": next((p for p in partitions if p['default']), None)
        })

    except Exception as e:
        print(f"Error getting partitions: {e}")
        return jsonify({
            "error": str(e),
            "partitions": [],
            "total_partitions": 0,
            "default_partition": None
        }), 500
def get_sinfo_data():
    cmd = ['sinfo','-o', '%P %t %C %m %l']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        nodes_data=[]
        lines = result.stdout.strip().split("\n")[1:]
        total_nodes = 0
        idle_nodes = 0
        alloc_nodes = 0
        total_cpus = 0
        cpus_in_use = 0
        total_mem_gb = 0
        mem_in_use_gb = 0
        for line in lines:
            parts = line.split()
            if len(parts) < 5 : continue
            partition, state, cpus_str, mem_mb, alloc_mem_mb = parts            
            cpu_parts = cpus_str.split('/')
            alloc_cpu = int(cpu_parts[0])
            idle_cpu = int(cpu_parts[1])
            total_cpu_node = int(cpu_parts[3])

            total_nodes += 1 # This is tricky, sinfo groups nodes.
                             # A better command is 'scontrol show node'
            total_cpus += total_cpu_node
            cpus_in_use += alloc_cpu
            
            total_mem_gb += int(mem_mb) / 1024
            mem_in_use_gb += int(alloc_mem_mb) / 1024
            
            if state == 'idle':
                idle_nodes += 1 # Again, simplified
            elif state in ['alloc', 'mix']:
                alloc_nodes += 1

        cpu_percent = (cpus_in_use / total_cpus * 100) if total_cpus > 0 else 0
        mem_percent = (mem_in_use_gb / total_mem_gb * 100) if total_mem_gb > 0 else 0
        return {
            "totalNodes": total_nodes, # Fix this by parsing 'scontrol show node'
                "allocNodes": alloc_nodes,
                "idleNodes": idle_nodes,
                "cpuUtilization": cpu_percent,
                "cpusInUse": cpus_in_use,
                "totalCpus": total_cpus,
                "memoryUsage": mem_percent,
                "memInUseGB": round(mem_in_use_gb, 2),
                "totalMemGB": round(total_mem_gb, 2)
            }
    except Exception as e:
        print(f"Error parsing sinfo: {e}")
        return {"error": str(e)} # Send error to frontend


    
# def get_partition_info():
#     """Get detailed partition information using scontrol"""
#     output = run_command(["scontrol", "show", "partition", "-o"])
#     partitions = []
    
#     if output:
#         for line in output.strip().split('\n'):
#             parts = dict(item.split('=', 1) for item in line.split() if '=' in item)
#             partition = {
#                 'name': parts.get('PartitionName', 'unknown'),
#                 'nodes': parts.get('Nodes', ''),
#                 'state': parts.get('State', 'unknown'),
#                 'max_time': parts.get('MaxTime', 'infinite'),
#                 'default': parts.get('Default', 'NO') == 'YES',
#                 'total_nodes': int(parts.get('TotalNodes', '0')),
#                 'available_nodes': int(parts.get('AvailableNodes', '0')),
#                 'allocated_nodes': 0,  # Will be calculated from node info
#                 'total_cpus': 0,      # Will be calculated from node info
#                 'allocated_cpus': 0,   # Will be calculated from node info
#                 'total_memory': 0,     # Will be calculated from node info
#                 'allocated_memory': 0   # Will be calculated from node info
#             }
#             partitions.append(partition)
#     return partitions

# def get_node_info():
#     """Get detailed node information using scontrol"""
#     output = run_command(["scontrol", "show", "node", "-o"])
#     nodes = []
    
#     if output:
#         for line in output.strip().split('\n'):
#             parts = dict(item.split('=', 1) for item in line.split() if '=' in item)
            
#             # Parse CPU information
#             cpus_total = int(parts.get('CPUTot', '0'))
#             cpus_allocated = int(parts.get('CPUAlloc', '0'))
            
#             # Parse memory information (convert to GB)
#             memory_total = int(parts.get('RealMemory', '0')) // 1024  # Convert MB to GB
#             memory_allocated = int(parts.get('AllocMem', '0')) // 1024
            
#             # Parse GPU information if available
#             gres = parts.get('Gres', '')
#             gpus = None
#             if 'gpu:' in gres.lower():
#                 gpu_info = [g for g in gres.split(',') if 'gpu' in g.lower()]
#                 if gpu_info:
#                     gpus = gpu_info[0]
            
#             node = {
#                 'name': parts.get('NodeName', 'unknown'),
#                 'state': parts.get('State', 'unknown'),
#                 'partition': parts.get('Partitions', 'unknown'),
#                 'cpus_total': cpus_total,
#                 'cpus_allocated': cpus_allocated,
#                 'cpus_idle': cpus_total - cpus_allocated,
#                 'memory_total': memory_total,
#                 'memory_allocated': memory_allocated,
#                 'memory_free': memory_total - memory_allocated,
#                 'gpus': gpus,
#                 'features': parts.get('AvailableFeatures', ''),
#                 'active_features': parts.get('ActiveFeatures', ''),
#                 'load': parts.get('CPULoad', '0.00')
#             }
#             nodes.append(node)
#     return nodes

@app.route("/api/resources", methods=["GET"])
def get_resources():
    """Get comprehensive cluster resource information"""
    try:
        # Check if SLURM commands are available
        for cmd in ['sinfo', 'scontrol']:
            if not run_command(['which', cmd]):
                return jsonify({
                    "error": f"SLURM command '{cmd}' not found in PATH. Please ensure SLURM client tools are installed.",
                    "total_nodes": 0,
                    "allocated_nodes": 0,
                    "total_cpus": 0,
                    "allocated_cpus": 0,
                    "total_memory": 0,
                    "allocated_memory": 0,
                    "partitions": [],
                    "nodes": [],
                    "gpu_nodes": {}
                })

        # Get partition and node information
        partitions = get_partition_info()
        nodes = get_node_info()
        
        # Initialize totals
        total_cpus = total_allocated_cpus = 0
        total_memory = total_allocated_memory = 0
        gpu_nodes = {}
        
        # Create partition lookup for faster processing
        partition_lookup = {p['name']: p for p in partitions}
        
        # Process node information and update partition stats
        for node in nodes:
            # Update global totals
            total_cpus += node['cpus_total']
            total_allocated_cpus += node['cpus_allocated']
            total_memory += node['memory_total']
            total_allocated_memory += node['memory_allocated']
            
            # Track GPU nodes
            if node['gpus']:
                gpu_nodes[node['name']] = node['gpus']
            
            # Update partition statistics
            for partition_name in node['partition'].split(','):
                if partition_name in partition_lookup:
                    p = partition_lookup[partition_name]
                    p['allocated_nodes'] += 1 if node['cpus_allocated'] > 0 else 0
                    p['total_cpus'] += node['cpus_total']
                    p['allocated_cpus'] += node['cpus_allocated']
                    p['total_memory'] += node['memory_total']
                    p['allocated_memory'] += node['memory_allocated']
        
        # Return comprehensive cluster information
        return jsonify({
            "total_nodes": len(nodes),
            "allocated_nodes": sum(1 for n in nodes if n['cpus_allocated'] > 0),
            "total_cpus": total_cpus,
            "allocated_cpus": total_allocated_cpus,
            "total_memory": total_memory,
            "allocated_memory": total_allocated_memory,
            "partitions": [p for p in partitions if p['total_nodes'] > 0],  # Only return active partitions
            "nodes": nodes,
            "gpu_nodes": gpu_nodes,
            "cluster_load": sum(float(n['load']) for n in nodes) / len(nodes) if nodes else 0.0
        })
    except Exception as e:
        print(f"Error in get_resources: {str(e)}")
        return jsonify({
            "error": str(e),
            "total_nodes": 0,
            "allocated_nodes": 0,
            "total_cpus": 0,
            "allocated_cpus": 0,
            "total_memory": 0,
            "allocated_memory": 0,
            "partitions": [],
            "nodes": [],
            "gpu_nodes": {}
        }), 500        # Return comprehensive cluster information
        return jsonify({
            "total_nodes": len(nodes),
            "allocated_nodes": sum(1 for n in nodes if n['cpus_allocated'] > 0),
            "total_cpus": total_cpus,
            "allocated_cpus": total_allocated_cpus,
            "total_memory": total_memory,
            "allocated_memory": total_allocated_memory,
            "partitions": [p for p in partitions if p['total_nodes'] > 0],  # Only return active partitions
            "nodes": nodes,
            "gpu_nodes": gpu_nodes,
            "cluster_load": sum(float(n['load']) for n in nodes) / len(nodes) if nodes else 0.0
        })        # Get node information with detailed CPU, memory, and state
        node_output = run_command([
            "sinfo",
            "-N",
            "-o",
            "%N|%t|%C|%m|%e|%P"
        ])  # name|state|CPUs|memory|free_mem|partition

        # Keep raw output for debugging (useful inside Docker)
        raw_node_output = node_output

        if not node_output or "error" in node_output.lower():
            raise Exception(f"Failed to get node information: {node_output}")

        # Get partition and node information
        partitions = get_partition_info()
        nodes = get_node_info()
        
        # Initialize totals
        total_cpus = total_allocated_cpus = 0
        total_memory = total_allocated_memory = 0
        gpu_nodes = {}
        
        # Create partition lookup for faster processing
        partition_lookup = {p['name']: p for p in partitions}
        
        # Process node information and update partition stats
        for node in nodes:
            # Update global totals
            total_cpus += node['cpus_total']
            total_allocated_cpus += node['cpus_allocated']
            total_memory += node['memory_total']
            total_allocated_memory += node['memory_allocated']
            
            # Track GPU nodes
            if node['gpus']:
                gpu_nodes[node['name']] = node['gpus']
            
            # Update partition statistics
            for partition_name in node['partition'].split(','):
                if partition_name in partition_lookup:
                    p = partition_lookup[partition_name]
                    p['allocated_nodes'] += 1 if node['cpus_allocated'] > 0 else 0
                    p['total_cpus'] += node['cpus_total']
                    p['allocated_cpus'] += node['cpus_allocated']
                    p['total_memory'] += node['memory_total']
                    p['allocated_memory'] += node['memory_allocated']

        lines = [line for line in node_output.strip().split("\n") if line.strip()]
        if len(lines) > 1:  # Skip header
            lines = lines[1:]
    except Exception as e:
        print(f"Error in get_resources: {str(e)}")
        return jsonify({
            "error": str(e),
            "total_nodes": 0,
            "allocated_nodes": 0,
            "total_cpus": 0,
            "allocated_cpus": 0,
            "total_memory": 0,
            "allocated_memory": 0,
            "partitions": [],
            "nodes": [],
            "gpu_nodes": {}
        }), 500
            
    for line in lines:
        parts = line.split("|")
        if len(parts) < 6:
            continue
            
        name, state, cpu_field, total_mem, free_mem, partition = [p.strip() for p in parts]
        
        # Parse CPU information (format: allocated/idle/other/total)
        cpu_parts = cpu_field.split("/")
        if len(cpu_parts) == 4:
            cpus_allocated = int(cpu_parts[0])
            cpus_idle = int(cpu_parts[1])
            cpus_total = int(cpu_parts[3])
        else:
            cpus_allocated = cpus_idle = cpus_total = 0
            
        # Parse memory values
        total_mem_gb = parse_memory_value(total_mem)
        free_mem_gb = parse_memory_value(free_mem)
        used_mem_gb = total_mem_gb - free_mem_gb
        
        # Update totals
        total_cpus += cpus_total
        total_allocated_cpus += cpus_allocated
        total_memory += total_mem_gb
        total_allocated_memory += used_mem_gb
        
        # Track partition statistics
        if partition not in partitions:
            partitions[partition] = {
                "name": partition,
                "total_nodes": 0,
                "allocated_nodes": 0,
                "total_cpus": 0,
                "allocated_cpus": 0,
                "total_memory": 0,
                "allocated_memory": 0
            }
        
        p_stats = partitions[partition]
        p_stats["total_nodes"] += 1
        if state.startswith(("alloc", "mix")):
            p_stats["allocated_nodes"] += 1
        p_stats["total_cpus"] += cpus_total
        p_stats["allocated_cpus"] += cpus_allocated
        p_stats["total_memory"] += total_mem_gb
        p_stats["allocated_memory"] += used_mem_gb
        
        nodes.append({
            "name": name,
            "state": state,
            "partition": partition,
            "cpus_allocated": cpus_allocated,
            "cpus_idle": cpus_idle,
            "cpus_total": cpus_total,
            "memory_total": total_mem_gb,
            "memory_free": free_mem_gb,
            "memory_used": used_mem_gb
        })
    
    # Get GPU information if available
    gpu_nodes = {}
    gpu_output = run_command(["sinfo", "-N", "-o", "%N|%G"]) if 'sinfo' in locals() or True else ''
    raw_gpu_output = gpu_output
    if gpu_output:
        lines = gpu_output.strip().split("\n")
        if len(lines) > 1:
            for line in lines[1:]:
                parts = line.split("|")
                if len(parts) == 2:
                    node, gpu = parts
                    if gpu.strip() not in ('N/A', '(null)'):
                        gpu_nodes[node.strip()] = gpu.strip()
    
    # Combine all information
    cluster_stats = {
        "total_nodes": len(nodes),
        "allocated_nodes": sum(1 for n in nodes if n["state"].startswith(("alloc", "mix"))),
        "total_cpus": total_cpus,
        "allocated_cpus": total_allocated_cpus,
        "total_memory": total_memory,
        "allocated_memory": total_allocated_memory,
        "partitions": list(partitions.values()),
        "nodes": nodes,
        "gpu_nodes": gpu_nodes
    }
    # Attach raw outputs for debugging in dev environments
    try:
        cluster_stats["debug"] = {
            "raw_node_output": raw_node_output,
            "raw_gpu_output": raw_gpu_output
        }
    except Exception:
        pass
    
    return jsonify(cluster_stats)

@app.route("/api/usage", methods=["GET"])
def get_usage():
    """Legacy endpoint that redirects to /api/resources"""
    return get_resources()


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

