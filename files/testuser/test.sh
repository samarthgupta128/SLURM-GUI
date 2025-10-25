#!/bin/bash
#SBATCH --job-name=default_job
#SBATCH --output=test.sh-%j.out
#SBATCH --error=test.sh-%j.err
#SBATCH --time=01:00:00
#SBATCH --ntasks=1
# This script has no SBATCH directives

echo "Hello from Slurm!"
echo "This is job $SLURM_JOB_ID"
echo "Running on node $(hostname)"
sleep 3 # Do a tiny bit of work
echo "Job finished."
