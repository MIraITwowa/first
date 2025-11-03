-- Initialize MySQL database for crossborder trade
-- This script runs when the MySQL container starts for the first time

-- Set character set and collation
ALTER DATABASE crossborder_trade CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create additional indexes if needed (Django will create most)
-- These are examples of performance optimizations

-- Disable foreign key checks temporarily for faster import
SET FOREIGN_KEY_CHECKS = 0;

-- Re-enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;