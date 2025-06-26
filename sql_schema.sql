-- Enable UUID generation if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Function to update 'updated_at' column automatically (re-defined for clarity)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Table for Menu Items
-- DROP TABLE IF EXISTS menu_items CASCADE; -- Uncomment to drop if recreating database
CREATE TABLE menu_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
DROP TRIGGER IF EXISTS update_menu_items_updated_at ON menu_items; -- Drop old trigger if re-running
CREATE TRIGGER update_menu_items_updated_at
BEFORE UPDATE ON menu_items
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();


-- Table for Users (Admins)
-- DROP TABLE IF EXISTS users CASCADE; -- Uncomment to drop if recreating database
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'customer' NOT NULL, -- 'admin', 'customer'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Trigger for users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users; -- Drop old trigger if re-running
CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();


-- Define the ENUM type for reservation status (THIS IS THE KEY CHANGE)
-- DROP TYPE IF EXISTS reservation_status_enum; -- Uncomment to drop if you've already created it and need to change values
CREATE TYPE reservation_status_enum AS ENUM ('pending', 'confirmed', 'cancelled', 'completed', 'no_show');

-- Table for Reservations
-- DROP TABLE IF EXISTS reservations CASCADE; -- Uncomment to drop if recreating database
CREATE TABLE reservations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
DROP TRIGGER IF EXISTS update_reservations_updated_at ON reservations; -- Drop old trigger if re-running
CREATE TRIGGER update_reservations_updated_at
BEFORE UPDATE ON reservations
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Optional: Create an initial admin user (replace with strong password!)
-- You'll need to hash 'adminpassword' using bcrypt, or do this via the API once deployed
-- INSERT INTO users (username, hashed_password, role) VALUES ('admin', '$2b$12$...your_hashed_password...', 'admin');
