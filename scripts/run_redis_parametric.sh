#!/bin/bash
#
# Redis Parametric Benchmark Automation Script
#
# This script automates the complete workflow for running parametric Redis benchmarks:
# 1. Check for running Redis service
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
echo "Redis Parametric Benchmark Automation"
echo "========================================================================"
echo ""

# Step 1: Check for running Redis service
echo "[1/6] Checking for running Redis service..."
SERVICE_OUTPUT=$(python main.py --list-running-services 2>/dev/null || echo "")

if echo "$SERVICE_OUTPUT" | grep -q "redis"; then
    # Extract service ID
    SERVICE_ID=$(echo "$SERVICE_OUTPUT" | grep "redis" | head -1 | awk '{print $2}')
    echo "    ✓ Found Redis service: $SERVICE_ID"
else
    echo "    ✗ No Redis service found!"
    echo ""
    echo "Please start a Redis service first:"
    echo "    python main.py --recipe recipes/services/redis.yaml"
    echo ""
    read -p "Would you like to start Redis now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "    Starting Redis service..."
        python main.py --recipe recipes/services/redis.yaml
        echo ""
        echo "    Waiting for service to initialize (30s)..."
        sleep 30
        
        # Get the service ID
        SERVICE_OUTPUT=$(python main.py --list-running-services 2>/dev/null || echo "")
        SERVICE_ID=$(echo "$SERVICE_OUTPUT" | grep "redis" | head -1 | awk '{print $2}')
        
        if [ -z "$SERVICE_ID" ]; then
            echo "    ✗ Failed to get service ID"
            exit 1
        fi
        echo "    ✓ Service started: $SERVICE_ID"
    else
        echo "Exiting."
        exit 1
    fi
fi

echo ""

# Step 2: Submit parametric benchmark job
echo "[2/6] Submitting parametric benchmark job..."
SUBMIT_OUTPUT=$(python main.py --recipe recipes/clients/redis_parametric.yaml --target-service "$SERVICE_ID" 2>&1)

if echo "$SUBMIT_OUTPUT" | grep -q "Client started"; then
    CLIENT_ID=$(echo "$SUBMIT_OUTPUT" | grep "Client started" | awk '{print $NF}')
    echo "    ✓ Benchmark job submitted: $CLIENT_ID"
else
    echo "    ✗ Failed to submit benchmark job"
    echo "$SUBMIT_OUTPUT"
    exit 1
fi

echo ""

# Step 3: Poll for job completion
echo "[3/6] Waiting for benchmark to complete..."
echo "    This may take 1-4 hours depending on parameter ranges."
echo "    You can monitor progress with: python main.py --status"
echo ""

POLL_INTERVAL=60  # Check every 60 seconds
ELAPSED=0

while true; do
    STATUS_OUTPUT=$(python main.py --status 2>/dev/null || echo "")
    
    # Check if job is completed or failed
    if echo "$STATUS_OUTPUT" | grep "$CLIENT_ID" | grep -q "COMPLETED"; then
        echo "    ✓ Benchmark completed!"
        break
    elif echo "$STATUS_OUTPUT" | grep "$CLIENT_ID" | grep -q "FAILED\|CANCELLED\|TIMEOUT"; then
        echo "    ✗ Benchmark job failed or was cancelled"
        exit 1
    elif ! echo "$STATUS_OUTPUT" | grep -q "$CLIENT_ID"; then
        # Job not found (might have been cleaned up if completed)
        echo "    ✓ Job no longer in queue (likely completed)"
        break
    fi
    
    # Still running
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
    MINUTES=$((ELAPSED / 60))
    echo "    ⏳ Still running... (${MINUTES} minutes elapsed)"
    sleep $POLL_INTERVAL
done

echo ""

# Step 4: Download results
echo "[4/6] Downloading results from cluster..."
DOWNLOAD_OUTPUT=$(python main.py --download-results 2>&1)

if echo "$DOWNLOAD_OUTPUT" | grep -q "Downloaded"; then
    NUM_FILES=$(echo "$DOWNLOAD_OUTPUT" | grep "Downloaded" | grep -oP '\d+' | head -1)
    echo "    ✓ Downloaded $NUM_FILES result file(s)"
else
    echo "    ⚠️  Warning: No new results downloaded"
    echo "    (Results may have been downloaded previously)"
fi

echo ""

# Step 5: Generate plots
echo "[5/6] Generating analysis plots..."

# Check for required Python packages
if ! python -c "import matplotlib; import numpy" 2>/dev/null; then
    echo "    ⚠️  matplotlib or numpy not installed"
    echo "    Installing dependencies..."
    pip install -q matplotlib numpy
fi

# Run plotting script
if python analysis/plot_redis_results.py; then
    echo "    ✓ Plots generated successfully"
else
    echo "    ✗ Failed to generate plots"
    echo "    You can manually run: python analysis/plot_redis_results.py"
    exit 1
fi

echo ""

# Step 6: Open plots directory
echo "[6/6] Opening plots directory..."
PLOTS_DIR="$PROJECT_ROOT/analysis/plots"

if [ -d "$PLOTS_DIR" ]; then
    echo "    ✓ Plots saved to: $PLOTS_DIR"
    echo ""
    echo "Available plots:"
    ls -1 "$PLOTS_DIR"/*.png 2>/dev/null | sed 's/^/      /'
    echo ""
    
    # Try to open plots directory in file manager (OS-specific)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open "$PLOTS_DIR"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v xdg-open &> /dev/null; then
            xdg-open "$PLOTS_DIR"
        fi
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows
        explorer "$PLOTS_DIR"
    fi
else
    echo "    ✗ Plots directory not found"
fi

echo ""
echo "========================================================================"
echo "✓ Parametric benchmark workflow complete!"
echo "========================================================================"
echo ""
echo "Results location: ./results/"
echo "Plots location:   ./analysis/plots/"
echo ""
echo "To view individual plot files:"
echo "    ls analysis/plots/"
echo ""
echo "To regenerate plots with different settings:"
echo "    python analysis/plot_redis_results.py --help"
echo ""

