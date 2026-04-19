-- Enable uuid-ossp extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create test database for pytest
SELECT 'CREATE DATABASE aujasya_test'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'aujasya_test')\gexec
