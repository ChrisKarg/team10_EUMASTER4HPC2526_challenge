#!/usr/bin/env python3
"""
MySQL Benchmark Script

This script performs benchmark tests on a MySQL database by simulating multiple
concurrent connections and measuring performance metrics.
"""

import argparse
import json
import logging
import mysql.connector
import time
import threading
from datetime import datetime
from typing import Dict, List, Any
import statistics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MySQLBenchmark:
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        num_connections: int,
        transactions_per_client: int
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.num_connections = num_connections
        self.transactions_per_client = transactions_per_client
        self.results: List[Dict[str, Any]] = []
        self.lock = threading.Lock()

    def setup_database(self) -> None:
        """Create test table and initial data"""
        connection = self._create_connection()
        cursor = connection.cursor()

        try:
            # Create test table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS benchmark_data (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100),
                    value INT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create test data
            cursor.execute("SELECT COUNT(*) FROM benchmark_data")
            count = cursor.fetchone()[0]

            if count == 0:
                logger.info("Inserting initial test data...")
                for i in range(1000):
                    cursor.execute(
                        "INSERT INTO benchmark_data (name, value) VALUES (%s, %s)",
                        (f"test_item_{i}", i)
                    )

            connection.commit()
            logger.info("Database setup completed successfully")

        except Exception as e:
            logger.error(f"Error setting up database: {e}")
            raise

        finally:
            cursor.close()
            connection.close()

    def _create_connection(self) -> mysql.connector.MySQLConnection:
        """Create a new database connection"""
        return mysql.connector.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database
        )

    def run_client_workload(self, client_id: int) -> None:
        """Execute benchmark workload for a single client"""
        connection = self._create_connection()
        cursor = connection.cursor()

        try:
            start_time = time.time()
            transaction_times = []

            for i in range(self.transactions_per_client):
                tx_start = time.time()

                # Perform a mix of operations
                # 1. Insert new record
                cursor.execute(
                    "INSERT INTO benchmark_data (name, value) VALUES (%s, %s)",
                    (f"client_{client_id}_item_{i}", i)
                )

                # 2. Read some records
                cursor.execute(
                    "SELECT * FROM benchmark_data WHERE value > %s LIMIT 5",
                    (i % 100,)
                )
                cursor.fetchall()

                # 3. Update a record
                cursor.execute(
                    "UPDATE benchmark_data SET value = %s WHERE name = %s",
                    (i * 2, f"client_{client_id}_item_{i}")
                )

                connection.commit()
                tx_end = time.time()
                transaction_times.append(tx_end - tx_start)

            end_time = time.time()
            total_time = end_time - start_time

            # Record results
            with self.lock:
                self.results.append({
                    'client_id': client_id,
                    'transactions': self.transactions_per_client,
                    'total_time': total_time,
                    'avg_transaction_time': statistics.mean(transaction_times),
                    'min_transaction_time': min(transaction_times),
                    'max_transaction_time': max(transaction_times),
                    'transactions_per_second': self.transactions_per_client / total_time
                })

        except Exception as e:
            logger.error(f"Error in client {client_id}: {e}")
            with self.lock:
                self.results.append({
                    'client_id': client_id,
                    'error': str(e)
                })

        finally:
            cursor.close()
            connection.close()

    def run_benchmark(self) -> Dict[str, Any]:
        """Run the complete benchmark with multiple clients"""
        logger.info(f"Starting benchmark with {self.num_connections} clients")
        start_time = time.time()

        # Create and start client threads
        threads = []
        for i in range(self.num_connections):
            thread = threading.Thread(target=self.run_client_workload, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all clients to complete
        for thread in threads:
            thread.join()

        end_time = time.time()
        total_time = end_time - start_time

        # Calculate aggregate statistics
        successful_results = [r for r in self.results if 'error' not in r]
        total_transactions = sum(r['transactions'] for r in successful_results)
        total_tps = sum(r['transactions_per_second'] for r in successful_results)
        
        avg_transaction_times = [r['avg_transaction_time'] for r in successful_results]
        if avg_transaction_times:
            overall_avg_transaction_time = statistics.mean(avg_transaction_times)
        else:
            overall_avg_transaction_time = 0

        # Compile final results
        benchmark_results = {
            'timestamp': datetime.now().isoformat(),
            'configuration': {
                'num_connections': self.num_connections,
                'transactions_per_client': self.transactions_per_client,
                'host': self.host,
                'port': self.port,
                'database': self.database
            },
            'overall_results': {
                'total_duration': total_time,
                'total_transactions': total_transactions,
                'total_transactions_per_second': total_tps,
                'average_transaction_time': overall_avg_transaction_time,
                'successful_clients': len(successful_results),
                'failed_clients': len(self.results) - len(successful_results)
            },
            'client_results': self.results
        }

        logger.info(f"Benchmark completed in {total_time:.2f} seconds")
        logger.info(f"Total transactions: {total_transactions}")
        logger.info(f"Total TPS: {total_tps:.2f}")

        return benchmark_results

def main():
    parser = argparse.ArgumentParser(description='MySQL Benchmark Tool')
    parser.add_argument('--endpoint', required=True, help='MySQL endpoint (host:port)')
    parser.add_argument('--user', default='benchmark_user', help='MySQL user')
    parser.add_argument('--password', default='benchmark_pass', help='MySQL password')
    parser.add_argument('--database', default='benchmark_db', help='MySQL database')
    parser.add_argument('--num-connections', type=int, default=10, help='Number of concurrent connections')
    parser.add_argument('--transactions-per-client', type=int, default=1000, help='Transactions per client')
    parser.add_argument('--output-file', default='/tmp/mysql_benchmark_results.json', help='Output file for results')

    args = parser.parse_args()

    # Parse endpoint
    host, port = args.endpoint.split(':')
    port = int(port)

    try:
        # Create and run benchmark
        benchmark = MySQLBenchmark(
            host=host,
            port=port,
            user=args.user,
            password=args.password,
            database=args.database,
            num_connections=args.num_connections,
            transactions_per_client=args.transactions_per_client
        )

        # Setup database (create tables, initial data)
        benchmark.setup_database()

        # Run benchmark
        results = benchmark.run_benchmark()

        # Save results
        with open(args.output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {args.output_file}")

    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        raise

if __name__ == '__main__':
    main()