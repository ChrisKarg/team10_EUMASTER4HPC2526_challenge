#!/usr/bin/env python3
"""
HPC Orchestrator for AI Benchmarking Framework
Manages containerized services on HPC clusters via SLURM
"""

import os
import sys
import argparse
import logging
from pathlib import Path

def setup_logging(log_level="INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('orchestrator.log')
        ]
    )

def check_dependencies():
    """Check if required dependencies are available"""
    required_modules = ['yaml', 'paramiko', 'scp']
    missing = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    return missing

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='HPC AI Benchmarking Orchestrator')
    parser.add_argument('--config', '-c', type=str, default='config.yaml',
                       help='Configuration file path')
    parser.add_argument('--recipe', '-r', type=str,
                       help='Recipe file to execute')
    parser.add_argument('--target-service', '-t', type=str,
                       help='Target service ID for client recipes (use with --recipe)')
    parser.add_argument('--target-endpoint', '-e', type=str,
                       help='Direct endpoint for client recipes (e.g., http://node-01:11434)')
    parser.add_argument('--list-services', action='store_true',
                       help='List available services')
    parser.add_argument('--list-clients', action='store_true',
                       help='List available clients')
    parser.add_argument('--status', action='store_true',
                       help='Show system status')
    parser.add_argument('--slurm-status', action='store_true',
                       help='Show SLURM job status (all user jobs)')
    parser.add_argument('--clear-state', action='store_true',
                       help='Clear all tracked services and clients')
    parser.add_argument('--stop-service', type=str, metavar='SERVICE_ID',
                       help='Stop a running service by ID')
    parser.add_argument('--stop-all-services', action='store_true',
                       help='Stop all running services')
    parser.add_argument('--stop-session', type=str, metavar='SESSION_ID',
                       help='Stop a benchmark session by ID')
    parser.add_argument('--debug-services', action='store_true',
                       help='Show detailed debug information about all services')
    parser.add_argument('--list-all-services', action='store_true',
                       help='List all services (tracked and SLURM-only)')
    parser.add_argument('--list-running-services', action='store_true',
                       help='List only running services with their IDs')
    parser.add_argument('--list-monitors', action='store_true',
                       help='List running monitors')
    parser.add_argument('--monitor-status', type=str, metavar='MONITOR_ID',
                       help='Check status of a specific monitor')
    parser.add_argument('--stop-monitor', type=str, metavar='MONITOR_ID',
                       help='Stop a running monitor')
    parser.add_argument('--query-metrics', type=str, nargs=2, metavar=('SERVICE_ID', 'QUERY'),
                       help='Query Prometheus metrics from a service or monitor (e.g., --query-metrics prometheus_4e29faf0 "up")')
    parser.add_argument('--list-available-metrics', type=str, metavar='SERVICE_ID',
                       help='List all available metric names from a Prometheus service (e.g., --list-available-metrics prometheus_4e29faf0)')
    parser.add_argument('--query-service-metrics', type=str, nargs=2, metavar=('SERVICE_ID', 'QUERY'),
                       help='Query Prometheus metrics from a service (e.g., --query-service-metrics svc123 "up")')
    parser.add_argument('--monitor-endpoint', type=str, metavar='MONITOR_ID',
                       help='Get Prometheus endpoint URL for a monitor')
    parser.add_argument('--service-endpoint', type=str, metavar='SERVICE_ID',
                       help='Get endpoint URL for a service (including Prometheus)')
    parser.add_argument('--create-tunnel', type=str, nargs='+', metavar='SERVICE_ID [LOCAL_PORT] [REMOTE_PORT]',
                       help='Create SSH tunnel to a service (e.g., --create-tunnel prometheus_abc123 9090 9090). If ports not specified, defaults to 9090:9090')
    parser.add_argument('--start-session', type=str, nargs=3, metavar=('SERVICE_RECIPE', 'CLIENT_RECIPE', 'PROMETHEUS_RECIPE'),
                       help='Complete automated session: starts service with cAdvisor, starts client benchmark, starts Prometheus monitoring, creates SSH tunnel (e.g., --start-session recipes/services/ollama_with_cadvisor.yaml recipes/clients/ollama_benchmark.yaml recipes/services/prometheus_with_cadvisor.yaml)')
    parser.add_argument('--start-monitoring', type=str, nargs=2, metavar=('SERVICE_RECIPE', 'PROMETHEUS_RECIPE'),
                       help='[DEPRECATED: Use --start-session] Automated monitoring setup: starts service with cAdvisor, starts Prometheus, creates SSH tunnel')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--setup', action='store_true',
                       help='Run setup and dependency check')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting HPC Orchestrator")
    
    # Check dependencies first
    missing_deps = check_dependencies()
    if missing_deps and not args.setup:
        print(f"❌ Missing required dependencies: {', '.join(missing_deps)}")
        print("Install with: pip install -r requirements.txt")
        print("Or run: python main.py --setup")
        return 1
    
    # Run setup if requested
    if args.setup:
        print("Running setup...")
        try:
            import setup
            return setup.main()
        except ImportError:
            print("❌ Setup script not found")
            return 1
    
    try:
        # Add src directory to path for imports
        sys.path.insert(0, str(Path(__file__).parent / 'src'))
        
        # Import modules (will fail gracefully if dependencies missing)
        from orchestrator import BenchmarkOrchestrator
        
        # Initialize the orchestrator
        interface = BenchmarkOrchestrator(config_path=args.config)
        
        if args.list_services:
            services = interface.servers.list_available_services()
            print("Available Services:")
            for service in services:
                print(f"  - {service}")
        
        elif args.list_clients:
            clients = interface.clients.list_available_clients()
            print("Available Clients:")
            for client in clients:
                print(f"  - {client}")
        
        elif args.status:
            # Use SLURM-based status as default since it's more reliable
            slurm_status = interface.get_slurm_status()
            
            if 'error' in slurm_status:
                print(f"❌ Error getting SLURM status: {slurm_status['error']}")
                return 1
            
            print("SLURM Job Status:")
            print(f"  Total Jobs: {slurm_status['total_jobs']}")
            print(f"  Services: {slurm_status['services']['count']}")
            print(f"  Clients: {slurm_status['clients']['count']}")
            print(f"  Other: {slurm_status['other']['count']}")
            
            # Show services
            if slurm_status['services']['jobs']:
                print("\nServices:")
                for job in slurm_status['services']['jobs']:
                    print(f"  {job['job_id']:>8} | {job['name']:>15} | {job['state']:>10} | {job['time']:>8} | {job['nodes']}")
            
            # Show clients  
            if slurm_status['clients']['jobs']:
                print("\nClients:")
                for job in slurm_status['clients']['jobs']:
                    print(f"  {job['job_id']:>8} | {job['name']:>15} | {job['state']:>10} | {job['time']:>8} | {job['nodes']}")
            
            # Show other jobs
            if slurm_status['other']['jobs']:
                print("\nOther Jobs:")
                for job in slurm_status['other']['jobs']:
                    print(f"  {job['job_id']:>8} | {job['name']:>15} | {job['state']:>10} | {job['time']:>8} | {job['nodes']}")
        
        elif args.slurm_status:
            # Alternative detailed SLURM view
            status = interface.get_system_status()
            print("Orchestrator Internal Status:")
            print(f"  SSH Connected: {status['ssh_connected']}")
            print(f"  Tracked Services: {status['services']['total_services']}")
            print(f"  Tracked Clients: {status['clients']['total_clients']}")
            print(f"  Active Sessions: {status['active_sessions']}")
            
            # Show detailed status for each service
            if status['services']['services']:
                print("\nTracked Services:")
                for service_id, service_info in status['services']['services'].items():
                    print(f"  {service_id}: {service_info.get('status', 'unknown')} (Job: {service_info.get('job_id', 'N/A')})")
            
            # Show detailed status for each client
            if status['clients']['clients']:
                print("\nTracked Clients:")
                for client_id, client_info in status['clients']['clients'].items():
                    print(f"  {client_id}: {client_info.get('status', 'unknown')} (Job: {client_info.get('job_id', 'N/A')})")
        
        elif args.clear_state:
            print("Clearing all tracked services and clients...")
            cleared_services, cleared_clients = interface.clear_all_state()
            print(f"✅ Cleared {cleared_services} services and {cleared_clients} clients from tracking.")
            print("Note: This does not cancel actual SLURM jobs, only clears internal tracking.")
        
        elif args.stop_service:
            service_id = args.stop_service
            print(f"Stopping service: {service_id}")
            
            success = interface.stop_service(service_id)
            if success:
                print(f"✅ Service {service_id} stopped successfully")
            else:
                print(f"❌ Failed to stop service {service_id}")
                print("Check if the service ID is valid and the service is running")
                return 1
        
        elif args.stop_all_services:
            print("Stopping all running services...")
            
            results = interface.stop_all_services()
            
            if 'error' in results:
                print(f"❌ Error: {results['error']}")
                return 1
            
            if results['total_services'] == 0:
                print("No running services found")
                return 0
            
            print(f"✅ Stopped {results['stopped_services']}/{results['total_services']} services")
            
            if results['failed_services'] > 0:
                print(f"❌ Failed to stop {results['failed_services']} services:")
                for service_id, result in results['results'].items():
                    if result != 'stopped':
                        print(f"  {service_id}: {result}")
        
        elif args.stop_session:
            session_id = args.stop_session
            print(f"Stopping benchmark session: {session_id}")
            
            success = interface.stop_benchmark_session(session_id)
            if success:
                print(f"✅ Benchmark session {session_id} stopped successfully")
            else:
                print(f"❌ Failed to stop benchmark session {session_id}")
                print("Check if the session ID is valid and the session is active")
                return 1
        
        elif args.debug_services:
            print("Debug information for all services:")
            debug_info = interface.debug_services()
            
            if 'error' in debug_info:
                print(f"❌ Error: {debug_info['error']}")
                return 1
            
            print(f"\n📊 Tracked Services ({len(debug_info['tracked_services'])})")
            for service_id, info in debug_info['tracked_services'].items():
                print(f"  {service_id}:")
                print(f"    Job ID: {info['job_id']}")
                print(f"    Status: {info['status']}")
                print(f"    Submitted: {info['submitted_at']}")
            
            print(f"\n🔧 SLURM Jobs ({len(debug_info['slurm_jobs'])})")
            for job in debug_info['slurm_jobs']:
                tracked_mark = "✅" if job['is_tracked'] else "❌"
                print(f"  {tracked_mark} {job['job_id']} | {job['name']} | {job['state']} | {job['time']}")
            
            print(f"\n📋 All Services Summary:")
            all_services = debug_info['all_services']
            print(f"  Tracked: {len(all_services['tracked_services'])}")
            print(f"  SLURM-only: {len(all_services['slurm_services'])}")
            print(f"  Total: {len(all_services['all_services'])}")
        
        elif args.list_all_services:
            print("All services (tracked and SLURM-only):")
            all_services = interface.servers.list_all_services()
            
            if all_services['tracked_services']:
                print(f"\n📊 Tracked Services ({len(all_services['tracked_services'])}):")
                for service in all_services['tracked_services']:
                    print(f"  {service['service_id']} (Job: {service['job_id']}) - {service['status']}")
            
            if all_services['slurm_services']:
                print(f"\n🔧 SLURM-only Services ({len(all_services['slurm_services'])}):")
                for service in all_services['slurm_services']:
                    print(f"  {service['service_id']} (Job: {service['job_id']}) - {service['status']}")
            
            if not all_services['all_services']:
                print("No services found")
        
        elif args.list_running_services:
            print("Currently running services:")
            all_services = interface.servers.list_all_services()
            
            running_services = [s for s in all_services['all_services'] 
                              if s['status'].upper() in ['RUNNING', 'PENDING']]
            
            if not running_services:
                print("  No running services found")
                print("\nTo start a service, use:")
                print("  python main.py --recipe recipes/services/ollama.yaml")
            else:
                print(f"\nFound {len(running_services)} running services:")
                for service in running_services:
                    type_marker = "📊" if service['type'] == 'tracked' else "🔧"
                    print(f"  {type_marker} {service['service_id']} (Job: {service['job_id']}) - {service['status']}")
                
                print(f"\nTo target a service, use:")
                print(f"  python main.py --recipe recipes/clients/ollama_benchmark.yaml --target-service <SERVICE_ID>")
        
        elif args.list_monitors:
            print("Running monitors/Prometheus services:")
            
            # Check monitors module
            running_monitors = interface.monitors.list_running_monitors()
            
            # Check for Prometheus services
            all_services = interface.servers.list_all_services()
            prometheus_services = [s for s in all_services['all_services'] 
                                  if 'prometheus' in s['service_id'].lower() and 
                                  s['status'].upper() in ['RUNNING', 'PENDING']]
            
            if not running_monitors and not prometheus_services:
                print("  No running monitors found")
                print("\nTo start a monitor, use:")
                print("  python main.py --recipe recipes/services/prometheus.yaml --target-service <SERVICE_ID>")
            else:
                total_count = len(running_monitors) + len(prometheus_services)
                print(f"\nFound {total_count} running Prometheus instance(s):")
                
                # Show monitors from monitors module
                if running_monitors:
                    print("\n  From Monitors Module:")
                    for monitor_id in running_monitors:
                        status = interface.monitors.check_monitor_status(monitor_id)
                        endpoint = interface.monitors.get_monitor_endpoint(monitor_id)
                        print(f"    📊 {monitor_id}")
                        print(f"       Status: {status['status']}")
                        print(f"       Job ID: {status.get('job_id', 'N/A')}")
                        if endpoint:
                            print(f"       Endpoint: {endpoint}")
                
                # Show Prometheus services
                if prometheus_services:
                    print("\n  From Services:")
                    for service in prometheus_services:
                        service_id = service['service_id']
                        host = interface.servers.get_service_host(service_id)
                        endpoint = f"http://{host}:9090" if host else "Not assigned"
                        print(f"    📊 {service_id}")
                        print(f"       Status: {service['status']}")
                        print(f"       Job ID: {service['job_id']}")
                        print(f"       Endpoint: {endpoint}")
                
                print(f"\nTo query metrics, use:")
                print(f"  python main.py --query-metrics <SERVICE_ID> \"up\"")
        
        elif args.monitor_status:
            monitor_id = args.monitor_status
            print(f"Monitor status: {monitor_id}")
            
            status = interface.monitors.check_monitor_status(monitor_id)
            
            if 'error' in status:
                print(f"❌ Error: {status['error']}")
                return 1
            
            print(f"  Monitor ID: {status['monitor_id']}")
            print(f"  Status: {status['status']}")
            print(f"  Job ID: {status.get('job_id', 'N/A')}")
            
            if status.get('nodes'):
                print(f"  Nodes: {', '.join(status['nodes'])}")
            
            if status.get('submitted_at'):
                from datetime import datetime
                submit_time = datetime.fromtimestamp(status['submitted_at'])
                print(f"  Submitted: {submit_time}")
            
            # Try to get endpoint
            endpoint = interface.monitors.get_monitor_endpoint(monitor_id)
            if endpoint:
                print(f"  Endpoint: {endpoint}")
                print(f"  UI: {endpoint}/graph")
        
        elif args.stop_monitor:
            monitor_id = args.stop_monitor
            print(f"Stopping monitor: {monitor_id}")
            
            success = interface.monitors.stop_monitor(monitor_id)
            if success:
                print(f"✅ Monitor {monitor_id} stopped successfully")
            else:
                print(f"❌ Failed to stop monitor {monitor_id}")
                return 1
        
        elif args.query_metrics:
            monitor_id, query = args.query_metrics
            print(f"Querying metrics from monitor/service {monitor_id}")
            print(f"Query: {query}")
            
            # Try to query from monitors module first
            result = interface.monitors.query_metrics(monitor_id, query)
            
            # If not found in monitors, try as a service (Prometheus started via --recipe)
            if 'error' in result and 'not available' in result['error'].lower():
                print(f"Not found in monitors, trying as a service...")
                
                # Get the host for this service/monitor
                host = interface.servers.get_service_host(monitor_id)
                
                if not host:
                    # Try searching by partial ID match
                    all_services = interface.servers.list_all_services()
                    matching_services = [s for s in all_services['all_services'] 
                                       if monitor_id in s['service_id'] and 'prometheus' in s['service_id'].lower()]
                    
                    if matching_services:
                        service_id = matching_services[0]['service_id']
                        print(f"Found Prometheus service: {service_id}")
                        host = interface.servers.get_service_host(service_id)
                
                if host:
                    # Build Prometheus endpoint and query via SSH
                    endpoint = f"http://{host}:9090"
                    print(f"Using endpoint: {endpoint}")
                    
                    try:
                        import json
                        import urllib.parse
                        
                        # Build the curl command to run on the cluster
                        query_url = f"{endpoint}/api/v1/query"
                        # URL-encode the query parameter properly
                        encoded_query = urllib.parse.quote(query)
                        curl_cmd = f"curl -s '{query_url}?query={encoded_query}'"
                        
                        print(f"Executing query via SSH...")
                        exit_code, stdout, stderr = interface.ssh_client.execute_command(curl_cmd)
                        
                        if exit_code != 0:
                            print(f"❌ Query failed with exit code {exit_code}")
                            if stderr:
                                print(f"Error: {stderr}")
                            return 1
                        
                        if not stdout or not stdout.strip():
                            print(f"❌ No response from Prometheus")
                            return 1
                        
                        # Parse and display the result
                        try:
                            result = json.loads(stdout)
                            print("\nResult:")
                            print(json.dumps(result, indent=2))
                        except json.JSONDecodeError as e:
                            print(f"❌ Invalid JSON response: {e}")
                            print(f"Raw response: {stdout[:500]}")
                            return 1
                    except Exception as e:
                        print(f"❌ Error querying Prometheus: {e}")
                        return 1
                else:
                    print(f"❌ Could not find Prometheus service with ID containing: {monitor_id}")
                    print("Available services:")
                    all_services = interface.servers.list_all_services()
                    for s in all_services['all_services']:
                        if 'prometheus' in s['service_id'].lower():
                            print(f"  {s['service_id']} (Job: {s['job_id']}) - {s['status']}")
                    return 1
            elif 'error' in result:
                print(f"❌ Error: {result['error']}")
                return 1
            else:
                # Pretty print the result
                import json
                print("\nResult:")
                print(json.dumps(result, indent=2))
        
        elif args.list_available_metrics:
            service_id = args.list_available_metrics
            print(f"Listing available metrics from Prometheus service {service_id}")
            
            # Get the host for this service
            host = interface.servers.get_service_host(service_id)
            
            if not host:
                # Try searching by partial ID match
                all_services = interface.servers.list_all_services()
                matching_services = [s for s in all_services['all_services'] 
                                   if service_id in s['service_id'] and 'prometheus' in s['service_id'].lower()]
                
                if matching_services:
                    service_id = matching_services[0]['service_id']
                    print(f"Found Prometheus service: {service_id}")
                    host = interface.servers.get_service_host(service_id)
            
            if not host:
                print(f"❌ Could not find Prometheus service with ID containing: {service_id}")
                return 1
            
            # Build Prometheus endpoint
            endpoint = f"http://{host}:9090"
            print(f"Using endpoint: {endpoint}")
            
            try:
                import json
                import urllib.parse
                
                # Query Prometheus for all metric names using label_values
                query = "{__name__=~\".+\"}"
                query_url = f"{endpoint}/api/v1/series"
                encoded_query = urllib.parse.quote(query)
                curl_cmd = f"curl -s '{query_url}?match[]={encoded_query}'"
                
                print(f"Fetching metric names...")
                exit_code, stdout, stderr = interface.ssh_client.execute_command(curl_cmd)
                
                if exit_code != 0 or not stdout or not stdout.strip():
                    print(f"❌ Failed to fetch metrics")
                    return 1
                
                # Parse the result
                try:
                    result = json.loads(stdout)
                    
                    if result.get('status') != 'success':
                        print(f"❌ Error: {result.get('error', 'Unknown error')}")
                        return 1
                    
                    # Extract unique metric names
                    metric_names = set()
                    for series in result.get('data', []):
                        if '__name__' in series:
                            metric_names.add(series['__name__'])
                    
                    if not metric_names:
                        print("\n⚠️  No metrics found!")
                        print("\nThis could mean:")
                        print("  1. The target service doesn't expose Prometheus metrics")
                        print("  2. Prometheus hasn't scraped the target yet (wait a moment)")
                        print("  3. The target is down (check with: python main.py --query-metrics", service_id, "\"up\")")
                        return 0
                    
                    # Sort and display metrics
                    sorted_metrics = sorted(metric_names)
                    
                    print(f"\n✅ Found {len(sorted_metrics)} available metrics:\n")
                    
                    # Group metrics by prefix for better readability
                    grouped = {}
                    for metric in sorted_metrics:
                        prefix = metric.split('_')[0] if '_' in metric else 'other'
                        if prefix not in grouped:
                            grouped[prefix] = []
                        grouped[prefix].append(metric)
                    
                    # Display grouped metrics
                    for prefix in sorted(grouped.keys()):
                        print(f"  [{prefix}]")
                        for metric in grouped[prefix]:
                            print(f"    - {metric}")
                        print()
                    
                    print(f"\n💡 To query a metric, use:")
                    print(f"  python main.py --query-metrics {service_id} \"<metric_name>\"")
                    print(f"\nExample:")
                    if 'up' in metric_names:
                        print(f"  python main.py --query-metrics {service_id} \"up\"")
                    else:
                        print(f"  python main.py --query-metrics {service_id} \"{sorted_metrics[0]}\"")
                    
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON response: {e}")
                    print(f"Raw response: {stdout[:500]}")
                    return 1
                    
            except Exception as e:
                print(f"❌ Error listing metrics: {e}")
                return 1
        
        elif args.query_service_metrics:
            service_id, query = args.query_service_metrics
            print(f"Querying metrics from service {service_id}")
            print(f"Query: {query}")
            
            # Get service host
            host = interface.servers.get_service_host(service_id)
            
            if not host:
                print(f"❌ Could not find host for service {service_id}")
                print("Make sure the service is running and has been assigned to a node.")
                return 1
            
            # Build Prometheus endpoint (assuming port 9090 for Prometheus)
            endpoint = f"http://{host}:9090"
            print(f"Using endpoint: {endpoint}")
            
            # Query Prometheus via SSH (since we can't reach internal cluster hostnames from local machine)
            try:
                import json
                import urllib.parse
                
                # Build the curl command to run on the cluster
                query_url = f"{endpoint}/api/v1/query"
                # URL-encode the query parameter properly
                encoded_query = urllib.parse.quote(query)
                curl_cmd = f"curl -s '{query_url}?query={encoded_query}'"
                
                print(f"Executing query via SSH...")
                exit_code, stdout, stderr = interface.ssh_client.execute_command(curl_cmd)
                
                if exit_code != 0:
                    print(f"❌ Query failed with exit code {exit_code}")
                    if stderr:
                        print(f"Error: {stderr}")
                    return 1
                
                if not stdout or not stdout.strip():
                    print(f"❌ No response from Prometheus")
                    return 1
                
                # Parse and display the result
                try:
                    result = json.loads(stdout)
                    print("\nResult:")
                    print(json.dumps(result, indent=2))
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON response: {e}")
                    print(f"Raw response: {stdout[:500]}")
                    return 1
                
            except Exception as e:
                print(f"❌ Error querying Prometheus: {e}")
                return 1
        
        elif args.monitor_endpoint:
            monitor_id = args.monitor_endpoint
            
            endpoint = interface.monitors.get_monitor_endpoint(monitor_id)
            
            if endpoint:
                print(f"Prometheus endpoint for {monitor_id}:")
                print(f"  API: {endpoint}")
                print(f"  UI: {endpoint}/graph")
                print(f"  Targets: {endpoint}/targets")
            else:
                print(f"❌ Could not get endpoint for monitor {monitor_id}")
                print("The monitor may not be running or not yet assigned to a node.")
                return 1
        
        elif args.service_endpoint:
            service_id = args.service_endpoint
            
            host = interface.servers.get_service_host(service_id)
            
            if not host:
                print(f"❌ Could not get host for service {service_id}")
                print("The service may not be running or not yet assigned to a node.")
                return 1
            
            # For Prometheus services, assume port 9090
            # For other services, you might need different logic
            service_name = service_id
            if 'prometheus' in service_name.lower():
                port = 9090
                endpoint = f"http://{host}:{port}"
                print(f"Prometheus endpoint for service {service_id}:")
                print(f"  Host: {host}")
                print(f"  API: {endpoint}")
                print(f"  UI: {endpoint}/graph")
                print(f"  Targets: {endpoint}/targets")
                print(f"\nQuery metrics with:")
                print(f"  python main.py --query-service-metrics {service_id} \"up\"")
            else:
                print(f"Service endpoint for {service_id}:")
                print(f"  Host: {host}")
                print(f"\n(Port detection not implemented for non-Prometheus services)")
        
        elif args.create_tunnel:
            # Parse arguments: SERVICE_ID [LOCAL_PORT] [REMOTE_PORT]
            tunnel_args = args.create_tunnel
            
            if len(tunnel_args) < 1:
                print("❌ Error: SERVICE_ID is required")
                print("Usage: --create-tunnel SERVICE_ID [LOCAL_PORT] [REMOTE_PORT]")
                return 1
            
            service_id = tunnel_args[0]
            local_port = int(tunnel_args[1]) if len(tunnel_args) > 1 else 9090
            remote_port = int(tunnel_args[2]) if len(tunnel_args) > 2 else 9090
            
            print(f"Creating SSH tunnel for service: {service_id}")
            print(f"  Local port: {local_port}")
            print(f"  Remote port: {remote_port}")
            
            success = interface.create_ssh_tunnel(service_id, local_port, remote_port)
            
            if not success:
                print(f"❌ Failed to create SSH tunnel for service {service_id}")
                return 1
            
            print(f"\nℹ️  After running the SSH command above, you can access the service at:")
            print(f"  http://localhost:{local_port}")
            
            return 0
        
        elif args.start_session:
            service_recipe_path, client_recipe_path, prometheus_recipe_path = args.start_session
            
            print("=" * 70)
            print("AUTOMATED BENCHMARKING SESSION")
            print("=" * 70)
            print(f"Service recipe:    {service_recipe_path}")
            print(f"Client recipe:     {client_recipe_path}")
            print(f"Prometheus recipe: {prometheus_recipe_path}")
            print("=" * 70)
            
            # Validate recipe files exist
            if not os.path.exists(service_recipe_path):
                print(f"❌ Service recipe not found: {service_recipe_path}")
                return 1
            
            if not os.path.exists(client_recipe_path):
                print(f"❌ Client recipe not found: {client_recipe_path}")
                return 1
            
            if not os.path.exists(prometheus_recipe_path):
                print(f"❌ Prometheus recipe not found: {prometheus_recipe_path}")
                return 1
            
            try:
                import time
                
                # Step 1: Start the service with cAdvisor
                print("\n[1/5] Starting service with cAdvisor...")
                service_recipe = interface.load_recipe(service_recipe_path)
                
                # Verify cAdvisor is enabled
                if 'service' in service_recipe:
                    if not service_recipe['service'].get('enable_cadvisor', False):
                        print("⚠️  Warning: cAdvisor not enabled in service recipe")
                        print("   Consider adding 'enable_cadvisor: true' to the service section")
                
                service_session_id = interface.start_benchmark_session(service_recipe)
                print(f"✅ Service started: {service_session_id}")
                
                # Step 2: Wait for service to be assigned to a node
                print("\n[2/5] Waiting for service to be assigned to a node...")
                service_id = None
                service_host = None
                
                for attempt in range(18):  # Try for up to 90 seconds
                    time.sleep(5)
                    
                    # Get all running services
                    all_services = interface.servers.list_all_services()
                    
                    running_services = [s for s in all_services['all_services'] 
                                      if s['status'].upper() in ['RUNNING', 'PENDING'] 
                                      and not (s.get('job_name') and 'prometheus' in s['job_name'].lower())]
                    
                    if running_services:
                        latest_service = running_services[-1]
                        temp_service_id = latest_service['service_id']
                        host = interface.servers.get_service_host(temp_service_id)
                        if host:
                            service_id = temp_service_id
                            service_host = host
                            print(f"   ✅ Service ready: {service_id} on {host}")
                            break
                        else:
                            print(f"   Attempt {attempt + 1}/18: Service found but waiting for node assignment...")
                    else:
                        print(f"   Attempt {attempt + 1}/18: Waiting for service...")
                
                if not service_id or not service_host:
                    print("❌ Failed to detect service ID/host after 90 seconds")
                    print("   Service may still be starting. Check status with: python main.py --status")
                    return 1
                
                # Step 3: Configure Prometheus with the detected service and start it
                print(f"\n[3/5] Configuring Prometheus to monitor {service_id} on {service_host}...")
                
                # Load Prometheus recipe
                prometheus_recipe = interface.load_recipe(prometheus_recipe_path)
                
                # Update monitoring targets with the detected service ID and host
                service_name = service_recipe.get('service', {}).get('name', 'service')
                if 'service' in prometheus_recipe:
                    prometheus_recipe['service']['monitoring_targets'] = [{
                        'service_id': service_id,
                        'host': service_host,
                        'job_name': f"{service_name}-cadvisor",
                        'port': 8080
                    }]
                    print(f"✅ Prometheus configured to monitor {service_id} at {service_host}:8080")
                else:
                    print("⚠️  Warning: Invalid Prometheus recipe format")
                
                # Now start Prometheus with the correct configuration
                print("   Starting Prometheus with configured targets...")
                prometheus_session_id = interface.start_benchmark_session(prometheus_recipe)
                print(f"✅ Prometheus started: {prometheus_session_id}")
                
                # Step 4: Wait for Prometheus to be ready
                print("\n[4/5] Waiting for Prometheus to be assigned to a node...")
                prometheus_id = None
                prometheus_host = None
                
                for attempt in range(12):  # Try for up to 60 seconds
                    time.sleep(5)
                    
                    all_services = interface.servers.list_all_services()
                    prometheus_services = [s for s in all_services['all_services'] 
                                         if s.get('job_name') and 'prometheus' in s['job_name'].lower() 
                                         and s['status'].upper() in ['RUNNING', 'PENDING']]
                    
                    if prometheus_services:
                        latest_prometheus = prometheus_services[-1]
                        temp_prometheus_id = latest_prometheus['service_id']
                        host = interface.servers.get_service_host(temp_prometheus_id)
                        if host:
                            prometheus_id = temp_prometheus_id
                            prometheus_host = host
                            print(f"   ✅ Prometheus ready: {prometheus_id} on {host}")
                            break
                        else:
                            print(f"   Attempt {attempt + 1}/12: Prometheus waiting for node assignment...")
                    else:
                        print(f"   Attempt {attempt + 1}/12: Waiting for Prometheus...")
                
                if not prometheus_id or not prometheus_host:
                    print("⚠️  Warning: Prometheus not ready after 60 seconds")
                    if prometheus_id:
                        print(f"   Prometheus detected ({prometheus_id}) but still waiting for node assignment")
                    else:
                        print("   Prometheus job not found in SLURM queue")
                    print("   Continuing anyway, but monitoring may not be available immediately")
                    print("   Check status with: python main.py --status")
                
                # Step 5: Start the client benchmark targeting the service
                print(f"\n[5/5] Starting client benchmark targeting {service_id}...")
                
                # Load client recipe
                client_recipe = interface.load_recipe(client_recipe_path)
                
                # Determine service port from service recipe (common ports)
                service_name = service_recipe.get('service', {}).get('name', 'service')
                service_port = None
                
                if 'ollama' in service_name.lower():
                    service_port = 11434
                elif 'redis' in service_name.lower():
                    service_port = 6379
                elif 'chroma' in service_name.lower():
                    service_port = 8000
                else:
                    # Try to get from ports section
                    ports = service_recipe.get('service', {}).get('ports', [])
                    if ports:
                        service_port = ports[0]
                    else:
                        service_port = 8000  # Default fallback
                
                service_endpoint = f"http://{service_host}:{service_port}"
                print(f"   Service endpoint: {service_endpoint}")
                
                # Start client with target service
                client_id = interface.clients.start_client(client_recipe, service_id, service_host)
                print(f"✅ Client started: {client_id}")
                
                # Create SSH tunnel to Prometheus
                if prometheus_id and prometheus_host:
                    print(f"\nCreating SSH tunnel to Prometheus...")
                    success = interface.create_ssh_tunnel(prometheus_id, 9090, 9090)
                    
                    if not success:
                        print(f"⚠️  Warning: Failed to create SSH tunnel, but session is complete")
                else:
                    print(f"\n⚠️  Skipping SSH tunnel creation (Prometheus not ready)")
                
                # Final summary
                print("\n" + "=" * 70)
                print("BENCHMARKING SESSION COMPLETE")
                print("=" * 70)
                print(f"Service ID:    {service_id}")
                print(f"Service Host:  {service_host}:{service_port}")
                print(f"Client ID:     {client_id}")
                print(f"Prometheus ID: {prometheus_id}")
                print(f"Prometheus UI: http://localhost:9090 (after tunnel setup)")
                print("\nSession Components:")
                print(f"  1. Service '{service_name}' with cAdvisor monitoring")
                print(f"  2. Client benchmark running against service")
                print(f"  3. Prometheus collecting metrics from cAdvisor")
                print(f"\nTo access Prometheus UI:")
                print(f"  1. Run the SSH command shown above in a separate terminal")
                print(f"  2. Open http://localhost:9090 in your browser")
                print(f"\nTo query metrics:")
                print(f"  python main.py --query-metrics {prometheus_id} \"up\"")
                print(f"  python main.py --query-metrics {prometheus_id} \"container_memory_usage_bytes\"")
                print(f"\nTo check client status:")
                print(f"  python main.py --status")
                print(f"\nTo stop everything:")
                print(f"  python main.py --stop-service {prometheus_id}")
                print(f"  python main.py --stop-service {client_id}")
                print(f"  python main.py --stop-service {service_id}")
                print(f"  # Or use: python main.py --stop-all-services")
                print("=" * 70)
                
                return 0
                
            except Exception as e:
                print(f"\n❌ Error during automated session setup: {e}")
                import traceback
                traceback.print_exc()
                return 1
        
        elif args.start_monitoring:
            service_recipe_path, prometheus_recipe_path = args.start_monitoring
            
            print("=" * 70)
            print("AUTOMATED MONITORING SETUP (DEPRECATED)")
            print("⚠️  Note: Use --start-session for complete workflow with client")
            print("=" * 70)
            print(f"Service recipe: {service_recipe_path}")
            print(f"Prometheus recipe: {prometheus_recipe_path}")
            print("=" * 70)
            
            # Validate recipe files exist
            if not os.path.exists(service_recipe_path):
                print(f"❌ Service recipe not found: {service_recipe_path}")
                return 1
            
            if not os.path.exists(prometheus_recipe_path):
                print(f"❌ Prometheus recipe not found: {prometheus_recipe_path}")
                return 1
            
            try:
                import time
                
                # Step 1: Start the service with cAdvisor
                print("\n[1/5] Starting service with cAdvisor...")
                service_recipe = interface.load_recipe(service_recipe_path)
                
                # Verify cAdvisor is enabled
                if 'service' in service_recipe:
                    if not service_recipe['service'].get('enable_cadvisor', False):
                        print("⚠️  Warning: cAdvisor not enabled in service recipe")
                        print("   Consider adding 'enable_cadvisor: true' to the service section")
                
                service_session_id = interface.start_benchmark_session(service_recipe)
                print(f"✅ Service started: {service_session_id}")
                
                # Step 2: Wait for service to be assigned to a node and get service ID
                print("\n[2/5] Waiting for service to be assigned to a node...")
                service_id = None
                
                for attempt in range(12):  # Try for up to 60 seconds
                    time.sleep(5)
                    
                    # Get all running services
                    all_services = interface.servers.list_all_services()
                    
                    # Find the most recently started service (should be ours)
                    running_services = [s for s in all_services['all_services'] 
                                      if s['status'].upper() in ['RUNNING', 'PENDING']]
                    
                    if running_services:
                        # Get the last service (most recent)
                        latest_service = running_services[-1]
                        service_id = latest_service['service_id']
                        
                        # Check if it has a host assigned
                        host = interface.servers.get_service_host(service_id)
                        if host:
                            print(f"✅ Service assigned: {service_id} on {host}")
                            break
                        else:
                            print(f"   Attempt {attempt + 1}/12: Service {service_id} not yet assigned to node...")
                    else:
                        print(f"   Attempt {attempt + 1}/12: No running services found yet...")
                
                if not service_id:
                    print("❌ Failed to detect service ID after 60 seconds")
                    print("   Service may still be starting. Check status with: python main.py --status")
                    return 1
                
                # Step 3: Update Prometheus recipe with the detected service ID
                print(f"\n[3/5] Configuring Prometheus to monitor {service_id}...")
                
                # Load Prometheus recipe
                prometheus_recipe = interface.load_recipe(prometheus_recipe_path)
                
                # Update monitoring targets with the detected service ID
                if 'service' in prometheus_recipe:
                    if 'monitoring_targets' not in prometheus_recipe['service']:
                        prometheus_recipe['service']['monitoring_targets'] = []
                    
                    # Check if service_id already exists in targets
                    existing_target = None
                    for target in prometheus_recipe['service']['monitoring_targets']:
                        if target.get('service_id') == service_id:
                            existing_target = target
                            break
                    
                    if not existing_target:
                        # Add new monitoring target
                        service_name = service_recipe.get('service', {}).get('name', 'service')
                        prometheus_recipe['service']['monitoring_targets'].append({
                            'service_id': service_id,
                            'job_name': f"{service_name}-cadvisor",
                            'port': 8080
                        })
                        print(f"✅ Added {service_id} to monitoring targets")
                    else:
                        print(f"✅ Service {service_id} already in monitoring targets")
                else:
                    print("❌ Invalid Prometheus recipe: missing 'service' section")
                    return 1
                
                # Step 4: Start Prometheus
                print(f"\n[4/5] Starting Prometheus...")
                prometheus_session_id = interface.start_benchmark_session(prometheus_recipe)
                print(f"✅ Prometheus started: {prometheus_session_id}")
                
                # Wait for Prometheus to be assigned
                print("   Waiting for Prometheus to be assigned to a node...")
                prometheus_id = None
                
                for attempt in range(12):  # Try for up to 60 seconds
                    time.sleep(5)
                    
                    all_services = interface.servers.list_all_services()
                    prometheus_services = [s for s in all_services['all_services'] 
                                         if 'prometheus' in s['service_id'].lower() and 
                                         s['status'].upper() in ['RUNNING', 'PENDING']]
                    
                    if prometheus_services:
                        latest_prometheus = prometheus_services[-1]
                        prometheus_id = latest_prometheus['service_id']
                        
                        host = interface.servers.get_service_host(prometheus_id)
                        if host:
                            print(f"✅ Prometheus assigned: {prometheus_id} on {host}")
                            break
                        else:
                            print(f"   Attempt {attempt + 1}/12: Prometheus not yet assigned to node...")
                    else:
                        print(f"   Attempt {attempt + 1}/12: Prometheus not detected yet...")
                
                if not prometheus_id:
                    print("❌ Failed to detect Prometheus ID after 60 seconds")
                    print("   Prometheus may still be starting. Check status with: python main.py --status")
                    return 1
                
                # Step 5: Create SSH tunnel
                print(f"\n[5/5] Creating SSH tunnel to Prometheus...")
                success = interface.create_ssh_tunnel(prometheus_id, 9090, 9090)
                
                if not success:
                    print(f"❌ Failed to create SSH tunnel")
                    return 1
                
                # Final summary
                print("\n" + "=" * 70)
                print("MONITORING SETUP COMPLETE")
                print("=" * 70)
                print(f"Service ID: {service_id}")
                print(f"Prometheus ID: {prometheus_id}")
                print(f"\nTo access Prometheus UI:")
                print(f"  1. Run the SSH command shown above in a separate terminal")
                print(f"  2. Open http://localhost:9090 in your browser")
                print(f"\nTo query metrics:")
                print(f"  python main.py --query-metrics {prometheus_id} \"up\"")
                print(f"  python main.py --query-metrics {prometheus_id} \"container_memory_usage_bytes\"")
                print(f"\nTo stop everything:")
                print(f"  python main.py --stop-service {prometheus_id}")
                print(f"  python main.py --stop-service {service_id}")
                print("=" * 70)
                
                return 0
                
            except Exception as e:
                print(f"\n❌ Error during automated monitoring setup: {e}")
                import traceback
                traceback.print_exc()
                return 1
        
        elif args.recipe:
            if not os.path.exists(args.recipe):
                logger.error(f"Recipe file not found: {args.recipe}")
                return 1
            
            logger.info(f"Loading recipe: {args.recipe}")
            recipe = interface.load_recipe(args.recipe)
            
            # Check if this is a client-only recipe
            if 'client' in recipe and 'service' not in recipe:
                logger.info("Client-only recipe detected")
                
                # Check for target service or endpoint
                target_service_id = args.target_service
                target_endpoint = args.target_endpoint
                
                if not target_service_id and not target_endpoint:
                    # List available services to help user choose
                    all_services = interface.servers.list_all_services()
                    
                    if not all_services['all_services']:
                        print("❌ No running services found. Please:")
                        print("  1. Start a service first with a service recipe, or")
                        print("  2. Use --target-endpoint to specify a direct endpoint, or") 
                        print("  3. Use --target-service to specify a service ID")
                        return 1
                    
                    print("Available running services:")
                    for i, service in enumerate(all_services['all_services'], 1):
                        status_info = f"{service['status']} (Job: {service['job_id']})"
                        print(f"  {i}. {service['service_id']} - {status_info}")
                    
                    print("\nTo target a service, use:")
                    print(f"  python main.py --recipe {args.recipe} --target-service <SERVICE_ID>")
                    print("\nOr to use a direct endpoint:")
                    print(f"  python main.py --recipe {args.recipe} --target-endpoint http://node-name:11434")
                    return 1
                
                # Start client with target specification
                logger.info("Starting client with target specification")
                target_service_host = None
                
                if target_endpoint:
                    # Extract host from endpoint for compatibility
                    import re
                    match = re.match(r'https?://([^:]+)', target_endpoint)
                    if match:
                        target_service_host = match.group(1)
                    
                    # Add endpoint to recipe parameters
                    if 'client' in recipe and 'parameters' in recipe['client']:
                        recipe['client']['parameters']['endpoint'] = target_endpoint
                    
                    logger.info(f"Using direct endpoint: {target_endpoint}")
                    client_id = interface.clients.start_client(recipe, target_service_id or "manual", target_service_host)
                    
                elif target_service_id:
                    # Resolve service host
                    logger.info(f"Resolving host for service: {target_service_id}")
                    
                    import time
                    for attempt in range(6):  # Try for up to 30 seconds
                        target_service_host = interface.servers.get_service_host(target_service_id)
                        if target_service_host:
                            logger.info(f"✅ Resolved service {target_service_id} to host: {target_service_host}")
                            break
                        else:
                            logger.info(f"🔄 Attempt {attempt + 1}/6: Service host not yet available, waiting 5s...")
                            time.sleep(5)
                    
                    if not target_service_host:
                        print(f"❌ Could not resolve host for service {target_service_id}")
                        print("The service might not be running or not yet assigned to a node.")
                        return 1
                    
                    client_id = interface.clients.start_client(recipe, target_service_id, target_service_host)
                
                print(f"Client started: {client_id}")
                print("Monitor the job status through SLURM or check logs.")
            
            # Check if this is a service-only recipe (e.g., Prometheus monitoring)
            elif 'service' in recipe and 'client' not in recipe:
                logger.info("Service-only recipe detected")
                
                # Check if target service is specified (for monitoring services like Prometheus)
                target_service_id = args.target_service
                
                if target_service_id:
                    logger.info(f"Starting service with target: {target_service_id}")
                    # Pass target_service_id to the orchestrator
                    session_id = interface.start_benchmark_session(recipe, target_service_id)
                else:
                    logger.info("Starting service without specific target")
                    session_id = interface.start_benchmark_session(recipe)
                
                print(f"Service started: {session_id}")
                print("Monitor the job status through SLURM or check logs.")
                
            else:
                # Original combined recipe logic
                logger.info("Starting benchmark session")
                session_id = interface.start_benchmark_session(recipe)
                
                print(f"Benchmark session started: {session_id}")
                print("Monitor the job status through SLURM or check logs.")
        
        else:
            # Interactive mode - enhanced with service management
            print("HPC Orchestrator - Interactive Mode")
            print("Available commands:")
            print("  1. List services")
            print("  2. List clients") 
            print("  3. Show status")
            print("  4. Stop service")
            print("  5. Stop all services")
            print("  6. Show running sessions")
            print("  7. Debug services")
            print("  8. List all services")
            print("  9. List monitors")
            print("  10. Monitor status")
            print("  11. Query metrics")
            print("  12. Exit")
            
            while True:
                try:
                    choice = input("\nEnter command (1-12): ").strip()
                    if choice == '1':
                        services = interface.servers.list_available_services()
                        print("Available Services:", services)
                    elif choice == '2':
                        clients = interface.clients.list_available_clients()
                        print("Available Clients:", clients)
                    elif choice == '3':
                        status = interface.get_system_status()
                        print(f"SSH Connected: {status['ssh_connected']}")
                        print(f"Tracked Services: {status['services']['total_services']}")
                        print(f"Tracked Clients: {status['clients']['total_clients']}")
                        
                        if status['services']['services']:
                            print("\nRunning Services:")
                            for service_id, service_info in status['services']['services'].items():
                                print(f"  {service_id}: {service_info.get('status', 'unknown')} (Job: {service_info.get('job_id', 'N/A')})")
                    elif choice == '4':
                        # Stop specific service
                        all_services = interface.servers.list_all_services()
                        
                        if not all_services['all_services']:
                            print("No services are currently available")
                            continue
                        
                        print("Available services:")
                        for i, service in enumerate(all_services['all_services'], 1):
                            status_info = f"{service['status']} (Job: {service['job_id']})"
                            service_type = service['type']
                            print(f"  {i}. {service['service_id']} - {status_info} [{service_type}]")
                        
                        try:
                            choice_num = int(input("Enter service number to stop (or 0 to cancel): ").strip())
                            if choice_num == 0:
                                continue
                            elif 1 <= choice_num <= len(all_services['all_services']):
                                selected_service = all_services['all_services'][choice_num - 1]
                                service_id = selected_service['service_id']
                                print(f"Stopping service: {service_id}")
                                if interface.stop_service(service_id):
                                    print(f"✅ Service {service_id} stopped successfully")
                                else:
                                    print(f"❌ Failed to stop service {service_id}")
                            else:
                                print("Invalid service number")
                        except ValueError:
                            print("Please enter a valid number")
                    elif choice == '5':
                        # Stop all services
                        all_services = interface.servers.list_all_services()
                        
                        if not all_services['all_services']:
                            print("No services found")
                            continue
                        
                        active_services = [s for s in all_services['all_services'] 
                                         if s['status'].upper() in ['RUNNING', 'PENDING']]
                        
                        if not active_services:
                            print("No active services found")
                            continue
                        
                        print(f"Found {len(active_services)} active services:")
                        for service in active_services:
                            print(f"  - {service['service_id']} ({service['status']})")
                        
                        confirm = input(f"Stop {len(active_services)} active services? (y/N): ").strip().lower()
                        if confirm == 'y':
                            results = interface.stop_all_services()
                            
                            if 'error' in results:
                                print(f"❌ Error: {results['error']}")
                            else:
                                print(f"✅ Stopped {results['stopped_services']}/{results['total_services']} services")
                                if results['failed_services'] > 0:
                                    print(f"❌ Failed to stop {results['failed_services']} services")
                        else:
                            print("Operation cancelled")
                    elif choice == '6':
                        # Show running sessions
                        sessions = interface._active_sessions
                        if not sessions:
                            print("No active sessions")
                        else:
                            print("Active sessions:")
                            for session_id, session_info in sessions.items():
                                print(f"  {session_id}: {session_info.get('status', 'unknown')} - Services: {len(session_info.get('services', []))}, Clients: {len(session_info.get('clients', []))}")
                    elif choice == '7':
                        # Debug services
                        print("Debug information for services:")
                        debug_info = interface.debug_services()
                        
                        if 'error' in debug_info:
                            print(f"❌ Error: {debug_info['error']}")
                        else:
                            print(f"\nTracked Services: {len(debug_info['tracked_services'])}")
                            print(f"SLURM Jobs: {len(debug_info['slurm_jobs'])}")
                            print(f"Service Mapping: {len(debug_info['service_mapping'])} entries")
                            
                            if debug_info['tracked_services']:
                                print("\nTracked Services:")
                                for service_id, info in debug_info['tracked_services'].items():
                                    print(f"  {service_id} -> Job {info['job_id']} ({info['status']})")
                    elif choice == '8':
                        # List all services
                        all_services = interface.servers.list_all_services()
                        
                        print(f"All Services Summary:")
                        print(f"  Tracked: {len(all_services['tracked_services'])}")
                        print(f"  SLURM-only: {len(all_services['slurm_services'])}")
                        print(f"  Total: {len(all_services['all_services'])}")
                        
                        if all_services['all_services']:
                            print("\nAll Services:")
                            for service in all_services['all_services']:
                                type_marker = "📊" if service['type'] == 'tracked' else "🔧"
                                print(f"  {type_marker} {service['service_id']} (Job: {service['job_id']}) - {service['status']}")
                    elif choice == '9':
                        # List monitors
                        running_monitors = interface.monitors.list_running_monitors()
                        
                        if not running_monitors:
                            print("No running monitors")
                        else:
                            print(f"Running monitors ({len(running_monitors)}):")
                            for monitor_id in running_monitors:
                                status = interface.monitors.check_monitor_status(monitor_id)
                                endpoint = interface.monitors.get_monitor_endpoint(monitor_id)
                                print(f"  📊 {monitor_id} - {status['status']}")
                                if endpoint:
                                    print(f"     {endpoint}")
                    elif choice == '10':
                        # Monitor status
                        running_monitors = interface.monitors.list_running_monitors()
                        
                        if not running_monitors:
                            print("No running monitors")
                            continue
                        
                        print("Available monitors:")
                        for i, monitor_id in enumerate(running_monitors, 1):
                            print(f"  {i}. {monitor_id}")
                        
                        try:
                            choice_num = int(input("Enter monitor number (or 0 to cancel): ").strip())
                            if choice_num == 0:
                                continue
                            elif 1 <= choice_num <= len(running_monitors):
                                monitor_id = running_monitors[choice_num - 1]
                                status = interface.monitors.check_monitor_status(monitor_id)
                                
                                print(f"\nMonitor: {monitor_id}")
                                print(f"  Status: {status['status']}")
                                print(f"  Job ID: {status.get('job_id', 'N/A')}")
                                
                                endpoint = interface.monitors.get_monitor_endpoint(monitor_id)
                                if endpoint:
                                    print(f"  Endpoint: {endpoint}")
                                    print(f"  UI: {endpoint}/graph")
                            else:
                                print("Invalid monitor number")
                        except ValueError:
                            print("Please enter a valid number")
                    elif choice == '11':
                        # Query metrics
                        running_monitors = interface.monitors.list_running_monitors()
                        
                        if not running_monitors:
                            print("No running monitors")
                            continue
                        
                        print("Available monitors:")
                        for i, monitor_id in enumerate(running_monitors, 1):
                            print(f"  {i}. {monitor_id}")
                        
                        try:
                            choice_num = int(input("Enter monitor number (or 0 to cancel): ").strip())
                            if choice_num == 0:
                                continue
                            elif 1 <= choice_num <= len(running_monitors):
                                monitor_id = running_monitors[choice_num - 1]
                                query = input("Enter PromQL query (e.g., 'up'): ").strip()
                                
                                if query:
                                    result = interface.monitors.query_metrics(monitor_id, query)
                                    
                                    if 'error' in result:
                                        print(f"❌ Error: {result['error']}")
                                    else:
                                        import json
                                        print("\nResult:")
                                        print(json.dumps(result, indent=2))
                            else:
                                print("Invalid monitor number")
                        except ValueError:
                            print("Please enter a valid number")
                    elif choice == '12':
                        break
                    else:
                        print("Invalid choice. Please enter 1-12.")
                except KeyboardInterrupt:
                    print("\nExiting...")
                    break
    
    except ImportError as e:
        logger.error(f"Import error: {e}")
        print("\n❌ Failed to import required modules.")
        print("Please install dependencies: pip install -r requirements.txt")
        return 1
    
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())