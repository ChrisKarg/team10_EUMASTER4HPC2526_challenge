# Prometheus Service Recipes

This directory contains Prometheus monitoring service recipes.

## Available Recipes

### 1. `prometheus.yaml` - Basic Prometheus

Empty monitoring targets. Use this as a template.

```bash
# Edit the file and add your monitoring_targets
# Then run:
python main.py --recipe recipes/services/prometheus.yaml
```

### 2. `prometheus_with_ollama.yaml` - Example with Ollama

Pre-configured example to monitor an Ollama service.

**Usage:**

1. Start Ollama service:
   ```bash
   python main.py --recipe recipes/services/ollama.yaml
   ```

2. Get the service ID:
   ```bash
   python main.py --status
   ```
   Example output: `ollama_abc123`

3. Edit `prometheus_with_ollama.yaml` and replace `ollama_abc123` with your actual service ID

4. Start Prometheus:
   ```bash
   python main.py --recipe recipes/services/prometheus_with_ollama.yaml
   ```

5. Query metrics:
   ```bash
   # Get prometheus service ID
   python main.py --status
   
   # Query
   python main.py --query-service-metrics <PROMETHEUS_ID> "up"
   ```

## Configuration Format

```yaml
service:
  name: prometheus
  
  monitoring_targets:
    # Monitor by service ID (recommended)
    - service_id: "SERVICE_ID"     # From: python main.py --status
      job_name: "my-service"       # Optional: name in Prometheus
      port: 11434                  # Optional: service port
    
    # Or monitor by hostname
    - host: "mel2073"
      job_name: "specific-node"
      port: 9100
  
  container:
    docker_source: docker://prom/prometheus:latest
    image_path: $HOME/containers/prometheus.sif
  
  resources:
    mem: 4G
    cpus_per_task: 2
    time: "02:00:00"
  
  ports:
    - 9090
```

## Important Notes

1. **Service must be running first**: Start the service you want to monitor before starting Prometheus
2. **Get the service ID**: Use `python main.py --status` to find service IDs
3. **Metrics availability**: Not all services expose Prometheus metrics by default
4. **Automatic host discovery**: If you use `service_id`, Prometheus automatically finds the host from SLURM

## Troubleshooting

**"No targets found"**
- Make sure the service is running: `python main.py --status`
- Check that the service_id in the recipe matches exactly

**"No metrics available"**
- The service may not expose a `/metrics` endpoint
- This is normal - many services don't have built-in Prometheus exporters

**"Connection refused"**
- Check the port number in the recipe matches the service
- Verify network connectivity between Prometheus and the target service
