CREATE TABLE users (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(64) NOT NULL UNIQUE,
  password VARCHAR(64) NOT NULL,
  full_name VARCHAR(128),
  email VARCHAR(128),
  phone VARCHAR(32),
  role VARCHAR(16) NOT NULL DEFAULT 'customer',
  last_login TIMESTAMP
);

CREATE TABLE policies (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  policy_no VARCHAR(32) NOT NULL UNIQUE,
  user_id BIGINT,
  holder_name VARCHAR(128),
  product VARCHAR(64),
  premium DECIMAL(10,2),
  postcode VARCHAR(16),
  status VARCHAR(16)
);

CREATE TABLE claims (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  claim_no VARCHAR(32) NOT NULL,
  policy_no VARCHAR(32),
  user_id BIGINT NOT NULL,
  title VARCHAR(200),
  description CLOB,
  amount DECIMAL(10,2),
  status VARCHAR(24) DEFAULT 'Submitted',
  adjuster_notes CLOB,
  bank_iban VARCHAR(40),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE documents (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  claim_id BIGINT,
  filename VARCHAR(200)
);

CREATE TABLE templates (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(64),
  body CLOB
);
