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
-- 2. Canonical National Retailer Chain Records (1 per Retailer)
--------------------------------------------------------------------------------
INSERT INTO stores (id, retailer_id, name, branch_code, address, is_active, created_at) VALUES
  ('26f7a89e-0e58-56e3-a225-8c7310382985', '3ae15000-8907-5fb5-9904-c47dba4bcc3e', 'Checkers', NULL, NULL, TRUE, NOW()),
  ('30c7639b-d34c-597b-9399-68e3ff9de7a7', 'bb29a5ff-6ca1-515e-aa5c-641225dfa51c', 'Woolworths Food', NULL, NULL, TRUE, NOW()),
  ('cd86c9b4-176c-551e-aebc-b91bfdce86c1', 'dae4891a-2bf0-5116-9688-9faf01f18567', 'Pick n Pay', NULL, NULL, TRUE, NOW()),
  ('c9753b0f-5341-5001-a2dc-3996ff85a7bc', '5f8147c2-db0d-51f1-b4b2-9cf0d4e975ad', 'SPAR', NULL, NULL, TRUE, NOW()),
  ('d1b6fc61-ff2b-5935-8d92-9eec487eeaae', 'de4bf312-1b55-5729-9069-8de6e816d541', 'Shoprite', NULL, NULL, TRUE, NOW());

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
-- 5. Chain-Level Active Prices (Full Catalog across 5 Retailers)
--------------------------------------------------------------------------------
INSERT INTO store_prices (id, store_id, product_id, price, is_promotional, is_in_stock, updated_at) VALUES
  ('e8f74067-213f-5463-a448-6a58379f3c0b', '26f7a89e-0e58-56e3-a225-8c7310382985', '6e2941e3-033d-5768-8143-5e7ebc24b874', 31.99, TRUE, TRUE, NOW()),
  ('fced4a8b-cd83-5540-88e3-755d7c7e4bf4', '30c7639b-d34c-597b-9399-68e3ff9de7a7', '6e2941e3-033d-5768-8143-5e7ebc24b874', 42.99, FALSE, TRUE, NOW()),
  ('e9f464d4-a29e-5255-b748-69ea99e3330a', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', '6e2941e3-033d-5768-8143-5e7ebc24b874', 38.99, FALSE, TRUE, NOW()),
  ('a5a05db1-9eb3-51ff-aa40-2c9cb88b0b52', 'c9753b0f-5341-5001-a2dc-3996ff85a7bc', '6e2941e3-033d-5768-8143-5e7ebc24b874', 40.49, FALSE, TRUE, NOW()),
  ('1957da2d-c3f8-5db5-8bf5-43634c7dee61', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', '6e2941e3-033d-5768-8143-5e7ebc24b874', 33.99, FALSE, TRUE, NOW()),
  ('c90f4355-8b43-5839-a25f-ea7cafb738a2', '26f7a89e-0e58-56e3-a225-8c7310382985', '4ca9f9c4-dea2-5f16-8ffb-4ec70ea08382', 64.99, FALSE, TRUE, NOW()),
  ('b8c0dcdc-a14e-5f11-805b-cd40969fab1c', '30c7639b-d34c-597b-9399-68e3ff9de7a7', '4ca9f9c4-dea2-5f16-8ffb-4ec70ea08382', 62.99, FALSE, TRUE, NOW()),
  ('0405c097-b10e-5ff7-8d02-20fc5187e590', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', '4ca9f9c4-dea2-5f16-8ffb-4ec70ea08382', 54.99, TRUE, TRUE, NOW()),
  ('1fd81de6-1c53-555a-a116-cc5e7be95511', 'c9753b0f-5341-5001-a2dc-3996ff85a7bc', '4ca9f9c4-dea2-5f16-8ffb-4ec70ea08382', 66.49, FALSE, TRUE, NOW()),
  ('2c8c296c-6fa4-5013-aa04-8ee89f6bdbf7', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', '4ca9f9c4-dea2-5f16-8ffb-4ec70ea08382', 58.99, FALSE, TRUE, NOW()),
  ('16afddb9-e4dc-57ac-a38f-54d6696bc14f', '26f7a89e-0e58-56e3-a225-8c7310382985', '80db6402-f52e-581b-9e8b-6d5855feaf0d', 79.99, FALSE, TRUE, NOW()),
  ('71be9afa-e7f5-59d5-bbd1-30068249ed70', '30c7639b-d34c-597b-9399-68e3ff9de7a7', '80db6402-f52e-581b-9e8b-6d5855feaf0d', 84.99, FALSE, TRUE, NOW()),
  ('afa467f9-5e76-54df-9b32-04a81ec360e1', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', '80db6402-f52e-581b-9e8b-6d5855feaf0d', 69.99, TRUE, TRUE, NOW()),
  ('04457673-7ebd-510f-b3f1-32b8467b6c11', 'c9753b0f-5341-5001-a2dc-3996ff85a7bc', '80db6402-f52e-581b-9e8b-6d5855feaf0d', 81.99, FALSE, TRUE, NOW()),
  ('9a96597f-b56c-5792-ae08-66020d6e1bee', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', '80db6402-f52e-581b-9e8b-6d5855feaf0d', 77.99, FALSE, TRUE, NOW()),
  ('170158e1-1f41-57e1-a26f-241f36bf747f', '26f7a89e-0e58-56e3-a225-8c7310382985', 'a69cbf68-41d3-594a-b0d2-b954fc2568dc', 49.99, FALSE, TRUE, NOW()),
  ('3d8198ff-2e06-5f6d-816b-cd35510dc817', '30c7639b-d34c-597b-9399-68e3ff9de7a7', 'a69cbf68-41d3-594a-b0d2-b954fc2568dc', 56.99, FALSE, TRUE, NOW()),
  ('a3fb9ad7-d8e6-56ef-8932-82a917c1bbb6', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', 'a69cbf68-41d3-594a-b0d2-b954fc2568dc', 47.99, TRUE, TRUE, NOW()),
  ('92b20375-4a58-571d-a380-9b5c4b8d6196', 'c9753b0f-5341-5001-a2dc-3996ff85a7bc', 'a69cbf68-41d3-594a-b0d2-b954fc2568dc', 52.49, FALSE, TRUE, NOW()),
  ('21469faa-ea83-5310-b1f8-f16638bf2d76', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', 'a69cbf68-41d3-594a-b0d2-b954fc2568dc', 48.99, FALSE, TRUE, NOW()),
  ('b2409333-944f-51e9-ad33-ecd3d54681ab', '26f7a89e-0e58-56e3-a225-8c7310382985', 'ab9928f5-221a-5546-8b6c-c4ec04fbe933', 17.99, FALSE, TRUE, NOW()),
  ('7b2ff1ae-c29a-5a60-8a83-69efe0e6b19c', '30c7639b-d34c-597b-9399-68e3ff9de7a7', 'ab9928f5-221a-5546-8b6c-c4ec04fbe933', 19.99, FALSE, TRUE, NOW()),
  ('ba354754-1e58-5267-9567-a1c0fe599d30', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', 'ab9928f5-221a-5546-8b6c-c4ec04fbe933', 16.99, FALSE, TRUE, NOW()),
  ('e4c2ae06-69be-5000-8c56-613374196f8d', 'c9753b0f-5341-5001-a2dc-3996ff85a7bc', 'ab9928f5-221a-5546-8b6c-c4ec04fbe933', 18.49, FALSE, TRUE, NOW()),
  ('b32e9e6c-39a5-5e6f-97e6-69a7e149b7ba', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', 'ab9928f5-221a-5546-8b6c-c4ec04fbe933', 15.99, FALSE, TRUE, NOW()),
  ('243671d9-bf3d-5c80-8b75-d57d78794cf5', '26f7a89e-0e58-56e3-a225-8c7310382985', '278d443f-3694-5a89-93cb-ea3f2e182985', 16.99, FALSE, TRUE, NOW()),
  ('fa95e328-a00d-5e3c-a7a7-9510bc7e921a', '30c7639b-d34c-597b-9399-68e3ff9de7a7', '278d443f-3694-5a89-93cb-ea3f2e182985', 18.99, FALSE, TRUE, NOW()),
  ('e7b7eb8a-a7b7-5f64-b89f-a3f4e90d3eb5', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', '278d443f-3694-5a89-93cb-ea3f2e182985', 15.99, FALSE, TRUE, NOW()),
  ('06b6fe4f-e3ec-5c6e-b58a-e8956c4c9387', 'c9753b0f-5341-5001-a2dc-3996ff85a7bc', '278d443f-3694-5a89-93cb-ea3f2e182985', 17.49, FALSE, TRUE, NOW()),
  ('dfd3165b-e8f4-5c45-87cb-13e89b99d54f', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', '278d443f-3694-5a89-93cb-ea3f2e182985', 14.99, FALSE, TRUE, NOW()),
  ('810bd125-2946-58e6-8a81-7e0fe9ad300b', '26f7a89e-0e58-56e3-a225-8c7310382985', '432c8a18-5879-53e0-8dab-e92f8b83b2d9', 32.99, FALSE, TRUE, NOW()),
  ('3f28c816-f32f-54ed-ac4e-a3f9c3a0c19c', '30c7639b-d34c-597b-9399-68e3ff9de7a7', '432c8a18-5879-53e0-8dab-e92f8b83b2d9', 36.99, FALSE, TRUE, NOW()),
  ('1d23077f-659e-5287-a8aa-1a26e2949c34', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', '432c8a18-5879-53e0-8dab-e92f8b83b2d9', 31.99, FALSE, TRUE, NOW()),
  ('1f62e7f8-e978-535e-a071-01ffffb86e6c', 'c9753b0f-5341-5001-a2dc-3996ff85a7bc', '432c8a18-5879-53e0-8dab-e92f8b83b2d9', 29.99, TRUE, TRUE, NOW()),
  ('8b9ca829-7b55-5496-a83f-6f1cd285504e', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', '432c8a18-5879-53e0-8dab-e92f8b83b2d9', 30.99, FALSE, TRUE, NOW()),
  ('5da9bcac-6030-5f59-b0db-92febdb35c5a', '26f7a89e-0e58-56e3-a225-8c7310382985', 'b7bdd5c6-6434-56c1-8e16-08b52ef508e4', 39.99, TRUE, TRUE, NOW()),
  ('9d7d4924-248e-5644-bb02-2fae659af773', '30c7639b-d34c-597b-9399-68e3ff9de7a7', 'b7bdd5c6-6434-56c1-8e16-08b52ef508e4', 49.99, FALSE, TRUE, NOW()),
  ('861abf92-d998-5211-905d-872b08bfa01f', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', 'b7bdd5c6-6434-56c1-8e16-08b52ef508e4', 43.99, FALSE, TRUE, NOW()),
  ('56f3961c-c05c-55d8-b72d-d73ddf067fa8', 'c9753b0f-5341-5001-a2dc-3996ff85a7bc', 'b7bdd5c6-6434-56c1-8e16-08b52ef508e4', 44.99, FALSE, TRUE, NOW()),
  ('09d0d4e5-5b69-5ff8-a069-699a4048d952', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', 'b7bdd5c6-6434-56c1-8e16-08b52ef508e4', 41.99, FALSE, TRUE, NOW()),
  ('841b2463-b426-5d70-a2ed-4ed28dc9fdc0', '26f7a89e-0e58-56e3-a225-8c7310382985', '16d3be61-6fd7-59de-9427-9a63ca022acb', 82.99, FALSE, TRUE, NOW()),
  ('6172a82f-d554-5202-88db-492b50f64139', '30c7639b-d34c-597b-9399-68e3ff9de7a7', '16d3be61-6fd7-59de-9427-9a63ca022acb', 89.99, FALSE, TRUE, NOW()),
  ('2b171e88-30a5-56ee-8178-c685e5248b7e', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', '16d3be61-6fd7-59de-9427-9a63ca022acb', 74.99, TRUE, TRUE, NOW()),
  ('9c12b31f-a726-569d-9866-531f6c1cd386', 'c9753b0f-5341-5001-a2dc-3996ff85a7bc', '16d3be61-6fd7-59de-9427-9a63ca022acb', 84.99, FALSE, TRUE, NOW()),
  ('46047573-6596-51cc-a83c-ea58d5dc24f9', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', '16d3be61-6fd7-59de-9427-9a63ca022acb', 76.99, FALSE, TRUE, NOW()),
  ('108cc997-faef-5de5-b35e-aa2053d87b3f', '26f7a89e-0e58-56e3-a225-8c7310382985', 'c30077d1-ba29-5539-bec1-bcdedb26ab85', 119.99, FALSE, TRUE, NOW()),
  ('b53d7e97-7dba-5c4b-8194-fbf5fd4fadbf', '30c7639b-d34c-597b-9399-68e3ff9de7a7', 'c30077d1-ba29-5539-bec1-bcdedb26ab85', 129.99, FALSE, TRUE, NOW()),
  ('53307d14-590f-5837-9488-98094518494b', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', 'c30077d1-ba29-5539-bec1-bcdedb26ab85', 114.99, FALSE, TRUE, NOW()),
  ('cc784736-21cb-5f5f-b4e0-13abb7ddbb34', 'c9753b0f-5341-5001-a2dc-3996ff85a7bc', 'c30077d1-ba29-5539-bec1-bcdedb26ab85', 122.99, FALSE, TRUE, NOW()),
  ('5b698303-a0b9-5bea-b711-fe713bf5f345', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', 'c30077d1-ba29-5539-bec1-bcdedb26ab85', 109.99, FALSE, TRUE, NOW()),
  ('87f8fbde-02e5-55ba-ac78-9ed8b0fe88d8', '26f7a89e-0e58-56e3-a225-8c7310382985', '84af7abc-3d97-5e7b-8235-6a147cdd3749', 58.99, FALSE, TRUE, NOW()),
  ('b2cd092e-ea45-56c0-ab55-af950e91f7d2', '30c7639b-d34c-597b-9399-68e3ff9de7a7', '84af7abc-3d97-5e7b-8235-6a147cdd3749', 64.99, FALSE, TRUE, NOW()),
  ('80a26183-072c-5211-ad07-c439939f8f9e', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', '84af7abc-3d97-5e7b-8235-6a147cdd3749', 56.99, FALSE, TRUE, NOW()),
  ('b8546494-3ce9-5541-85ca-c8796355c908', 'c9753b0f-5341-5001-a2dc-3996ff85a7bc', '84af7abc-3d97-5e7b-8235-6a147cdd3749', 59.99, FALSE, TRUE, NOW()),
  ('b6541896-ac88-5c0a-ad9f-a654f34d8a44', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', '84af7abc-3d97-5e7b-8235-6a147cdd3749', 54.99, TRUE, TRUE, NOW()),
  ('4d8c2c64-1be6-5403-b1ba-c3b0f58fc8d2', '26f7a89e-0e58-56e3-a225-8c7310382985', '32c30fc6-89e9-51e8-8fa3-31bf30074053', 18.99, FALSE, TRUE, NOW()),
  ('fb43a22c-549e-5d1b-a248-87822acf155d', '30c7639b-d34c-597b-9399-68e3ff9de7a7', '32c30fc6-89e9-51e8-8fa3-31bf30074053', 21.99, FALSE, TRUE, NOW()),
  ('6b0cb2fe-45c1-5fd2-929b-6b2b99b6ecb3', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', '32c30fc6-89e9-51e8-8fa3-31bf30074053', 17.99, FALSE, TRUE, NOW()),
  ('3993a619-1e4f-5f29-91a3-df51ea6c0893', 'c9753b0f-5341-5001-a2dc-3996ff85a7bc', '32c30fc6-89e9-51e8-8fa3-31bf30074053', 19.49, FALSE, TRUE, NOW()),
  ('7ec0ac52-662b-54e1-82ea-91f82211d169', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', '32c30fc6-89e9-51e8-8fa3-31bf30074053', 16.99, FALSE, TRUE, NOW()),
  ('66c40c06-da2d-51b8-b4cb-65503d503ca0', '26f7a89e-0e58-56e3-a225-8c7310382985', 'e33ed6ff-d4b8-5227-9acb-0213d8a27dc8', 21.99, FALSE, TRUE, NOW()),
  ('48f9a58d-0494-54cb-b956-cab6e9b46c04', '30c7639b-d34c-597b-9399-68e3ff9de7a7', 'e33ed6ff-d4b8-5227-9acb-0213d8a27dc8', 24.99, FALSE, TRUE, NOW()),
  ('182cf6e9-6992-53d6-85e7-43f7c491f6e9', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', 'e33ed6ff-d4b8-5227-9acb-0213d8a27dc8', 19.99, TRUE, TRUE, NOW()),
  ('719f0a7b-efe0-5108-ab0f-4fe42545d01a', 'c9753b0f-5341-5001-a2dc-3996ff85a7bc', 'e33ed6ff-d4b8-5227-9acb-0213d8a27dc8', 22.49, FALSE, TRUE, NOW()),
  ('8d85d209-3e53-50a6-9b1e-82fd47c2513e', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', 'e33ed6ff-d4b8-5227-9acb-0213d8a27dc8', 20.49, FALSE, TRUE, NOW()),
  ('69f83ff7-7ac5-5d23-b159-03c7749ce23c', '26f7a89e-0e58-56e3-a225-8c7310382985', '2e4ad4ea-4c3f-5066-9489-054ecad70658', 41.99, FALSE, TRUE, NOW()),
  ('41887f25-380e-5636-8457-435ee6a5d0e2', '30c7639b-d34c-597b-9399-68e3ff9de7a7', '2e4ad4ea-4c3f-5066-9489-054ecad70658', 46.99, FALSE, TRUE, NOW()),
  ('a6058ea7-2293-5065-895b-4e6e7607b422', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', '2e4ad4ea-4c3f-5066-9489-054ecad70658', 39.99, FALSE, TRUE, NOW()),
  ('8b301aa9-c831-5a67-b39f-80e12bbb229e', 'c9753b0f-5341-5001-a2dc-3996ff85a7bc', '2e4ad4ea-4c3f-5066-9489-054ecad70658', 42.99, FALSE, TRUE, NOW()),
  ('acc22ff2-6d5c-5dcd-80c2-088e37623fa0', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', '2e4ad4ea-4c3f-5066-9489-054ecad70658', 38.99, FALSE, TRUE, NOW()),
  ('479d6301-c95a-5a0c-af49-bb8febbdc652', '26f7a89e-0e58-56e3-a225-8c7310382985', '6dedc540-a93a-5eb2-8e7e-47f8a3e78480', 24.99, FALSE, TRUE, NOW()),
  ('892e5a9b-9d92-544b-bd56-e1cd278a0b9c', '30c7639b-d34c-597b-9399-68e3ff9de7a7', '6dedc540-a93a-5eb2-8e7e-47f8a3e78480', 28.99, FALSE, TRUE, NOW()),
  ('6d25cedb-008a-5301-acd1-16ca0bddbdab', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', '6dedc540-a93a-5eb2-8e7e-47f8a3e78480', 22.99, FALSE, TRUE, NOW()),
  ('1a709544-2e9d-5d76-9789-83092cfa6aef', 'c9753b0f-5341-5001-a2dc-3996ff85a7bc', '6dedc540-a93a-5eb2-8e7e-47f8a3e78480', 25.49, FALSE, TRUE, NOW()),
  ('32a33dd0-1857-5ff1-be60-0a916f719949', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', '6dedc540-a93a-5eb2-8e7e-47f8a3e78480', 21.99, FALSE, TRUE, NOW()),
  ('6bf2f276-8726-5900-b69b-0cd9b37447c3', '26f7a89e-0e58-56e3-a225-8c7310382985', '41f713f0-a121-5b66-9c3e-92ddf40dfe7b', 29.99, FALSE, TRUE, NOW()),
  ('fdb83f21-40b2-58ed-91c4-8a921fc3d92a', '30c7639b-d34c-597b-9399-68e3ff9de7a7', '41f713f0-a121-5b66-9c3e-92ddf40dfe7b', 34.99, FALSE, TRUE, NOW()),
  ('c2c4f97b-897a-5090-9dfc-b8a47520bad3', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', '41f713f0-a121-5b66-9c3e-92ddf40dfe7b', 27.99, FALSE, TRUE, NOW()),
  ('f44f3f0f-f058-50f4-a8cf-5567979acae8', 'c9753b0f-5341-5001-a2dc-3996ff85a7bc', '41f713f0-a121-5b66-9c3e-92ddf40dfe7b', 28.99, FALSE, TRUE, NOW()),
  ('337886b1-a9b5-519f-b9c0-6b1ff78f3517', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', '41f713f0-a121-5b66-9c3e-92ddf40dfe7b', 26.99, FALSE, TRUE, NOW()),
  ('0596a94e-82c4-5ab3-9cbd-f6fa59d3344f', '26f7a89e-0e58-56e3-a225-8c7310382985', '469f7fd2-b16e-59ee-9631-2b2dbd967a16', 36.99, TRUE, TRUE, NOW()),
  ('9e19c81a-12b5-5487-b82f-d94b9ebf03e7', '30c7639b-d34c-597b-9399-68e3ff9de7a7', '469f7fd2-b16e-59ee-9631-2b2dbd967a16', 44.99, FALSE, TRUE, NOW()),
  ('f293be2e-5843-5340-b467-617830ed8c19', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', '469f7fd2-b16e-59ee-9631-2b2dbd967a16', 39.99, FALSE, TRUE, NOW()),
  ('1b14ed76-a190-5ce1-9ab4-62022ce3fe5d', 'c9753b0f-5341-5001-a2dc-3996ff85a7bc', '469f7fd2-b16e-59ee-9631-2b2dbd967a16', 41.99, FALSE, TRUE, NOW()),
  ('fa5dcabf-ea67-5622-a736-fb4ddb0262dd', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', '469f7fd2-b16e-59ee-9631-2b2dbd967a16', 37.99, FALSE, TRUE, NOW()),
  ('d22004ef-e57b-539e-8681-c3b5751d0e25', '26f7a89e-0e58-56e3-a225-8c7310382985', 'b17192a0-dc06-526d-a5a0-1658e21ecce7', 52.99, FALSE, TRUE, NOW()),
  ('4ff54c4e-db01-512e-bdac-8a8cdd68a28a', '30c7639b-d34c-597b-9399-68e3ff9de7a7', 'b17192a0-dc06-526d-a5a0-1658e21ecce7', 56.99, FALSE, TRUE, NOW()),
  ('cde7a4e6-8b24-5ee4-8f67-ff1dfe94ef31', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', 'b17192a0-dc06-526d-a5a0-1658e21ecce7', 49.99, TRUE, TRUE, NOW()),
  ('34c8fc4e-e72a-59b8-9658-052c5fbc17f9', 'c9753b0f-5341-5001-a2dc-3996ff85a7bc', 'b17192a0-dc06-526d-a5a0-1658e21ecce7', 54.49, FALSE, TRUE, NOW()),
  ('74589802-0979-515e-84a9-f3da03a178ed', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', 'b17192a0-dc06-526d-a5a0-1658e21ecce7', 51.99, FALSE, TRUE, NOW());

--------------------------------------------------------------------------------
-- 6. Price History (Simulated 30-60 Day Tracking)
--------------------------------------------------------------------------------
INSERT INTO price_history (id, store_id, product_id, price, is_promotional, recorded_at) VALUES
  ('c16e8c21-dbcf-50cb-bf6a-7f2258af763f', '26f7a89e-0e58-56e3-a225-8c7310382985', '6e2941e3-033d-5768-8143-5e7ebc24b874', 36.99, FALSE, '2026-09-21T17:05:43.773775+00:00'),
  ('a3698f4b-7b4f-57ad-b45c-071d50b134c0', '26f7a89e-0e58-56e3-a225-8c7310382985', '6e2941e3-033d-5768-8143-5e7ebc24b874', 38.99, FALSE, '2026-10-21T17:05:43.773775+00:00'),
  ('5eb2f75c-f349-5bb7-9c32-b96d7b154256', '26f7a89e-0e58-56e3-a225-8c7310382985', '6e2941e3-033d-5768-8143-5e7ebc24b874', 31.99, TRUE, '2026-11-15T17:05:43.773775+00:00'),
  ('457a931a-1d5e-585b-982a-407f8f745b29', '30c7639b-d34c-597b-9399-68e3ff9de7a7', '16d3be61-6fd7-59de-9427-9a63ca022acb', 84.99, FALSE, '2026-09-21T17:05:43.773775+00:00'),
  ('a055cdf4-0103-50bf-90d6-a8c07be869d2', '30c7639b-d34c-597b-9399-68e3ff9de7a7', '16d3be61-6fd7-59de-9427-9a63ca022acb', 86.99, FALSE, '2026-10-16T17:05:43.773775+00:00'),
  ('c1f5e317-dc53-5978-8303-c929d2016184', '30c7639b-d34c-597b-9399-68e3ff9de7a7', '16d3be61-6fd7-59de-9427-9a63ca022acb', 89.99, FALSE, '2026-11-10T17:05:43.773775+00:00'),
  ('a04ae326-5b96-582a-aece-a8fa288f1b82', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', 'c30077d1-ba29-5539-bec1-bcdedb26ab85', 109.99, FALSE, '2026-10-06T17:05:43.773775+00:00'),
  ('a9183a34-a9a0-5cc2-bca7-c9e82aa241d8', 'cd86c9b4-176c-551e-aebc-b91bfdce86c1', 'c30077d1-ba29-5539-bec1-bcdedb26ab85', 114.99, FALSE, '2026-11-05T17:05:43.773775+00:00'),
  ('ee555682-f70a-5bbc-9a20-54b56fe30ed8', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', 'b7bdd5c6-6434-56c1-8e16-08b52ef508e4', 38.99, FALSE, '2026-10-01T17:05:43.773775+00:00'),
  ('448c9d78-79bf-52fa-a43f-a9433af70683', 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae', 'b7bdd5c6-6434-56c1-8e16-08b52ef508e4', 41.99, FALSE, '2026-10-31T17:05:43.773775+00:00');
