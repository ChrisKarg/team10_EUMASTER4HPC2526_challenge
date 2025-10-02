#!/bin/bash -l
## This file is called `MyFirstJob_MeluXina.sh`
#SBATCH --time=00:15:00
#SBATCH --account=p200981
#SBATCH --partition=cpu
#SBATCH --qos=default
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1

echo 'Hello, world!'