#!/bin/bash

#================================================================
# SLURM SCRIPT
#================================================================

# --- Job Configuration ---

#SBATCH --job-name=my_log_job         # Name for your job
#SBATCH --output=my_job_log_%j.log    # Log file for STDOUT and STDERR
                                      # %j will be replaced with the job ID

# --- Resource Allocation ---
#   (Adjust these to your needs)

#SBATCH --ntasks=1                    # Number of tasks (processes)
#SBATCH --cpus-per-task=1             # Number of CPU cores per task
#SBATCH --mem=1G                      # Memory per node (e.g., 1 gigabyte)
#SBATCH --time=00:05:00               # Time limit (hh:mm:ss)

#================================================================
# YOUR COMMANDS GO BELOW
#================================================================

echo "------------------------------------------------"
echo "Job Started: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "Host: $(hostname)"
echo "------------------------------------------------"
echo ""

# This line will be written to the log file
echo "This is a message to standard output (STDOUT)."

# This line will also be written to the *same* log file
echo "This is a message to standard error (STDERR)." >&2

echo ""
echo "Simulating some work for 10 seconds..."
sleep 10

echo ""
echo "------------------------------------------------"
echo "Job Finished: $(date)"
echo "------------------------------------------------"