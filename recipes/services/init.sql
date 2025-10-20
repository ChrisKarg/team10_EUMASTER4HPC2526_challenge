-- init.sql
-- MySQL initialization script to grant remote access

-- Create user with access from any host
CREATE USER IF NOT EXISTS 'benchmark_user'@'%' IDENTIFIED BY 'benchmark_pass';

-- Grant all privileges on the benchmark database
GRANT ALL PRIVILEGES ON benchmark_db.* TO 'benchmark_user'@'%';

-- Also grant privileges to localhost for good measure
CREATE USER IF NOT EXISTS 'benchmark_user'@'localhost' IDENTIFIED BY 'benchmark_pass';
GRANT ALL PRIVILEGES ON benchmark_db.* TO 'benchmark_user'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;

-- Optional: Create the benchmark table ahead of time
USE benchmark_db;
CREATE TABLE IF NOT EXISTS benchmark_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    value INT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;