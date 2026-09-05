-- Sample data + a read-only account, mounted identically into both mysql-1
-- and mysql-2 - the official MySQL image runs init scripts against the
-- database named by MYSQL_DATABASE, so this applies to whichever of
-- testdb1/testdb2 that container was started with.

CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer VARCHAR(255) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO orders (customer, amount, status) VALUES
    ('Alice', 19.99, 'paid'),
    ('Bob', 42.50, 'paid'),
    ('Carol', 5.00, 'pending');

CREATE USER IF NOT EXISTS 'toolbox_ro'@'%' IDENTIFIED BY 'toolbox_ro';
GRANT SELECT ON *.* TO 'toolbox_ro'@'%';
FLUSH PRIVILEGES;
