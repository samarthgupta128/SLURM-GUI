#!/bin/bash

#=======================================================================
#          CORRECTED SLURM SUBMISSION SCRIPT (Single-Node Job)
#=======================================================================

#-----------------------------------------------------------------------
#                SBATCH DIRECTIVES (CONFIGURING YOUR JOB)
#-----------------------------------------------------------------------

# -- Job Details --
# CORRECTED: The line below now uses the valid "--job-name" directive.
#SBATCH --job-name=test_job                # Name for your job, shows up in the queue
#SBATCH --output=job_output_%j.out         # File to save standard output (%j is the job ID)
#SBATCH --error=job_error_%j.err           # File to save standard error

# -- Resource Allocation --
#SBATCH --nodes=1                          # Request exactly one node
#SBATCH --ntasks=1                         # Run a single task on that node
#SBATCH --cpus-per-task=8                  # Request 8 CPU cores for the task
#SBATCH --mem=16G                          # Request 16 Gigabytes of RAM for the job

# -- Time & Partition --
#SBATCH --time=04:00:00                    # Job will be killed after 4 hours
#SBATCH --partition=debug    # IMPORTANT: You MUST change this to a valid partition

# -- (Optional) Email Notifications --
#SBATCH --mail-type=ALL
#SBATCH --mail-user=samarthgupta128@gmail.com # Change this to your email address

#=======================================================================
#                    YOUR ACTUAL COMMANDS TO RUN
#=======================================================================

# Print some useful information to the output file for logging
echo "SLURM JOB: $SLURM_JOB_NAME ($SLURM_JOB_ID)"
echo "Running on host: $(hostname)"
echo "Job started at: $(date)"
echo "Using $SLURM_CPUS_PER_TASK CPU cores."
echo "------------------------------------------------------"

# Navigate to the directory where you submitted the job
cd $SLURM_SUBMIT_DIR

# --- Place your commands below this line ---

# This is a simple command to test if the script works.
# It will run for 30 seconds and then print a success message.
echo "Starting the main task..."
sleep 30
echo "Task completed successfully."


# --- End of your commands ---

echo "------------------------------------------------------"
echo "Job finished at: $(date)"
