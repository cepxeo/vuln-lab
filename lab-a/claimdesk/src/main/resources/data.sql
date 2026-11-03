-- Synthetic seed for the benchmark target. Passwords are unsalted MD5 (a
-- deliberately weak legacy scheme) so the scanner can flag weak credentials.
INSERT INTO users (username, password, full_name, email, phone, role) VALUES
 ('admin',    '0192023a7bbd73250516f069df18b500', 'Test Admin',    'admin@example.test',    '000-0001', 'admin'),
 ('j.adjust', 'f065d609e55983bc6087c073c91c9bc7', 'Test Adjuster', 'adjuster@example.test', '000-0002', 'adjuster'),
 ('adjuster', 'b27a0f171226cf184cbe16721f1cea90', 'Shared Desk',   'desk@example.test',     '000-0003', 'adjuster'),
 ('cust1',    'b56e0b4ea4962283bee762525c2d490f', 'Test Customer One', 'cust1@example.test', '000-0004', 'customer'),
 ('cust2',    'd41e98d1eafa6d6011d3a70f1a5b92f0', 'Test Customer Two', 'cust2@example.test', '000-0005', 'customer'),
 ('cust3',    '2be3e1b644095f47ffc18c6ce695c668', 'Test Customer Three', 'cust3@example.test', '000-0006', 'customer');

INSERT INTO policies (policy_no, user_id, holder_name, product, premium, postcode, status) VALUES
 ('HL-1001', 4, 'Test Customer One', 'Home Cover',  420.00, 'ZZ1 1AA', 'active'),
 ('HL-1002', 5, 'Test Customer Two', 'Motor Cover', 610.00, 'ZZ2 2BB', 'active'),
 ('HL-1003', 6, 'Test Customer Three', 'Travel Cover', 95.00, 'ZZ3 3CC', 'lapsed');

INSERT INTO claims (claim_no, policy_no, user_id, title, description, amount, status, adjuster_notes, bank_iban) VALUES
 ('CLM-5001', 'HL-1001', 4, 'Water damage kitchen', 'Burst pipe under sink.', 1800.00, 'Under review', 'awaiting plumber invoice', 'TEST00IBAN0000000001'),
 ('CLM-5002', 'HL-1002', 5, 'Windscreen crack',     'Stone chip on motorway.', 240.00, 'Approved', 'fast-track', 'TEST00IBAN0000000002'),
 ('CLM-5003', 'HL-1003', 6, 'Lost luggage',         'Bag not delivered at airport.', 500.00, 'Submitted', '', 'TEST00IBAN0000000003');

INSERT INTO documents (claim_id, filename) VALUES
 (1, 'plumber-estimate.txt'),
 (2, 'windscreen-photo.txt');

INSERT INTO templates (name, body) VALUES
 ('approval', 'Dear [[name]], your claim [[claim]] has been approved.'),
 ('request-info', 'Dear [[name]], we need more detail on claim [[claim]].');
