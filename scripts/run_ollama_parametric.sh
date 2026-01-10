#!/bin/bash
#
# Ollama Parametric Benchmark Automation Script
#
# This script automates the complete workflow for running parametric Ollama benchmarks:
# 1. Check for running Ollama service
# 2. Submit parametric benchmark job
# 3. Poll for job completion
# 4. Download results
# 5. Generate analysis plots
# 6. Open plots directory
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "========================================================================"
echo "Ollama Parametric Benchmark Automation"
echo "========================================================================"
echo ""

# Step 1: Check for running Ollama service
echo "[1/6] Checking for running Ollama service..."
SERVICE_OUTPUT=$(python main.py --list-running-services 2>&1)

echo "    DEBUG: Service list output:"
echo "$SERVICE_OUTPUT" | head -5 | sed 's/^/        /'

# Try different patterns to find ollama service
if echo "$SERVICE_OUTPUT" | grep -qi "ollama"; then
    # Try to extract service ID - handle different output formats
    SERVICE_ID=$(echo "$SERVICE_OUTPUT" | grep -i "ollama" | head -1 | sed -E 's/.*service_([a-f0-9]+).*/\1/' | grep -E '^[a-f0-9]+$' || echo "")
    
    if [ -z "$SERVICE_ID" ]; then
        # Alternative: try extracting from patterns like "ID: service_xxxxx" or just the hex ID
        SERVICE_ID=$(echo "$SERVICE_OUTPUT" | grep -i "ollama" | head -1 | grep -oE 'service_[a-f0-9]+|[a-f0-9]{8}' | head -1)
    fi
    
    if [ -n "$SERVICE_ID" ]; then
        echo "    ✓ Found Ollama service: $SERVICE_ID"
    else
        echo "    ⚠  Found Ollama in output but couldn't extract ID"
        SERVICE_ID=""
    fi
fi

if [ -z "$SERVICE_ID" ]; then
    echo "    ✗ No Ollama service found!"
    echo ""
    echo "Starting Ollama service..."
    START_OUTPUT=$(python main.py --recipe recipes/services/ollama_with_cadvisor.yaml 2>&1)
    echo "$START_OUTPUT" | tail -10
    
    echo ""
    echo "    Waiting for service to initialize (60s)..."
    sleep 60
    
    # Get the service ID
    SERVICE_OUTPUT=$(python main.py --list-running-services 2>&1)
    SERVICE_ID=$(echo "$SERVICE_OUTPUT" | grep -i "ollama" | head -1 | sed -E 's/.*service_([a-f0-9]+).*/\1/' | grep -E '^[a-f0-9]+$' || echo "")
    
    if [ -z "$SERVICE_ID" ]; then
        SERVICE_ID=$(echo "$SERVICE_OUTPUT" | grep -i "ollama" | head -1 | grep -oE 'service_[a-f0-9]+|[a-f0-9]{8}' | head -1)
    fi
    
    if [ -z "$SERVICE_ID" ]; then
        echo "    ✗ Failed to get service ID after starting"
        echo "    Service output:"
        echo "$SERVICE_OUTPUT"
        exit 1
    fi
    echo "    ✓ Service started: $SERVICE_ID"
fi

echo ""

# Step 2: Submit parametric benchmark job
echo "[2/6] Submitting parametric benchmark job..."
SUBMIT_OUTPUT=$(python main.py --recipe recipes/clients/ollama_parametric.yaml --target-service "$SERVICE_ID" 2>&1)

if echo "$SUBMIT_OUTPUT" | grep -q "Client started"; then
    CLIENT_ID=$(echo "$SUBMIT_OUTPUT" | grep "Client started" | awk '{print $NF}')
    echo "    ✓ Benchmark job submitted: $CLIENT_ID"
else
    echo "    ✗ Failed to submit benchmark job"
    echo "$SUBMIT_OUTPUT"
    exit 1
fi

echo ""

# Step 3: Wait for job to complete
echo "[3/6] Waiting for benchmark to complete..."
echo "    This may take 1-2 hours depending on parameter ranges"
echo ""

POLL_INTERVAL=60  # Check every 60 seconds
MAX_WAIT=10800   # 3 hours max
ELAPSED=0
FIRST_CHECK=true

while [ $ELAPSED -lt $MAX_WAIT ]; do
    # Get all job statuses
    STATUS_OUTPUT=$(python main.py --status 2>&1)
    
    # Show full output on first check for debugging
    if [ "$FIRST_CHECK" = true ]; then
        echo "    DEBUG: Status output:"
        echo "$STATUS_OUTPUT" | grep -A 20 "SLURM Job Status:" | sed 's/^/        /'
        FIRST_CHECK=false
    fi
    
    # Look for our client job by ID pattern: ollama_parametric_benchmark_<CLIENT_ID>
    CLIENT_LINE=$(echo "$STATUS_OUTPUT" | grep "ollama_parametric_benchmark_${CLIENT_ID}" || echo "")
    
    if [ -z "$CLIENT_LINE" ]; then
        echo "    ⚠  Client job not found in status - may have completed and been cleaned up"
        echo "    Proceeding to download results..."
        break
    fi
    
    # Extract the status from the line (format: job_id | name | STATUS | time | node)
    JOB_STATUS=$(echo "$CLIENT_LINE" | awk -F'|' '{print $3}' | xargs)
    
    # Check job status
    if echo "$JOB_STATUS" | grep -qiE "(COMPLETED|DONE)"; then
        echo "    ✓ Benchmark completed successfully!"
        echo "    Final status: $CLIENT_LINE"
        break
    elif echo "$JOB_STATUS" | grep -qiE "(FAILED|CANCELLED|TIMEOUT|NODE_FAIL)"; then
        echo "    ✗ Benchmark failed!"
        echo "    Status: $CLIENT_LINE"
        exit 1
    elif echo "$JOB_STATUS" | grep -qiE "(RUNNING|PENDING|CONFIGURING)"; then
        ELAPSED=$((ELAPSED + POLL_INTERVAL))
        MINUTES=$((ELAPSED / 60))
        # Extract runtime from the line
        RUNTIME=$(echo "$CLIENT_LINE" | awk -F'|' '{print $4}' | xargs)
        echo "    ⏱  Still running... ($MINUTES min elapsed, job runtime: $RUNTIME)"
        sleep $POLL_INTERVAL
    else
        # Unknown status - show it and continue
        ELAPSED=$((ELAPSED + POLL_INTERVAL))
        MINUTES=$((ELAPSED / 60))
        echo "    ⚠  Status unclear ($MINUTES min): $CLIENT_LINE"
        sleep $POLL_INTERVAL
    fi
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo "    ✗ Timeout waiting for benchmark to complete"
    echo "    Last status: $CLIENT_LINE"
    exit 1
fi

echo ""

# Step 4: Download results
echo "[4/6] Downloading benchmark results..."
mkdir -p results

# Try to download results
RESULTS_FILE="results/ollama_parametric_${CLIENT_ID}.json"

# Use the get-results command if available
DOWNLOAD_OUTPUT=$(python main.py --get-results "$CLIENT_ID" --output "$RESULTS_FILE" 2>&1 || echo "")

if [ -f "$RESULTS_FILE" ]; then
    echo "    ✓ Results downloaded: $RESULTS_FILE"
    FILE_SIZE=$(du -h "$RESULTS_FILE" | cut -f1)
    echo "    File size: $FILE_SIZE"
else
    echo "    ⚠  Could not download results automatically"
    # echo "    Please manually retrieve: ollama_parametric_*.json from \$SCRATCH"
    # echo ""
    # read -p "Enter path to results file (or press Enter to skip): " MANUAL_PATH
    
    # if [ -n "$MANUAL_PATH" ] && [ -f "$MANUAL_PATH" ]; then
    #     cp "$MANUAL_PATH" "$RESULTS_FILE"
    #     echo "    ✓ Results copied: $RESULTS_FILE"
    # else
        echo "    ⚠  Skipping result download"
        echo "    You can analyze results later with:"
        echo "        python analysis/plot_ollama_results.py --results-dir <path>"
        exit 0
    fi
fi

echo ""

# Step 5: Generate analysis plots
echo "[5/6] Generating analysis plots..."

if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
else
    PYTHON_CMD=python
fi

# Check for required packages
$PYTHON_CMD -c "import matplotlib, numpy" 2>/dev/null || {
    echo "    ⚠  Installing required packages (matplotlib, numpy)..."
    $PYTHON_CMD -m pip install --quiet matplotlib numpy
}

# Run analysis
PLOT_OUTPUT=$(cd "$PROJECT_ROOT" && $PYTHON_CMD analysis/plot_ollama_results.py --results-dir results 2>&1)

if echo "$PLOT_OUTPUT" | grep -q "Analysis complete"; then
    echo "    ✓ Plots generated successfully!"
    echo ""
    echo "$PLOT_OUTPUT" | grep "✓ Saved:" | sed 's/^/        /'
else
    echo "    ⚠  Plot generation encountered issues:"
    echo "$PLOT_OUTPUT"
fi

echo ""

# Step 6: Open plots directory
echo "[6/6] Opening plots directory..."
PLOTS_DIR="$PROJECT_ROOT/analysis/plotsOllama"

if [ -d "$PLOTS_DIR" ]; then
    PLOT_COUNT=$(find "$PLOTS_DIR" -name "*.png" -type f | wc -l)
    echo "    ✓ Found $PLOT_COUNT plot(s) in: $PLOTS_DIR"
    
    # Try to open the directory (OS-specific)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "$PLOTS_DIR"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v xdg-open &> /dev/null; then
            xdg-open "$PLOTS_DIR" 2>/dev/null || echo "    (Could not auto-open directory)"
        fi
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        explorer "$PLOTS_DIR"
    fi
else
    echo "    ⚠  Plots directory not found: $PLOTS_DIR"
fi

echo ""
echo "========================================================================"
echo "Benchmark Complete!"
echo "========================================================================"
echo ""
echo "Results file:  $RESULTS_FILE"
echo "Plots directory: $PLOTS_DIR"
echo ""
echo "You can re-run the analysis with:"
echo "    python analysis/plot_ollama_results.py --results-dir results"
echo ""
