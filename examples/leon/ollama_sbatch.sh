#!/bin/bash -l
## This file is called 'ollama_sbatch.sh'

#SBATCH --time=00:05:00
#SBATCH --qos=default
#SBATCH --partition=gpu
#SBATCH --account=p200981
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1


echo "Date 		= $(date)"
echo "Hostname 		= $(hostname -s)"
echo "Working Directory = $(pwd)"

# Load the env
module load Apptainer

# Run the processing
apptainer pull docker://ollama/ollama
apptainer exec --nv ollama_latest.sif ollama serve
