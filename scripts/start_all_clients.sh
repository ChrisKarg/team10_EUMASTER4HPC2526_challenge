#!/bin/bash
#
# Start All Benchmark Clients
#
# This script starts benchmark clients for all running services.
# Run this AFTER start_all_services.sh to see real-time results in Grafana.
#
# Clients started:
#   - Ollama benchmark (LLM inference)
#   - Redis benchmark (in-memory database)
#   - Chroma benchmark (vector database)
#   - MySQL benchmark (relational database)
#
# Usage: ./scripts/start_all_clients.sh
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo "========================================================================"
printf "${BLUE}HPC Benchmarking Orchestrator - Start All Clients${NC}\n"
echo "========================================================================"
echo ""

# Load service IDs if available
SERVICE_IDS_FILE="$PROJECT_ROOT/.service_ids"
if [ -f "$SERVICE_IDS_FILE" ]; then
    echo "Loading service IDs from previous session..."
    source "$SERVICE_IDS_FILE"
    echo ""
fi

# Function to find service ID by name
find_service_id() {
    local service_name=$1
    local service_id=""
    
    STATUS_OUTPUT=$(python main.py --list-running-services 2>&1 || echo "")
    
    # Look for the service in output
    SERVICE_LINE=$(echo "$STATUS_OUTPUT" | grep -i "$service_name" | grep -v "benchmark" | head -1 || echo "")
    
    if [ -n "$SERVICE_LINE" ]; then
        service_id=$(echo "$SERVICE_LINE" | grep -oE "${service_name}_[a-f0-9]+" | head -1 || echo "")
    fi
    
    echo "$service_id"
}

echo "========================================================================"
printf "${CYAN}Discovering running services...${NC}\n"
echo "========================================================================"
echo ""

# Discover services
OLLAMA_ID=$(find_service_id "ollama")
REDIS_ID=$(find_service_id "redis")
CHROMA_ID=$(find_service_id "chroma")
MYSQL_ID=$(find_service_id "mysql")

# Use saved IDs if discovery failed
[ -z "$OLLAMA_ID" ] && OLLAMA_ID="$OLLAMA_SERVICE_ID"
[ -z "$REDIS_ID" ] && REDIS_ID="$REDIS_SERVICE_ID"
[ -z "$CHROMA_ID" ] && CHROMA_ID="$CHROMA_SERVICE_ID"
[ -z "$MYSQL_ID" ] && MYSQL_ID="$MYSQL_SERVICE_ID"

echo "Discovered services:"
echo "  Ollama: ${OLLAMA_ID:-NOT FOUND}"
echo "  Redis:  ${REDIS_ID:-NOT FOUND}"
echo "  Chroma: ${CHROMA_ID:-NOT FOUND}"
echo "  MySQL:  ${MYSQL_ID:-NOT FOUND}"
echo ""

# Check if any services are available
if [ -z "$OLLAMA_ID" ] && [ -z "$REDIS_ID" ] && [ -z "$CHROMA_ID" ] && [ -z "$MYSQL_ID" ]; then
    printf "${RED}ERROR: No services found!${NC}\n"
    echo ""
    echo "Please start services first with:"
    echo "  ./scripts/start_all_services.sh"
    echo ""
    exit 1
fi

# Counter for started clients
STARTED_COUNT=0
STARTED_LIST=""

echo "========================================================================"
printf "${BLUE}Starting benchmark clients...${NC}\n"
echo "========================================================================"
echo ""

# ======================================================================
# Start Ollama Benchmark
# ======================================================================
if [ -n "$OLLAMA_ID" ]; then
    printf "${BLUE}[1/4] Starting Ollama benchmark...${NC}\n"
    echo "    Target service: $OLLAMA_ID"
    
    OLLAMA_CLIENT_OUTPUT=$(python main.py --recipe recipes/clients/ollama_benchmark.yaml --target-service "$OLLAMA_ID" 2>&1) || true
    
    if echo "$OLLAMA_CLIENT_OUTPUT" | grep -qiE "(Client started|submitted|job)"; then
        CLIENT_ID=$(echo "$OLLAMA_CLIENT_OUTPUT" | grep -oE "ollama[_a-z]*_[a-f0-9]+" | head -1 || echo "ollama_benchmark")
        printf "    ${GREEN}✓${NC} Ollama benchmark submitted: $CLIENT_ID\n"
        STARTED_COUNT=$((STARTED_COUNT + 1))
        STARTED_LIST="${STARTED_LIST}  - ollama_benchmark\n"
    else
        printf "    ${RED}✗${NC} Failed to start Ollama benchmark\n"
        echo "    Output: $OLLAMA_CLIENT_OUTPUT"
    fi
else
    printf "${YELLOW}[1/4] Skipping Ollama benchmark (service not running)${NC}\n"
fi

echo ""

# ======================================================================
# Start Redis Benchmark
# ======================================================================
if [ -n "$REDIS_ID" ]; then
    printf "${BLUE}[2/4] Starting Redis benchmark...${NC}\n"
    echo "    Target service: $REDIS_ID"
    
    REDIS_CLIENT_OUTPUT=$(python main.py --recipe recipes/clients/redis_benchmark.yaml --target-service "$REDIS_ID" 2>&1) || true
    
    if echo "$REDIS_CLIENT_OUTPUT" | grep -qiE "(Client started|submitted|job)"; then
        CLIENT_ID=$(echo "$REDIS_CLIENT_OUTPUT" | grep -oE "redis[_a-z]*_[a-f0-9]+" | head -1 || echo "redis_benchmark")
        printf "    ${GREEN}✓${NC} Redis benchmark submitted: $CLIENT_ID\n"
        STARTED_COUNT=$((STARTED_COUNT + 1))
        STARTED_LIST="${STARTED_LIST}  - redis_benchmark\n"
    else
        printf "    ${RED}✗${NC} Failed to start Redis benchmark\n"
        echo "    Output: $REDIS_CLIENT_OUTPUT"
    fi
else
    printf "${YELLOW}[2/4] Skipping Redis benchmark (service not running)${NC}\n"
fi

echo ""

# ======================================================================
# Start Chroma Benchmark
# ======================================================================
if [ -n "$CHROMA_ID" ]; then
    printf "${BLUE}[3/4] Starting Chroma benchmark...${NC}\n"
    echo "    Target service: $CHROMA_ID"
    
    CHROMA_CLIENT_OUTPUT=$(python main.py --recipe recipes/clients/chroma_benchmark.yaml --target-service "$CHROMA_ID" 2>&1) || true
    
    if echo "$CHROMA_CLIENT_OUTPUT" | grep -qiE "(Client started|submitted|job)"; then
        CLIENT_ID=$(echo "$CHROMA_CLIENT_OUTPUT" | grep -oE "chroma[_a-z]*_[a-f0-9]+" | head -1 || echo "chroma_benchmark")
        printf "    ${GREEN}✓${NC} Chroma benchmark submitted: $CLIENT_ID\n"
        STARTED_COUNT=$((STARTED_COUNT + 1))
        STARTED_LIST="${STARTED_LIST}  - chroma_benchmark\n"
    else
        printf "    ${RED}✗${NC} Failed to start Chroma benchmark\n"
        echo "    Output: $CHROMA_CLIENT_OUTPUT"
    fi
else
    printf "${YELLOW}[3/4] Skipping Chroma benchmark (service not running)${NC}\n"
fi

echo ""

# ======================================================================
# Start MySQL Benchmark
# ======================================================================
if [ -n "$MYSQL_ID" ]; then
    printf "${BLUE}[4/4] Starting MySQL benchmark...${NC}\n"
    echo "    Target service: $MYSQL_ID"
    
    MYSQL_CLIENT_OUTPUT=$(python main.py --recipe recipes/clients/mysql_benchmark.yaml --target-service "$MYSQL_ID" 2>&1) || true
    
    if echo "$MYSQL_CLIENT_OUTPUT" | grep -qiE "(Client started|submitted|job)"; then
        CLIENT_ID=$(echo "$MYSQL_CLIENT_OUTPUT" | grep -oE "mysql[_a-z]*_[a-f0-9]+" | head -1 || echo "mysql_benchmark")
        printf "    ${GREEN}✓${NC} MySQL benchmark submitted: $CLIENT_ID\n"
        STARTED_COUNT=$((STARTED_COUNT + 1))
        STARTED_LIST="${STARTED_LIST}  - mysql_benchmark\n"
    else
        printf "    ${RED}✗${NC} Failed to start MySQL benchmark\n"
        echo "    Output: $MYSQL_CLIENT_OUTPUT"
    fi
else
    printf "${YELLOW}[4/4] Skipping MySQL benchmark (service not running)${NC}\n"
fi

echo ""

# ======================================================================
# Summary
# ======================================================================
echo "========================================================================"
printf "${GREEN}BENCHMARK CLIENTS STARTED${NC}\n"
echo "========================================================================"
echo ""
echo "Started clients: $STARTED_COUNT"
printf "$STARTED_LIST"
echo ""

# Show current status
echo "========================================================================"
printf "${CYAN}Current System Status${NC}\n"
echo "========================================================================"
echo ""
python main.py --status 2>&1 | head -40
echo ""

echo "========================================================================"
printf "${BLUE}VIEW RESULTS IN GRAFANA${NC}\n"
echo "========================================================================"
echo ""
echo "To see real-time benchmark results in Grafana:"
echo ""
echo "1. Ensure SSH tunnels are running (from start_all_services.sh output)"
echo ""
echo "2. Open Grafana in your browser:"
echo "   http://localhost:3000"
echo ""
echo "3. Navigate to dashboards:"
echo "   - Overview: System summary and resource usage"
echo "   - Service Monitoring: Detailed CPU, memory, network metrics"
echo ""
echo "4. Key metrics to watch:"
echo "   - CPU usage rate (spikes during benchmarks)"
echo "   - Memory usage (growth patterns)"
echo "   - Network I/O (data transfer rates)"
echo ""
echo "========================================================================"
printf "${BLUE}USEFUL COMMANDS${NC}\n"
echo "========================================================================"
echo ""
echo "Check benchmark status:"
echo "  python main.py --status"
echo ""
echo "Query Prometheus metrics:"
echo "  python main.py --query-metrics <prometheus_id> 'up'"
echo "  python main.py --query-metrics <prometheus_id> 'container_cpu_usage_seconds_total'"
echo ""
echo "Download benchmark results (after completion):"
echo "  python main.py --download-results"
echo ""
echo "Stop all services and clients:"
echo "  python main.py --stop-all-services"
echo ""
echo "========================================================================"
printf "${GREEN}Benchmarks are now running! Watch the results in Grafana.${NC}\n"
echo "========================================================================"
