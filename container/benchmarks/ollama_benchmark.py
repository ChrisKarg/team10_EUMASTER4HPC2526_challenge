# ollama_benchmark.py
import subprocess
import time

# ============================================
# Ollama Benchmark
# ============================================

OLLAMA_CONTAINER = "/opt/benchmarks/ollama_latest.sif"  # path to your Ollama SIF
PROMPT = "Write a short poem about AI benchmarking."

def run_ollama_query(prompt):
    """
    Run a query in the Ollama container using Apptainer.
    Returns the container output as string.
    """
    cmd = [
        "apptainer",
        "exec",
        OLLAMA_CONTAINER,
        "ollama",
        "query",
        prompt
    ]
    try:
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        end = time.time()
        print(f"Query executed in {end - start:.2f} seconds")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print("Error running Ollama container:", e.stderr)
        return None

if __name__ == "__main__":
    print("Running Ollama benchmark...")
    response = run_ollama_query(PROMPT)
    if response:
        print("Ollama response:")
        print(response)
