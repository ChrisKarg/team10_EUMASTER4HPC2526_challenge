# Writing Custom Recipes

Create custom recipes for new services or specialized benchmark configurations.

## Creating a Service Recipe

### Step 1: Basic Structure

```yaml
# recipes/services/my_service.yaml
service:
  name: my_service
  description: "Description of my service"
  
  container:
    docker_source: docker://myimage:tag
    image_path: $HOME/containers/my_service.sif
  
  resources:
    cpus_per_task: 4
    mem: "8G"
    time: "02:00:00"
    partition: cpu
  
  environment:
    MY_VAR: "value"
  
  ports:
    - 8080
```

### Step 2: Test the Recipe

```bash
# Validate and run
python main.py --verbose --recipe recipes/services/my_service.yaml

# Check it started
python main.py --status
```

### Step 3: Add Monitoring (Optional)

```yaml
service:
  name: my_service
  # ... other fields ...
  
  enable_cadvisor: true
  cadvisor_port: 8080
```

## Creating a Client Recipe

### Step 1: Choose Client Type

Use an existing client type or create a new one:

| Type | For Service |
|------|-------------|
| `ollama_benchmark` | Ollama LLM |
| `redis_benchmark` | Redis |
| `chroma_benchmark` | Chroma |
| `mysql_benchmark` | MySQL |

### Step 2: Define Parameters

```yaml
# recipes/clients/my_benchmark.yaml
client:
  name: my_benchmark
  type: redis_benchmark  # Use existing type
  
  parameters:
    clients: 100
    requests: 50000
    data_size: 512
    tests: "SET,GET,HSET,HGET"
    output_file: "$HOME/results/my_benchmark.json"
  
  resources:
    cpus_per_task: 2
    mem: "4G"
    time: "00:30:00"
```

### Step 3: Run the Benchmark

```bash
python main.py --recipe recipes/clients/my_benchmark.yaml --target-service redis_xxx
```

## Advanced: Custom Service Class

For completely new services, create a Python class:

### Step 1: Create Service Class

```python
# src/services/my_service.py
from .base import Service
from ..base import JobFactory

class MyService(Service):
    """My custom service implementation"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.my_option = config.get('my_option', 'default')
    
    def get_service_setup_commands(self):
        """Custom setup commands"""
        commands = super().get_service_setup_commands()
        commands.extend([
            f"export MY_OPTION={self.my_option}",
            "mkdir -p $HOME/my_service/data",
        ])
        return commands
    
    def get_container_command(self):
        """Custom container execution"""
        return f"""
        apptainer exec \\
            --bind $HOME/my_service/data:/data \\
            {self._resolve_container_path()} \\
            my_service_command --port 8080 &
        """

# Register with factory
JobFactory.register_service('my_service', MyService)
```

### Step 2: Register in `__init__.py`

```python
# src/services/__init__.py
from .my_service import MyService
# Add to imports and registration
```

### Step 3: Create Recipe

```yaml
# recipes/services/my_service.yaml
service:
  name: my_service
  my_option: "custom_value"
  
  container:
    docker_source: docker://myimage:tag
    image_path: $HOME/containers/my_service.sif
  
  resources:
    cpus_per_task: 4
    mem: "8G"
```

## Recipe Validation

Recipes are validated for:

1. **Required fields**: `name`, `container.docker_source`
2. **Valid types**: Resource values, partition names
3. **Path resolution**: `$HOME`, `$SCRATCH` variables
4. **Port conflicts**: Unique port assignments

## Tips for Custom Recipes

!!! tip "Start Simple"
    Begin with minimal configuration and add options as needed.

!!! tip "Test Locally First"
    If possible, test container commands locally before deploying.

!!! tip "Use Existing Templates"
    Copy and modify existing recipes rather than starting from scratch.

!!! warning "Resource Limits"
    Be mindful of HPC allocation limits when setting resources.

## Debugging Recipes

```bash
# Verbose mode shows generated script
python main.py --verbose --recipe recipes/services/my_service.yaml

# View generated script
cat scripts/service_my_service_*.sh

# Check SLURM logs
ssh meluxina "cat slurm-*.out"
```

---

See also: [Services Overview](../services/overview.md) | [Development Guide](../development/extending.md)
