-- ============================================================
-- PyBI sample dataset — loaded automatically on first postgres
-- container startup via /docker-entrypoint-initdb.d/
-- ============================================================

-- ── Sales fact table ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sales (
    id          SERIAL PRIMARY KEY,
    sale_date   DATE           NOT NULL,
    product     TEXT           NOT NULL,
    category    TEXT           NOT NULL,
    region      TEXT           NOT NULL,
    salesperson TEXT           NOT NULL,
    quantity    INTEGER        NOT NULL,
    unit_price  NUMERIC(10,2)  NOT NULL,
    revenue     NUMERIC(10,2)  NOT NULL
);

INSERT INTO sales (sale_date, product, category, region, salesperson, quantity, unit_price, revenue)
SELECT
    (DATE '2024-01-01' + (random() * 730)::int)::date                              AS sale_date,
    (ARRAY['Laptop','Monitor','Keyboard','Mouse','Headset',
           'Webcam','Tablet','Phone','SSD','Printer'])[ceil(random()*10)::int]      AS product,
    (ARRAY['Electronics','Peripherals','Mobile','Storage','Office'])
        [ceil(random()*5)::int]                                                     AS category,
    (ARRAY['North','South','East','West','Central'])[ceil(random()*5)::int]         AS region,
    (ARRAY['Alice','Bob','Charlie','Diana','Eve','Frank','Grace','Hank'])
        [ceil(random()*8)::int]                                                     AS salesperson,
    (random()*9 + 1)::int                                                           AS quantity,
    ROUND((random()*900 + 100)::numeric, 2)                                         AS unit_price,
    ROUND(((random()*9+1) * (random()*900+100))::numeric, 2)                       AS revenue
FROM generate_series(1, 1000);

-- ── Customers table ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customers (
    id          SERIAL PRIMARY KEY,
    name        TEXT    NOT NULL,
    email       TEXT    UNIQUE NOT NULL,
    country     TEXT    NOT NULL,
    segment     TEXT    NOT NULL,         -- SMB | Enterprise | Consumer
    joined_date DATE    NOT NULL,
    lifetime_value NUMERIC(12,2) DEFAULT 0
);

INSERT INTO customers (name, email, country, segment, joined_date, lifetime_value)
SELECT
    'Customer_' || g                                                                AS name,
    'customer' || g || '@example.com'                                              AS email,
    (ARRAY['USA','UK','Germany','France','India','Australia','Canada','Japan'])
        [ceil(random()*8)::int]                                                    AS country,
    (ARRAY['SMB','Enterprise','Consumer'])[ceil(random()*3)::int]                  AS segment,
    (DATE '2020-01-01' + (random()*1460)::int)::date                               AS joined_date,
    ROUND((random()*50000 + 500)::numeric, 2)                                      AS lifetime_value
FROM generate_series(1, 300) g;

-- ── Monthly targets table ────────────────────────────────────
CREATE TABLE IF NOT EXISTS monthly_targets (
    id         SERIAL PRIMARY KEY,
    year       INTEGER NOT NULL,
    month      INTEGER NOT NULL,
    region     TEXT    NOT NULL,
    target     NUMERIC(12,2) NOT NULL,
    achieved   NUMERIC(12,2) NOT NULL
);

INSERT INTO monthly_targets (year, month, region, target, achieved)
SELECT
    yr,
    mo,
    region,
    ROUND((random()*80000 + 20000)::numeric, 2)                                    AS target,
    ROUND((random()*90000 + 15000)::numeric, 2)                                    AS achieved
FROM
    generate_series(2024, 2025)                           yr,
    generate_series(1, 12)                                mo,
    unnest(ARRAY['North','South','East','West','Central']) region;
