#!/bin/bash
#
# Start All Services with Monitoring
#
# This script starts all benchmark services with cAdvisor monitoring,
# Prometheus for metrics collection, and Grafana for visualization.
#
# Services started:
#   - Ollama (LLM inference) on GPU partition
#   - Redis (in-memory database) on CPU partition
#   - Chroma (vector database) on CPU partition
#   - MySQL (relational database) on CPU partition
#   - Prometheus (metrics collection)
#   - Grafana (visualization dashboard)
#
# Usage: ./scripts/start_all_services.sh
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Colors for output (using printf for compatibility)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "========================================================================"
printf "${BLUE}HPC Benchmarking Orchestrator - Start All Services${NC}\n"
echo "========================================================================"
echo ""
echo "This script will start:"
echo "  1. Ollama (LLM inference service) - GPU"
echo "  2. Redis (in-memory database) - CPU"
echo "  3. Chroma (vector database) - CPU"
echo "  4. MySQL (relational database) - CPU"
echo "  5. Prometheus (metrics collection)"
echo "  6. Grafana (monitoring dashboard)"
echo ""
echo "========================================================================"
echo ""

# Variables to store service IDs
OLLAMA_SERVICE_ID=""
OLLAMA_SERVICE_HOST=""
REDIS_SERVICE_ID=""
REDIS_SERVICE_HOST=""
CHROMA_SERVICE_ID=""
CHROMA_SERVICE_HOST=""
MYSQL_SERVICE_ID=""
MYSQL_SERVICE_HOST=""
PROMETHEUS_SERVICE_ID=""
PROMETHEUS_SERVICE_HOST=""
GRAFANA_SERVICE_ID=""
GRAFANA_SERVICE_HOST=""

# Function to wait for service to be assigned and set global variables
wait_for_service() {
    local service_name=$1
    local max_attempts=30
    local attempt=1
    
    echo "    Waiting for $service_name to be assigned to a node..."
    
    # Reset the return variables
    FOUND_SERVICE_ID=""
    FOUND_SERVICE_HOST=""
    
    while [ $attempt -le $max_attempts ]; do
        # Use --status to get properly formatted output
        STATUS_OUTPUT=$(python main.py --status 2>&1 || echo "")
        
        # Look for the service in output (Services section shows: job_id | name | status | time | node)
        SERVICE_LINE=$(echo "$STATUS_OUTPUT" | grep -i "${service_name}_" | grep -i "RUNNING" | head -1 || echo "")
        
        if [ -n "$SERVICE_LINE" ]; then
            # Extract service ID (format: service_name_hexid)
            FOUND_SERVICE_ID=$(echo "$SERVICE_LINE" | grep -oE "${service_name}_[a-f0-9]+" | head -1 || echo "")
            
            # Extract host - last column after the last pipe, should be like mel0123
            FOUND_SERVICE_HOST=$(echo "$SERVICE_LINE" | awk -F'|' '{print $NF}' | tr -d ' ' || echo "")
            
            # Verify host looks like a valid node name (starts with 'mel')
            if [ -n "$FOUND_SERVICE_ID" ] && echo "$FOUND_SERVICE_HOST" | grep -qE "^mel[0-9]+"; then
                printf "    ${GREEN}✓${NC} $service_name assigned: $FOUND_SERVICE_ID on $FOUND_SERVICE_HOST\n"
                return 0
            fi
        fi
        
        echo "    Attempt $attempt/$max_attempts: waiting..."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    printf "    ${YELLOW}⚠${NC} $service_name not assigned after $max_attempts attempts\n"
    return 1
}

# ======================================================================
# Step 1: Start Ollama Service
# ======================================================================
printf "${BLUE}[1/6] Starting Ollama service (GPU)...${NC}\n"

OLLAMA_OUTPUT=$(python main.py --recipe recipes/services/ollama_with_cadvisor.yaml 2>&1) || true

if echo "$OLLAMA_OUTPUT" | grep -qiE "(Service started|submitted|job)"; then
    printf "    ${GREEN}✓${NC} Ollama service submitted\n"
    if wait_for_service "ollama"; then
        OLLAMA_SERVICE_ID="$FOUND_SERVICE_ID"
        OLLAMA_SERVICE_HOST="$FOUND_SERVICE_HOST"
    fi
else
    printf "    ${RED}✗${NC} Failed to start Ollama service\n"
    echo "$OLLAMA_OUTPUT"
fi

echo ""

# ======================================================================
# Step 2: Start Redis Service
# ======================================================================
printf "${BLUE}[2/6] Starting Redis service (CPU)...${NC}\n"

REDIS_OUTPUT=$(python main.py --recipe recipes/services/redis_with_cadvisor.yaml 2>&1) || true

if echo "$REDIS_OUTPUT" | grep -qiE "(Service started|submitted|job)"; then
    printf "    ${GREEN}✓${NC} Redis service submitted\n"
    if wait_for_service "redis"; then
        REDIS_SERVICE_ID="$FOUND_SERVICE_ID"
        REDIS_SERVICE_HOST="$FOUND_SERVICE_HOST"
    fi
else
    printf "    ${RED}✗${NC} Failed to start Redis service\n"
    echo "$REDIS_OUTPUT"
fi

echo ""

# ======================================================================
# Step 3: Start Chroma Service
# ======================================================================
printf "${BLUE}[3/6] Starting Chroma service (CPU)...${NC}\n"

CHROMA_OUTPUT=$(python main.py --recipe recipes/services/chroma_with_cadvisor.yaml 2>&1) || true

if echo "$CHROMA_OUTPUT" | grep -qiE "(Service started|submitted|job)"; then
    printf "    ${GREEN}✓${NC} Chroma service submitted\n"
    if wait_for_service "chroma"; then
        CHROMA_SERVICE_ID="$FOUND_SERVICE_ID"
        CHROMA_SERVICE_HOST="$FOUND_SERVICE_HOST"
    fi
else
    printf "    ${RED}✗${NC} Failed to start Chroma service\n"
    echo "$CHROMA_OUTPUT"
fi

echo ""

# ======================================================================
# Step 4: Start MySQL Service
# ======================================================================
printf "${BLUE}[4/6] Starting MySQL service (CPU)...${NC}\n"

MYSQL_OUTPUT=$(python main.py --recipe recipes/services/mysql_with_cadvisor.yaml 2>&1) || true

if echo "$MYSQL_OUTPUT" | grep -qiE "(Service started|submitted|job)"; then
    printf "    ${GREEN}✓${NC} MySQL service submitted\n"
    if wait_for_service "mysql"; then
        MYSQL_SERVICE_ID="$FOUND_SERVICE_ID"
        MYSQL_SERVICE_HOST="$FOUND_SERVICE_HOST"
    fi
else
    printf "    ${RED}✗${NC} Failed to start MySQL service\n"
    echo "$MYSQL_OUTPUT"
fi

echo ""

# ======================================================================
# Step 5: Start Prometheus (with cAdvisor targets from services)
# ======================================================================
printf "${BLUE}[5/6] Starting Prometheus (metrics collection)...${NC}\n"

# Build list of cAdvisor targets from the services we started
echo "    Configuring Prometheus to scrape cAdvisor on service nodes..."

# Collect service hosts for Prometheus targets
TARGETS=""
[ -n "$OLLAMA_SERVICE_HOST" ] && TARGETS="$TARGETS ollama:$OLLAMA_SERVICE_HOST"
[ -n "$REDIS_SERVICE_HOST" ] && TARGETS="$TARGETS redis:$REDIS_SERVICE_HOST"
[ -n "$CHROMA_SERVICE_HOST" ] && TARGETS="$TARGETS chroma:$CHROMA_SERVICE_HOST"
[ -n "$MYSQL_SERVICE_HOST" ] && TARGETS="$TARGETS mysql:$MYSQL_SERVICE_HOST"

if [ -n "$TARGETS" ]; then
    echo "    Found cAdvisor targets: $TARGETS"
    
    # Write Prometheus config to remote cluster via SSH
    python3 - "$TARGETS" << 'PYEOF'
import paramiko
import yaml
import sys
import os

targets_str = sys.argv[1]
targets = []
for t in targets_str.strip().split():
    if ':' in t:
        name, host = t.split(':', 1)
        targets.append((name, host))

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

ssh_config = config.get('ssh', config.get('hpc', {}))
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

key_path = ssh_config.get('key_filename', ssh_config.get('key_path', '~/.ssh/id_ed25519_mlux'))
if key_path.startswith('~'):
    key_path = os.path.expanduser(key_path)

client.connect(
    hostname=ssh_config.get('hostname', 'login.lxp.lu'),
    port=ssh_config.get('port', 8822),
    username=ssh_config.get('username'),
    key_filename=key_path
)

# Build scrape configs for each target
scrape_configs = ""
for name, host in targets:
    scrape_configs += f'''
  - job_name: '{name}-cadvisor'
    static_configs:
      - targets: ['{host}:8080']
        labels:
          service: '{name}'
          instance: '{host}'
'''

# Create Prometheus config
prometheus_yml = f'''global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
{scrape_configs}'''

# Write config to cluster
commands = f'''
mkdir -p $HOME/prometheus/config
mkdir -p $HOME/prometheus/data

cat > $HOME/prometheus/config/prometheus.yml << 'PROMEOF'
{prometheus_yml}
PROMEOF

echo "Prometheus config created with {len(targets)} cAdvisor target(s)"
cat $HOME/prometheus/config/prometheus.yml
'''

stdin, stdout, stderr = client.exec_command(commands)
output = stdout.read().decode().strip()
for line in output.split('\n'):
    print(f"    {line}")
client.close()
PYEOF

else
    printf "    ${YELLOW}⚠${NC} No service hosts found, Prometheus will have no targets\n"
fi

# Now start Prometheus
PROMETHEUS_OUTPUT=$(python main.py --recipe recipes/services/prometheus_with_cadvisor.yaml 2>&1) || true

if echo "$PROMETHEUS_OUTPUT" | grep -qiE "(Service started|submitted|job)"; then
    printf "    ${GREEN}✓${NC} Prometheus service submitted\n"
    if wait_for_service "prometheus"; then
        PROMETHEUS_SERVICE_ID="$FOUND_SERVICE_ID"
        PROMETHEUS_SERVICE_HOST="$FOUND_SERVICE_HOST"
    fi
else
    printf "    ${RED}✗${NC} Failed to start Prometheus service\n"
    echo "$PROMETHEUS_OUTPUT"
fi

echo ""

# ======================================================================
# Step 6: Start Grafana
# ======================================================================
printf "${BLUE}[6/6] Starting Grafana (visualization)...${NC}\n"

# Create Grafana config with correct Prometheus URL on the REMOTE cluster
if [ -n "$PROMETHEUS_SERVICE_HOST" ]; then
    echo "    Prometheus running on: $PROMETHEUS_SERVICE_HOST"
    PROM_URL="http://${PROMETHEUS_SERVICE_HOST}:9090"

    # Write config to REMOTE cluster via Python/SSH
    echo "    Writing Grafana config to MeluXina cluster..."
    python3 - "$PROM_URL" << 'PYEOF'
import paramiko
import yaml
import sys
import os

prom_url = sys.argv[1]

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

ssh_config = config.get('ssh', config.get('hpc', {}))
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

key_path = ssh_config.get('key_filename', ssh_config.get('key_path', '~/.ssh/id_ed25519_mlux'))
if key_path.startswith('~'):
    key_path = os.path.expanduser(key_path)

client.connect(
    hostname=ssh_config.get('hostname', 'login.lxp.lu'),
    port=ssh_config.get('port', 8822),
    username=ssh_config.get('username'),
    key_filename=key_path
)

# Create directories and write config
commands = f'''
mkdir -p $HOME/grafana/provisioning/datasources
mkdir -p $HOME/grafana/provisioning/dashboards
mkdir -p $HOME/grafana/dashboards
mkdir -p $HOME/grafana/data
mkdir -p $HOME/grafana/logs

# Write Prometheus URL to file for discovery
echo "{prom_url}" > $HOME/.prometheus_url

# Write datasource config
cat > $HOME/grafana/provisioning/datasources/prometheus.yml << 'EOFDS'
apiVersion: 1

datasources:
  - name: Prometheus
    uid: prometheus
    type: prometheus
    access: proxy
    url: {prom_url}
    isDefault: true
    editable: true
    jsonData:
      timeInterval: "15s"
EOFDS

echo "Grafana config created with Prometheus at: {prom_url}"
'''

stdin, stdout, stderr = client.exec_command(commands)
print("    " + stdout.read().decode().strip())
err = stderr.read().decode().strip()
if err:
    print(f"    Warnings: {err}")
client.close()
PYEOF

    echo "    Grafana will connect to Prometheus at: $PROM_URL"
else
    echo "    WARNING: Prometheus host not found, Grafana may not connect properly"
fi

GRAFANA_OUTPUT=$(python main.py --recipe recipes/services/grafana.yaml 2>&1) || true

if echo "$GRAFANA_OUTPUT" | grep -qiE "(Service started|submitted|job)"; then
    printf "    ${GREEN}✓${NC} Grafana service submitted\n"
    if wait_for_service "grafana"; then
        GRAFANA_SERVICE_ID="$FOUND_SERVICE_ID"
        GRAFANA_SERVICE_HOST="$FOUND_SERVICE_HOST"
    fi
else
    printf "    ${RED}✗${NC} Failed to start Grafana service\n"
    echo "$GRAFANA_OUTPUT"
fi

echo ""

# ======================================================================
# Summary and SSH Tunnel Instructions
# ======================================================================
echo "========================================================================"
printf "${GREEN}SERVICE STARTUP COMPLETE${NC}\n"
echo "========================================================================"
echo ""

# Show current status
echo "Current service status:"
python main.py --status 2>&1 | head -40

echo ""
echo "========================================================================"
printf "${BLUE}SSH TUNNEL COMMANDS${NC}\n"
echo "========================================================================"
echo ""
echo "Run these commands in separate terminals to access the services:"
echo ""

# Use captured hosts or placeholder
PROM_HOST="${PROMETHEUS_SERVICE_HOST:-<prometheus_node>}"
GRAF_HOST="${GRAFANA_SERVICE_HOST:-<grafana_node>}"

printf "${YELLOW}# Prometheus (metrics):${NC}\n"
echo "ssh -i ~/.ssh/id_ed25519_mlux -L 9090:${PROM_HOST}:9090 -N u103227@login.lxp.lu -p 8822"
echo ""
printf "${YELLOW}# Grafana (dashboards):${NC}\n"
echo "ssh -i ~/.ssh/id_ed25519_mlux -L 3000:${GRAF_HOST}:3000 -N u103227@login.lxp.lu -p 8822"
echo ""
echo "========================================================================"
printf "${BLUE}ACCESS URLS (after creating tunnels)${NC}\n"
echo "========================================================================"
echo ""
echo "  Prometheus: http://localhost:9090"
echo "  Grafana:    http://localhost:3000 (admin/admin)"
echo ""
echo "========================================================================"
printf "${BLUE}SERVICE IDS FOR CLIENTS${NC}\n"
echo "========================================================================"
echo ""
echo "Use these service IDs when starting benchmark clients:"
echo ""
echo "  Ollama:     ${OLLAMA_SERVICE_ID:-<not_started>}"
echo "  Redis:      ${REDIS_SERVICE_ID:-<not_started>}"
echo "  Chroma:     ${CHROMA_SERVICE_ID:-<not_started>}"
echo "  MySQL:      ${MYSQL_SERVICE_ID:-<not_started>}"
echo ""

# Save service IDs to a file for the client script
SERVICE_IDS_FILE="$PROJECT_ROOT/.service_ids"
cat > "$SERVICE_IDS_FILE" << EOF
# Service IDs (auto-generated by start_all_services.sh)
# Generated: $(date)
OLLAMA_SERVICE_ID="${OLLAMA_SERVICE_ID}"
REDIS_SERVICE_ID="${REDIS_SERVICE_ID}"
CHROMA_SERVICE_ID="${CHROMA_SERVICE_ID}"
MYSQL_SERVICE_ID="${MYSQL_SERVICE_ID}"
PROMETHEUS_SERVICE_ID="${PROMETHEUS_SERVICE_ID}"
GRAFANA_SERVICE_ID="${GRAFANA_SERVICE_ID}"
PROMETHEUS_HOST="${PROM_HOST}"
GRAFANA_HOST="${GRAF_HOST}"
EOF

echo "Service IDs saved to: $SERVICE_IDS_FILE"
echo ""
echo "========================================================================"
printf "${GREEN}NEXT STEP${NC}\n"
echo "========================================================================"
echo ""
echo "To start all benchmark clients and see results in Grafana:"
echo ""
echo "  ./scripts/start_all_clients.sh"
echo ""
echo "========================================================================"
