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
            print("  9. Exit")
            
            while True:
                try:
                    choice = input("\nEnter command (1-9): ").strip()
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
                        break
                    else:
                        print("Invalid choice. Please enter 1-9.")
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