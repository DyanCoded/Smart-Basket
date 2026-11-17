-- scripts/seed.sql
-- Smart Basket: Catalog Seeding & Multi-Store Pricing Test Data
-- PostgreSQL 16 compatible idempotent seed script

-- Clean up existing data in reverse order of foreign key dependencies
TRUNCATE TABLE price_history, basket_items, baskets, store_prices, products, categories, stores, retailers CASCADE;

--------------------------------------------------------------------------------
-- 1. Retailers (South African Supermarket Chains)
--------------------------------------------------------------------------------
INSERT INTO retailers (id, name, slug, created_at) VALUES
  ('3ae15000-8907-5fb5-9904-c47dba4bcc3e', 'Checkers', 'checkers', NOW()),
  ('bb29a5ff-6ca1-515e-aa5c-641225dfa51c', 'Woolworths Food', 'woolworths-food', NOW()),
  ('dae4891a-2bf0-5116-9688-9faf01f18567', 'Pick n Pay', 'pick-n-pay', NOW()),
  ('5f8147c2-db0d-51f1-b4b2-9cf0d4e975ad', 'SPAR', 'spar', NOW()),
  ('de4bf312-1b55-5729-9069-8de6e816d541', 'Shoprite', 'shoprite', NOW());

--------------------------------------------------------------------------------
-- 2. Stores (Retailer Branches across Johannesburg and Cape Town)
--------------------------------------------------------------------------------
INSERT INTO stores (id, retailer_id, name, branch_code, address, is_active, created_at) VALUES
  ('a3b3c260-9228-54dd-ba6d-3b216931987e', '3ae15000-8907-5fb5-9904-c47dba4bcc3e', 'Checkers Sandton City', 'CHK-JHB-001', 'Sandton City Shopping Centre, Rivonia Rd, Sandton, Johannesburg', TRUE, NOW()),
  ('437b5aae-0881-59ca-8f79-7968cca50fff', '3ae15000-8907-5fb5-9904-c47dba4bcc3e', 'Checkers Sea Point', 'CHK-CPT-002', 'Regent Rd, Sea Point, Cape Town', TRUE, NOW()),
  ('aafe584e-791a-5f4c-92c3-2c8c14365911', 'bb29a5ff-6ca1-515e-aa5c-641225dfa51c', 'Woolworths Sandton City', 'WW-JHB-001', 'Sandton City Mall, 83 Rivonia Rd, Sandton, Johannesburg', TRUE, NOW()),
  ('d0627e50-99f3-50af-b4c4-0a7243d480e2', 'bb29a5ff-6ca1-515e-aa5c-641225dfa51c', 'Woolworths V&A Waterfront', 'WW-CPT-002', 'Victoria Wharf Shopping Centre, V&A Waterfront, Cape Town', TRUE, NOW()),
  ('03e133be-5dbc-5024-b413-95596e909a67', 'dae4891a-2bf0-5116-9688-9faf01f18567', 'Pick n Pay On Nicol', 'PNP-JHB-001', 'William Nicol Dr & Republic Rd, Bryanston, Johannesburg', TRUE, NOW()),
  ('78e782c3-0337-5193-8cf1-4eb321341c34', 'dae4891a-2bf0-5116-9688-9faf01f18567', 'Pick n Pay Claremont', 'PNP-CPT-002', 'Main Rd, Claremont, Cape Town', TRUE, NOW()),
  ('b7a02c2b-3113-515d-a39f-8b2299713850', '5f8147c2-db0d-51f1-b4b2-9cf0d4e975ad', 'SUPERSPAR Rosebank', 'SPR-JHB-001', 'The Zone @ Rosebank, Oxford Rd, Rosebank, Johannesburg', TRUE, NOW()),
  ('d283369e-f1c1-5e89-9bf6-a561eb6b09c6', 'de4bf312-1b55-5729-9069-8de6e816d541', 'Shoprite Johannesburg Central', 'SHP-JHB-001', 'Plein & Wanderers St, Johannesburg Central', TRUE, NOW());

--------------------------------------------------------------------------------
-- 3. Core Grocery Categories
--------------------------------------------------------------------------------
INSERT INTO categories (id, name, slug, parent_id) VALUES
  ('dcda34e0-efd6-5f43-b188-db739a0deab7', 'Dairy & Eggs', 'dairy-eggs', NULL),
  ('367e044b-773f-5fd2-aa87-3e9c91188484', 'Bakery', 'bakery', NULL),
  ('26b61474-0603-5f47-9c1f-97e2b58d8a70', 'Pantry & Staples', 'pantry-staples', NULL),
  ('2c2c318c-9669-59e3-ba0e-4b1eea0fcb83', 'Fresh Produce', 'fresh-produce', NULL),
  ('3564e0f8-09f8-56da-a0e5-f4715c947669', 'Beverages', 'beverages', NULL);

--------------------------------------------------------------------------------
-- 4. Universal Products (Common Grocery Items)
--------------------------------------------------------------------------------
INSERT INTO products (id, category_id, name, brand, barcode, unit_size, unit_type, created_at) VALUES
  ('6e2941e3-033d-5768-8143-5e7ebc24b874', 'dcda34e0-efd6-5f43-b188-db739a0deab7', 'Full Cream Fresh Milk 2L', 'Clover', '6001299011011', 2.00, 'L', NOW()),
  ('4ca9f9c4-dea2-5f16-8ffb-4ec70ea08382', 'dcda34e0-efd6-5f43-b188-db739a0deab7', 'Large Eggs 18pk', 'Farmer Brown', '6001299011028', 18.00, 'unit', NOW()),
  ('80db6402-f52e-581b-9e8b-6d5855feaf0d', 'dcda34e0-efd6-5f43-b188-db739a0deab7', 'Salted Butter 500g', 'Lurpak', '6001299011035', 500.00, 'g', NOW()),
  ('a69cbf68-41d3-594a-b0d2-b954fc2568dc', 'dcda34e0-efd6-5f43-b188-db739a0deab7', 'Greek Plain Double Cream Yogurt 1kg', 'Lancewood', '6001299011042', 1.00, 'kg', NOW()),
  ('ab9928f5-221a-5546-8b6c-c4ec04fbe933', '367e044b-773f-5fd2-aa87-3e9c91188484', 'Superior Sliced White Bread 700g', 'Albany', '6001299011059', 700.00, 'g', NOW()),
  ('278d443f-3694-5a89-93cb-ea3f2e182985', '367e044b-773f-5fd2-aa87-3e9c91188484', 'More Slices Brown Bread 700g', 'Sasko', '6001299011066', 700.00, 'g', NOW()),
  ('432c8a18-5879-53e0-8dab-e92f8b83b2d9', '367e044b-773f-5fd2-aa87-3e9c91188484', 'Fresh Butter Croissants 4pk', 'Bakery Fresh', '6001299011073', 4.00, 'unit', NOW()),
  ('b7bdd5c6-6434-56c1-8e16-08b52ef508e4', '26b61474-0603-5f47-9c1f-97e2b58d8a70', 'Long Grain Parboiled White Rice 2kg', 'Tastic', '6001299011080', 2.00, 'kg', NOW()),
  ('16d3be61-6fd7-59de-9427-9a63ca022acb', '26b61474-0603-5f47-9c1f-97e2b58d8a70', 'Pure Sunflower Cooking Oil 2L', 'Sunfoil', '6001299011097', 2.00, 'L', NOW()),
  ('c30077d1-ba29-5539-bec1-bcdedb26ab85', '26b61474-0603-5f47-9c1f-97e2b58d8a70', 'Instant Coffee Classic Jar 200g', 'Nescafe', '6001299011103', 200.00, 'g', NOW()),
  ('84af7abc-3d97-5e7b-8235-6a147cdd3749', '26b61474-0603-5f47-9c1f-97e2b58d8a70', 'Pure White Sugar 2.5kg', 'Huletts', '6001299011110', 2.50, 'kg', NOW()),
  ('32c30fc6-89e9-51e8-8fa3-31bf30074053', '26b61474-0603-5f47-9c1f-97e2b58d8a70', 'Spaghetti Pasta 500g', 'Fatti''s & Moni''s', '6001299011127', 500.00, 'g', NOW()),
  ('e33ed6ff-d4b8-5227-9acb-0213d8a27dc8', '26b61474-0603-5f47-9c1f-97e2b58d8a70', 'Chopped Peeled Tomatoes 400g', 'Rhodes Quality', '6001299011134', 400.00, 'g', NOW()),
  ('2e4ad4ea-4c3f-5066-9489-054ecad70658', '26b61474-0603-5f47-9c1f-97e2b58d8a70', 'Tomato Sauce Bottle 700ml', 'All Gold', '6001299011141', 700.00, 'ml', NOW()),
  ('6dedc540-a93a-5eb2-8e7e-47f8a3e78480', '2c2c318c-9669-59e3-ba0e-4b1eea0fcb83', 'Fresh Yellow Bananas 1kg', 'Fresh Produce', '6001299011158', 1.00, 'kg', NOW()),
  ('41f713f0-a121-5b66-9c3e-92ddf40dfe7b', '2c2c318c-9669-59e3-ba0e-4b1eea0fcb83', 'Washed Baby Potatoes 1kg', 'Fresh Produce', '6001299011165', 1.00, 'kg', NOW()),
  ('469f7fd2-b16e-59ee-9631-2b2dbd967a16', '2c2c318c-9669-59e3-ba0e-4b1eea0fcb83', 'Ripe & Ready Hass Avocados 2pk', 'Fresh Produce', '6001299011172', 2.00, 'unit', NOW()),
  ('b17192a0-dc06-526d-a5a0-1658e21ecce7', '3564e0f8-09f8-56da-a0e5-f4715c947669', 'Rooibos Tagless Teabags 80pk', 'Freshpak', '6001299011189', 80.00, 'unit', NOW());

--------------------------------------------------------------------------------
-- 5. Store-Specific Active Prices (Multi-Store Price Divergence)
--------------------------------------------------------------------------------
INSERT INTO store_prices (id, store_id, product_id, price, is_promotional, is_in_stock, updated_at) VALUES
  ('b0f82ed5-7949-5474-a828-78a987353ccc', 'a3b3c260-9228-54dd-ba6d-3b216931987e', '6e2941e3-033d-5768-8143-5e7ebc24b874', 34.99, TRUE, TRUE, NOW()),
  ('7b8e62fd-bc20-50fe-86b8-76f43d3b62bb', '437b5aae-0881-59ca-8f79-7968cca50fff', '6e2941e3-033d-5768-8143-5e7ebc24b874', 36.99, FALSE, TRUE, NOW()),
  ('5e4f8286-6878-5876-a981-0560895e621b', 'aafe584e-791a-5f4c-92c3-2c8c14365911', '6e2941e3-033d-5768-8143-5e7ebc24b874', 42.99, FALSE, TRUE, NOW()),
  ('2ac60f40-e2b1-5d89-b927-6f57898b2adf', 'd0627e50-99f3-50af-b4c4-0a7243d480e2', '6e2941e3-033d-5768-8143-5e7ebc24b874', 44.99, FALSE, TRUE, NOW()),
  ('b00df950-be5a-561b-b5e2-dc76d3df3b29', '03e133be-5dbc-5024-b413-95596e909a67', '6e2941e3-033d-5768-8143-5e7ebc24b874', 38.99, FALSE, TRUE, NOW()),
  ('ce5491ad-eb8b-56eb-b152-2dd4525f89f4', '78e782c3-0337-5193-8cf1-4eb321341c34', '6e2941e3-033d-5768-8143-5e7ebc24b874', 37.99, FALSE, TRUE, NOW()),
  ('709742c0-4fac-5320-99ec-7030bcd62ba1', 'b7a02c2b-3113-515d-a39f-8b2299713850', '6e2941e3-033d-5768-8143-5e7ebc24b874', 40.49, FALSE, TRUE, NOW()),
  ('72c69844-2ff4-5503-8d73-68c08e39e38b', 'd283369e-f1c1-5e89-9bf6-a561eb6b09c6', '6e2941e3-033d-5768-8143-5e7ebc24b874', 33.99, FALSE, TRUE, NOW()),
  ('23890302-446b-5e04-a134-28416818ce68', 'a3b3c260-9228-54dd-ba6d-3b216931987e', '4ca9f9c4-dea2-5f16-8ffb-4ec70ea08382', 64.99, FALSE, TRUE, NOW()),
  ('43decab4-8878-5f9d-b0c4-965558642f7b', 'aafe584e-791a-5f4c-92c3-2c8c14365911', '4ca9f9c4-dea2-5f16-8ffb-4ec70ea08382', 62.99, TRUE, TRUE, NOW()),
  ('25de9715-5fd2-57e5-9823-cee13b76bf29', 'd0627e50-99f3-50af-b4c4-0a7243d480e2', '4ca9f9c4-dea2-5f16-8ffb-4ec70ea08382', 69.99, FALSE, TRUE, NOW()),
  ('c5d31242-d7df-52c3-858e-08040c3c520b', '03e133be-5dbc-5024-b413-95596e909a67', '4ca9f9c4-dea2-5f16-8ffb-4ec70ea08382', 63.99, FALSE, TRUE, NOW()),
  ('87e2849d-fae1-5c9b-9372-497a6614f238', 'd283369e-f1c1-5e89-9bf6-a561eb6b09c6', '4ca9f9c4-dea2-5f16-8ffb-4ec70ea08382', 58.99, FALSE, TRUE, NOW()),
  ('27e778ab-fa78-5e7d-bbf1-c1d8ae5d7ec0', 'a3b3c260-9228-54dd-ba6d-3b216931987e', '80db6402-f52e-581b-9e8b-6d5855feaf0d', 79.99, FALSE, TRUE, NOW()),
  ('c5bf4604-d8e8-5f2b-b2da-cf397f8508b9', 'aafe584e-791a-5f4c-92c3-2c8c14365911', '80db6402-f52e-581b-9e8b-6d5855feaf0d', 84.99, FALSE, TRUE, NOW()),
  ('3e716717-4f4a-5b1c-8f03-c92e48a11e0b', '03e133be-5dbc-5024-b413-95596e909a67', '80db6402-f52e-581b-9e8b-6d5855feaf0d', 69.99, TRUE, TRUE, NOW()),
  ('cfdece43-07bc-5ae1-8a88-7de1dc73d155', 'b7a02c2b-3113-515d-a39f-8b2299713850', '80db6402-f52e-581b-9e8b-6d5855feaf0d', 81.99, FALSE, TRUE, NOW()),
  ('8496038a-5f3e-51a8-9ccc-d4b7797522bf', 'a3b3c260-9228-54dd-ba6d-3b216931987e', 'ab9928f5-221a-5546-8b6c-c4ec04fbe933', 17.99, FALSE, TRUE, NOW()),
  ('95202f63-70a0-5ca5-a73e-05ac67be0eca', 'aafe584e-791a-5f4c-92c3-2c8c14365911', 'ab9928f5-221a-5546-8b6c-c4ec04fbe933', 19.99, FALSE, TRUE, NOW()),
  ('80832f33-315a-57b7-8e07-85ad9019ba9a', '03e133be-5dbc-5024-b413-95596e909a67', 'ab9928f5-221a-5546-8b6c-c4ec04fbe933', 16.99, FALSE, TRUE, NOW()),
  ('2f9987e4-52a4-5faf-933e-f0a2de97aeb7', 'd283369e-f1c1-5e89-9bf6-a561eb6b09c6', 'ab9928f5-221a-5546-8b6c-c4ec04fbe933', 15.99, FALSE, TRUE, NOW()),
  ('48d71351-34aa-5d68-a313-57817642d8b9', 'a3b3c260-9228-54dd-ba6d-3b216931987e', '278d443f-3694-5a89-93cb-ea3f2e182985', 16.99, FALSE, TRUE, NOW()),
  ('cb20011a-e318-56e3-9246-96a0effb4686', 'aafe584e-791a-5f4c-92c3-2c8c14365911', '278d443f-3694-5a89-93cb-ea3f2e182985', 18.99, FALSE, TRUE, NOW()),
  ('89b1f97c-556d-566b-b011-d21aa7cb9aa4', 'd283369e-f1c1-5e89-9bf6-a561eb6b09c6', '278d443f-3694-5a89-93cb-ea3f2e182985', 14.99, FALSE, TRUE, NOW()),
  ('603b13ff-c57b-5926-824b-5e77bf60b29b', 'a3b3c260-9228-54dd-ba6d-3b216931987e', 'b7bdd5c6-6434-56c1-8e16-08b52ef508e4', 39.99, TRUE, TRUE, NOW()),
  ('4cb7f9be-a2ce-532d-b45b-2110c50fdce7', 'aafe584e-791a-5f4c-92c3-2c8c14365911', 'b7bdd5c6-6434-56c1-8e16-08b52ef508e4', 49.99, FALSE, TRUE, NOW()),
  ('9b8db285-cb3b-55e9-ae15-759d3b9762ff', '03e133be-5dbc-5024-b413-95596e909a67', 'b7bdd5c6-6434-56c1-8e16-08b52ef508e4', 43.99, FALSE, TRUE, NOW()),
  ('3bfcb6e6-4c24-5e92-87ae-bc42c9b21e63', 'd283369e-f1c1-5e89-9bf6-a561eb6b09c6', 'b7bdd5c6-6434-56c1-8e16-08b52ef508e4', 41.99, FALSE, TRUE, NOW()),
  ('7903dc95-2a00-563a-b2dc-f2b6a809f8f6', 'a3b3c260-9228-54dd-ba6d-3b216931987e', '16d3be61-6fd7-59de-9427-9a63ca022acb', 82.99, FALSE, TRUE, NOW()),
  ('72ec1b9b-b587-50e2-b33c-b95e14e07a08', 'aafe584e-791a-5f4c-92c3-2c8c14365911', '16d3be61-6fd7-59de-9427-9a63ca022acb', 89.99, FALSE, TRUE, NOW()),
  ('129d5321-d631-545a-91e0-526e3f8fe5aa', '03e133be-5dbc-5024-b413-95596e909a67', '16d3be61-6fd7-59de-9427-9a63ca022acb', 74.99, TRUE, TRUE, NOW()),
  ('6560dfb6-05a1-5841-959e-e32431046852', 'd283369e-f1c1-5e89-9bf6-a561eb6b09c6', '16d3be61-6fd7-59de-9427-9a63ca022acb', 76.99, FALSE, TRUE, NOW()),
  ('90e5d0ec-92eb-589b-8135-d4eddb542395', 'a3b3c260-9228-54dd-ba6d-3b216931987e', 'c30077d1-ba29-5539-bec1-bcdedb26ab85', 119.99, FALSE, TRUE, NOW()),
  ('9c4d9ced-c16b-5c2f-a712-d5cd98c8ab5e', 'aafe584e-791a-5f4c-92c3-2c8c14365911', 'c30077d1-ba29-5539-bec1-bcdedb26ab85', 129.99, FALSE, TRUE, NOW()),
  ('846d97fa-2468-50ef-8e38-acd5082a5186', '03e133be-5dbc-5024-b413-95596e909a67', 'c30077d1-ba29-5539-bec1-bcdedb26ab85', 114.99, FALSE, TRUE, NOW()),
  ('7cffc182-7bba-5920-a936-26752b5fea37', 'd283369e-f1c1-5e89-9bf6-a561eb6b09c6', 'c30077d1-ba29-5539-bec1-bcdedb26ab85', 109.99, FALSE, TRUE, NOW()),
  ('30bf1b74-6bd1-5f19-89ac-fb8c31cebbfe', 'a3b3c260-9228-54dd-ba6d-3b216931987e', '6dedc540-a93a-5eb2-8e7e-47f8a3e78480', 24.99, FALSE, TRUE, NOW()),
  ('47c61a3b-ab61-5b04-988f-ceae1300c1f9', 'aafe584e-791a-5f4c-92c3-2c8c14365911', '6dedc540-a93a-5eb2-8e7e-47f8a3e78480', 28.99, FALSE, TRUE, NOW()),
  ('ab220ece-7724-5833-8126-0cb6a0c57624', '03e133be-5dbc-5024-b413-95596e909a67', '6dedc540-a93a-5eb2-8e7e-47f8a3e78480', 22.99, FALSE, TRUE, NOW()),
  ('1f79b795-ab63-5b57-8912-bfd640738adc', 'd283369e-f1c1-5e89-9bf6-a561eb6b09c6', '6dedc540-a93a-5eb2-8e7e-47f8a3e78480', 21.99, FALSE, TRUE, NOW()),
  ('c33f4968-0e00-5ad4-a9a5-9bcaa51cc6b9', 'a3b3c260-9228-54dd-ba6d-3b216931987e', 'b17192a0-dc06-526d-a5a0-1658e21ecce7', 52.99, FALSE, TRUE, NOW()),
  ('b904ef1c-a949-5fad-a151-53cda3039eb4', '03e133be-5dbc-5024-b413-95596e909a67', 'b17192a0-dc06-526d-a5a0-1658e21ecce7', 49.99, TRUE, TRUE, NOW()),
  ('6eb1368e-2eb6-5d26-96e7-05e52c752c5e', 'aafe584e-791a-5f4c-92c3-2c8c14365911', 'b17192a0-dc06-526d-a5a0-1658e21ecce7', 56.99, FALSE, TRUE, NOW());

--------------------------------------------------------------------------------
-- 6. Price History (Simulated 30-60 Day Tracking)
--------------------------------------------------------------------------------
INSERT INTO price_history (id, store_id, product_id, price, is_promotional, recorded_at) VALUES
  ('e7b5c419-db0d-5942-b090-a4671e614f2f', 'a3b3c260-9228-54dd-ba6d-3b216931987e', '6e2941e3-033d-5768-8143-5e7ebc24b874', 36.99, FALSE, '2026-09-18T15:17:14.009725+00:00'),
  ('280138ff-68f8-58cd-8c15-9365d6acc8e8', 'a3b3c260-9228-54dd-ba6d-3b216931987e', '6e2941e3-033d-5768-8143-5e7ebc24b874', 38.99, FALSE, '2026-10-18T15:17:14.009725+00:00'),
  ('690f2595-b1d8-5138-b855-84267a4a5556', 'a3b3c260-9228-54dd-ba6d-3b216931987e', '6e2941e3-033d-5768-8143-5e7ebc24b874', 34.99, TRUE, '2026-11-12T15:17:14.009725+00:00'),
  ('f5387aca-3ccd-5a51-9eba-61271215d5e4', 'aafe584e-791a-5f4c-92c3-2c8c14365911', '16d3be61-6fd7-59de-9427-9a63ca022acb', 84.99, FALSE, '2026-09-18T15:17:14.009725+00:00'),
  ('599b42a2-6d79-57d1-b80f-6f763482ef70', 'aafe584e-791a-5f4c-92c3-2c8c14365911', '16d3be61-6fd7-59de-9427-9a63ca022acb', 86.99, FALSE, '2026-10-13T15:17:14.009725+00:00'),
  ('92081895-45d3-5105-8921-b2fb92be6d1b', 'aafe584e-791a-5f4c-92c3-2c8c14365911', '16d3be61-6fd7-59de-9427-9a63ca022acb', 89.99, FALSE, '2026-11-07T15:17:14.009725+00:00'),
  ('784b8b43-4eed-585e-985e-8c370fcd2beb', '03e133be-5dbc-5024-b413-95596e909a67', 'c30077d1-ba29-5539-bec1-bcdedb26ab85', 109.99, FALSE, '2026-10-03T15:17:14.009725+00:00'),
  ('289ffb53-f691-560e-a938-1ab850509035', '03e133be-5dbc-5024-b413-95596e909a67', 'c30077d1-ba29-5539-bec1-bcdedb26ab85', 114.99, FALSE, '2026-11-02T15:17:14.009725+00:00'),
  ('ee555682-f70a-5bbc-9a20-54b56fe30ed8', 'd283369e-f1c1-5e89-9bf6-a561eb6b09c6', 'b7bdd5c6-6434-56c1-8e16-08b52ef508e4', 38.99, FALSE, '2026-09-28T15:17:14.009725+00:00'),
  ('448c9d78-79bf-52fa-a43f-a9433af70683', 'd283369e-f1c1-5e89-9bf6-a561eb6b09c6', 'b7bdd5c6-6434-56c1-8e16-08b52ef508e4', 41.99, FALSE, '2026-10-28T15:17:14.009725+00:00');
