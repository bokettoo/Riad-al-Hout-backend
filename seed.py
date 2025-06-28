import os
import random
import uuid
from datetime import datetime, timedelta, date, time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from dotenv import load_dotenv

# --- Configuration (Load from .env) ---
load_dotenv() # Load environment variables from .env file

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Please set it in your .env file.")

# Password hashing context (must match auth.py)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Database Setup (reusing parts of database.py) ---
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Utility Function for Hashing Password (reusing from auth.py concept) ---
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# --- Main Seeder Function ---
def seed_database():
    db = next(get_db()) # Get a single database session
    try:
        print("Starting database seeding...")

        # --- 0. Clear existing data (OPTIONAL, but useful for fresh seeding) ---
        # USE WITH CAUTION! This will delete ALL data from these tables.
        confirm_clear = input("Type 'clear' to confirm clearing existing data before seeding (all data will be lost): ")
        if confirm_clear.lower() == 'clear':
            print("Clearing existing data...")
            db.execute(text("DELETE FROM revenue_records;"))
            db.execute(text("DELETE FROM order_items;"))
            db.execute(text("DELETE FROM orders;"))
            db.execute(text("DELETE FROM reservations;"))
            db.execute(text("DELETE FROM users WHERE username != 'admin';")) # Keep the first manually created admin if it exists
            db.commit()
            print("Existing data cleared.")
        else:
            print("Skipping data clearing.")

        # --- 1. Seed Admin User (if not exists) ---
        admin_username = "admin"
        admin_password = "adminpassword" # CHANGE THIS TO A SECURE PASSWORD FOR REAL USE!

        existing_admin = db.execute(text("SELECT id FROM users WHERE username = :username"), {"username": admin_username}).fetchone()
        if not existing_admin:
            print(f"Creating admin user: {admin_username}...")
            hashed_admin_password = get_password_hash(admin_password)
            db.execute(text("INSERT INTO users (username, hashed_password, role) VALUES (:username, :hashed_password, 'admin')"),
                       {"username": admin_username, "hashed_password": hashed_admin_password})
            db.commit()
            print(f"Admin user '{admin_username}' created.")
        else:
            print(f"Admin user '{admin_username}' already exists. Skipping creation.")

        # --- 2. Fetch Existing Menu Items (CRITICAL for Order Items) ---
        print("Fetching existing menu items...")
        menu_items_result = db.execute(text("SELECT id, name, price FROM menu_items")).fetchall()
        
        # Ensure menu_items are present before trying to create orders
        if not menu_items_result:
            print("WARNING: No menu items found in the database. Please insert menu items first before seeding orders.")
            print("Seeding process aborted for reservations and orders.")
            return

        # Convert to list of dicts for easier use
        menu_items = [{ 'id': item[0], 'name': item[1], 'price': float(item[2]) } for item in menu_items_result]
        print(f"Fetched {len(menu_items)} menu items.")


        # --- 3. Seed Reservations and Orders ---
        print("Seeding historical reservations and orders...")
        
        # Date range: 1 month (30 days) prior to June 27, 2025
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 26) # The day before June 27, 2025
        
        current_date = start_date
        while current_date <= end_date:
            num_reservations_today = random.randint(5, 10) # 5 to 10 reservations per day
            
            for i in range(num_reservations_today):
                reservation_id = uuid.uuid4()
                customer_name = f"Guest {current_date.strftime('%m%d')}-{i+1}"
                customer_email = f"guest{current_date.strftime('%m%d')}{i+1}@example.com"
                customer_phone = f"0{random.randint(6,7)}{random.randint(10000000, 99999999)}"
                
                # Statuses as requested: completed, no_show, cancelled
                status = random.choice(['completed', 'no_show', 'cancelled'])
                
                res_time = time(random.randint(18, 22), random.choice([0, 15, 30, 45]))
                num_guests = random.randint(2, 8)
                notes = "No specific notes." if random.random() < 0.7 else f"Special request {random.randint(1,5)}."

                # Insert Reservation
                db.execute(text(
                    "INSERT INTO reservations (id, customer_name, customer_email, customer_phone, reservation_date, reservation_time, number_of_guests, status, notes) "
                    "VALUES (:id, :customer_name, :customer_email, :customer_phone, :reservation_date, :reservation_time, :number_of_guests, :status, :notes)"
                ), {
                    "id": reservation_id,
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "customer_phone": customer_phone,
                    "reservation_date": current_date,
                    "reservation_time": res_time,
                    "number_of_guests": num_guests,
                    "status": status,
                    "notes": notes if notes != "No specific notes." else None
                })
                
                # If status is 'completed', create an order
                if status == 'completed':
                    order_id = uuid.uuid4()
                    current_order_total = 0.0
                    order_items_data = []

                    # Insert Order (initial total_amount 0.0, will be updated)
                    db.execute(text(
                        "INSERT INTO orders (id, reservation_id, total_amount, order_date) "
                        "VALUES (:id, :reservation_id, :total_amount, :order_date)"
                    ), {
                        "id": order_id,
                        "reservation_id": reservation_id,
                        "total_amount": 0.0,
                        "order_date": datetime.now() # Use current datetime for order creation
                    })

                    # Generate Order Items
                    num_order_items = random.randint(1, min(5, len(menu_items))) # Max 5 items per order
                    selected_items_for_order = random.sample(menu_items, num_order_items) # Pick unique items

                    for item_data in selected_items_for_order:
                        quantity = random.randint(1, num_guests // 2 if num_guests > 1 else 1) or 1
                        price_at_order = item_data['price']
                        subtotal = price_at_order * quantity
                        current_order_total += subtotal

                        order_items_data.append({
                            "id": uuid.uuid4(),
                            "order_id": order_id,
                            "menu_item_id": item_data['id'],
                            "quantity": quantity,
                            "price_at_order": price_at_order,
                            "subtotal": subtotal
                        })
                    
                    # Insert Order Items (batch insert for performance)
                    if order_items_data:
                        db.execute(text(
                            "INSERT INTO order_items (id, order_id, menu_item_id, quantity, price_at_order, subtotal) VALUES " +
                            ", ".join([f"(:id_{j}, :order_id_{j}, :menu_item_id_{j}, :quantity_{j}, :price_at_order_{j}, :subtotal_{j})" for j in range(len(order_items_data))])
                        ), {f"{key}_{j}": value for j, item in enumerate(order_items_data) for key, value in item.items()})


                    # Update the Order's total_amount (THIS WILL TRIGGER REVENUE_RECORDS)
                    db.execute(text(
                        "UPDATE orders SET total_amount = :total_amount WHERE id = :id"
                    ), {
                        "total_amount": current_order_total,
                        "id": order_id
                    })
            
            db.commit() # Commit after each day's reservations/orders
            current_date += timedelta(days=1)
        
        print("Database seeding completed successfully.")

    except Exception as e:
        db.rollback()
        print(f"An error occurred during seeding: {e}")
    finally:
        db.close()

# --- Run Seeder ---
if __name__ == "__main__":
    seed_database()
