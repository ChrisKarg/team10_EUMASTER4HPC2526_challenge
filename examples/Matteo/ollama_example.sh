#!/bin/bash -l
#SBATCH --time=01:00:00
#SBATCH --qos=default
#SBATCH --partition=gpu
#SBATCH --account=p200981
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1

module add Apptainer

# Set environment to skip TLS verification
export OLLAMA_TLS_SKIP_VERIFY=1

# Start ollama in background
apptainer exec --nv --env OLLAMA_TLS_SKIP_VERIFY=1 ollama_latest.sif ollama serve &
sleep 10

# Pull and run a model
apptainer exec --nv --env OLLAMA_TLS_SKIP_VERIFY=1 ollama_latest.sif ollama pull llama2
apptainer exec --nv --env OLLAMA_TLS_SKIP_VERIFY=1 ollama_latest.sif ollama run llama2 "Hello, how are you?"