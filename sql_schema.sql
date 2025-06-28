-- Enable UUID generation if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Function to update 'updated_at' column automatically
-- This function is used by multiple tables, so define it once at the top.
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Table for Menu Items
-- Consider adding DROP TABLE IF EXISTS menu_items CASCADE; if running on an existing DB for full reset
CREATE TABLE menu_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4 (),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL,
    category VARCHAR(100),
    image_url TEXT, -- URL to the image storage (e.g., AWS S3, Cloudinary, etc.)
    is_available BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Trigger for menu_items table
DROP TRIGGER IF EXISTS update_menu_items_updated_at ON menu_items;

CREATE TRIGGER update_menu_items_updated_at
BEFORE UPDATE ON menu_items
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Table for Users (Admins)
-- Consider adding DROP TABLE IF EXISTS users CASCADE; if running on an existing DB for full reset
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4 (),
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    ROLE VARCHAR(50) DEFAULT 'customer' NOT NULL, -- 'admin', 'customer'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Trigger for users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users;

CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Define the ENUM type for reservation status
-- DROP TYPE IF EXISTS reservation_status_enum; -- Uncomment to drop if you've already created it and need to change values
CREATE TYPE reservation_status_enum AS ENUM ('pending', 'confirmed', 'cancelled', 'completed', 'no_show');

-- Table for Reservations
-- Consider adding DROP TABLE IF EXISTS reservations CASCADE; if running on an existing DB for full reset
CREATE TABLE reservations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4 (),
    customer_name VARCHAR(255) NOT NULL,
    customer_email VARCHAR(255) NOT NULL,
    customer_phone VARCHAR(50) NOT NULL,
    reservation_date DATE NOT NULL,
    reservation_time TIME WITHOUT TIME ZONE NOT NULL,
    number_of_guests INTEGER NOT NULL,
    status reservation_status_enum NOT NULL DEFAULT 'pending', -- Use the ENUM type here
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    -- The CHECK constraint is no longer needed because the ENUM type handles validation
);

-- Trigger for reservations table
DROP TRIGGER IF EXISTS update_reservations_updated_at ON reservations;

CREATE TRIGGER update_reservations_updated_at
BEFORE UPDATE ON reservations
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Table for Orders
-- DROP TABLE IF EXISTS orders CASCADE; -- Uncomment to drop if recreating database
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4 (),
    reservation_id UUID UNIQUE NOT NULL, -- One order per completed reservation
    total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    order_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reservation FOREIGN KEY (reservation_id) REFERENCES reservations (id) ON DELETE CASCADE -- If reservation is deleted, delete its order
);

-- Trigger for orders table
DROP TRIGGER IF EXISTS update_orders_updated_at ON orders;

CREATE TRIGGER update_orders_updated_at
BEFORE UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Table for Order Items
-- DROP TABLE IF EXISTS order_items CASCADE; -- Uncomment to drop if recreating database
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4 (),
    order_id UUID NOT NULL,
    menu_item_id UUID NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price_at_order NUMERIC(10, 2) NOT NULL, -- Price of the item when it was ordered
    subtotal NUMERIC(10, 2) NOT NULL, -- quantity * price_at_order
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_order FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE, -- If an order is deleted, delete its items
    CONSTRAINT fk_menu_item FOREIGN KEY (menu_item_id) REFERENCES menu_items (id) ON DELETE RESTRICT -- Do not allow deleting a menu item if it's part of an existing order
);

-- Trigger for order_items table
DROP TRIGGER IF EXISTS update_order_items_updated_at ON order_items;

CREATE TRIGGER update_order_items_updated_at
BEFORE UPDATE ON order_items
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Table for Revenue Records
-- DROP TABLE IF EXISTS revenue_records CASCADE; -- Uncomment to drop if recreating database
CREATE TABLE revenue_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4 (),
    order_id UUID NOT NULL UNIQUE, -- One revenue record per order
    reservation_id UUID NOT NULL, -- Denormalized for easier lookup if needed
    amount NUMERIC(10, 2) NOT NULL,
    record_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_revenue_order FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE, -- If an order is deleted, delete its revenue record
    CONSTRAINT fk_revenue_reservation FOREIGN KEY (reservation_id) REFERENCES reservations (id) ON DELETE RESTRICT -- Don't delete reservation if revenue is linked (though cascading from order would handle this)
);

-- Trigger for revenue_records table (to update its own updated_at)
DROP TRIGGER IF EXISTS update_revenue_records_updated_at ON revenue_records;

CREATE TRIGGER update_revenue_records_updated_at
BEFORE UPDATE ON revenue_records
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Function to handle inserting/updating revenue records based on orders
CREATE OR REPLACE FUNCTION record_order_revenue()
RETURNS TRIGGER AS $$
BEGIN
    -- Insert a new record or update an existing one for the order's total amount
    INSERT INTO revenue_records (order_id, reservation_id, amount)
    VALUES (NEW.id, NEW.reservation_id, NEW.total_amount)
    ON CONFLICT (order_id) DO UPDATE SET
        amount = EXCLUDED.amount,
        record_date = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to fire after an order's total_amount is inserted or updated
DROP TRIGGER IF EXISTS trg_record_order_revenue ON orders;

CREATE TRIGGER trg_record_order_revenue
AFTER INSERT OR UPDATE OF total_amount ON orders
FOR EACH ROW
EXECUTE FUNCTION record_order_revenue();

-- Optional: Create an initial admin user (replace with strong password!)
-- You'll need to hash 'adminpassword' using bcrypt, or do this via the API once deployed
-- INSERT INTO users (username, hashed_password, role) VALUES ('admin', '$2b$12$...your_hashed_password...', 'admin');