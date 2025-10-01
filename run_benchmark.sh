#!/bin/bash -l
#SBATCH -J AI_Benchmark
#SBATCH --time=00:15:00
#SBATCH --account=p200981
#SBATCH --partition=cpu
#SBATCH --qos=default
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1

module load Apptainer/1.2.4-GCCcore-12.3.0

# Container ausführen
srun apptainer run ai-benchmark.sif run_inference
