import os
from datetime import date, datetime
from typing import List, Optional, Literal, Dict
from uuid import UUID

from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
from models import (
    MenuItemResponse, MenuItemCreate, MenuItemUpdate,
    ReservationResponse, ReservationCreate, ReservationUpdate,
    UserResponse, Token, ErrorResponse, UserCreate, # <--- ENSURE Token is now here, and UserCreate too!
    OrderItemCreate, OrderItemResponse,
    OrderCreate, OrderResponse,RevenueRecordResponse
)
from auth import authenticate_user, create_access_token, get_current_admin_user, get_password_hash, get_current_user
from dotenv import load_dotenv
# Load environment variables
load_dotenv()

# FastAPI App instance
app = FastAPI(
    title="Neptune's Bounty Restaurant API",
    description="Backend API for managing menu items, reservations, and admin users.",
    version="1.0.0",
    docs_url="/api/docs", # Custom docs path
    redoc_url="/api/redoc" # Custom redoc path
)

# --- Health Check ---
@app.get("/api/health", summary="Health check endpoint")
async def health_check():
    return {"status": "ok", "message": "API is running"}

# --- Authentication Endpoints ---
@app.post("/api/token", response_model=Token, summary="Login and get an access token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    return {"access_token": access_token, "token_type": "bearer", "user_role": user.role}

# Optional: Endpoint to create an admin user (for initial setup, protect this heavily!)
@app.post("/api/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create a new user (admin or customer)")
async def create_user(user_create: UserCreate, db: Session = Depends(get_db),
                      current_admin: UserResponse = Depends(get_current_admin_user)): # Only admins can create users for now
    from sqlalchemy import text
    try:
        # Check if username already exists
        existing_user_query = text("SELECT id FROM users WHERE username = :username")
        existing_user_result = db.execute(existing_user_query, {"username": user_create.username}).fetchone()
        if existing_user_result:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

        hashed_password = get_password_hash(user_create.password)
        insert_query = text(
            "INSERT INTO users (username, hashed_password, role) VALUES (:username, :hashed_password, :role) RETURNING id, username, role, created_at, updated_at"
        )
        result = db.execute(insert_query, {
            "username": user_create.username,
            "hashed_password": hashed_password,
            "role": user_create.role
        }).fetchone()

        db.commit()

        if result:
            user_data = {
                "id": result[0],
                "username": result[1],
                "role": result[2],
                "created_at": result[3],
                "updated_at": result[4]
            }
            return UserResponse(**user_data)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User creation failed")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# --- Auth: Get Current User ---
@app.get("/api/users/me", response_model=UserResponse, summary="Get current user info")
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    return current_user

# --- Auth: Logout (dummy for JWT) ---
@app.post("/api/auth/logout", status_code=204, summary="Logout (dummy endpoint for JWT)")
async def logout(response: Response):
    # For JWT, logout is handled client-side by deleting the token
    return Response(status_code=204)

# --- Auth: Refresh Token (not implemented) ---
@app.post("/api/auth/refresh-token", summary="Refresh JWT token (not implemented)")
async def refresh_token():
    from fastapi import HTTPException
    raise HTTPException(status_code=501, detail="Refresh token not implemented. Use short-lived JWTs or implement refresh logic.")

# --- Menu Item Endpoints ---
@app.get("/api/menu", response_model=List[MenuItemResponse], summary="Get all menu items")
async def get_all_menu_items(db: Session = Depends(get_db)):
    query = text("SELECT id, name, description, price, category, image_url, is_available, created_at, updated_at FROM menu_items ORDER BY category, name")
    result = db.execute(query).fetchall()
    return [MenuItemResponse(**item._asdict()) for item in result] # Convert RowProxy to dict

@app.get("/api/menu/{menu_item_id}", response_model=MenuItemResponse, summary="Get a specific menu item by ID")
async def get_menu_item(menu_item_id: UUID, db: Session = Depends(get_db)):
    query = text("SELECT id, name, description, price, category, image_url, is_available, created_at, updated_at FROM menu_items WHERE id = :id")
    result = db.execute(query, {"id": menu_item_id}).fetchone()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    return MenuItemResponse(**result._asdict())

@app.post("/api/menu", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED, summary="Create a new menu item (Admin only)")
async def create_menu_item(menu_item: MenuItemCreate, db: Session = Depends(get_db), current_admin: UserResponse = Depends(get_current_admin_user)):
    try:
        insert_query = text(
            "INSERT INTO menu_items (name, description, price, category, image_url, is_available) "
            "VALUES (:name, :description, :price, :category, :image_url, :is_available) "
            "RETURNING id, name, description, price, category, image_url, is_available, created_at, updated_at"
        )
        result = db.execute(insert_query, menu_item.model_dump()).fetchone() # Use model_dump() for Pydantic v2
        db.commit()
        if result:
            return MenuItemResponse(**result._asdict())
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create menu item")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.put("/api/menu/{menu_item_id}", response_model=MenuItemResponse, summary="Update an existing menu item (Admin only)")
async def update_menu_item(menu_item_id: UUID, menu_item: MenuItemUpdate, db: Session = Depends(get_db), current_admin: UserResponse = Depends(get_current_admin_user)):
    # Build update query dynamically based on provided fields
    set_clauses = []
    update_data = menu_item.model_dump(exclude_unset=True) # Only include fields that were set
    for key, value in update_data.items():
        if key in ["name", "description", "price", "category", "image_url", "is_available"]:
            set_clauses.append(f"{key} = :{key}")

    if not set_clauses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    update_query = text(
        f"UPDATE menu_items SET {', '.join(set_clauses)}, updated_at = NOW() "
        f"WHERE id = :id RETURNING id, name, description, price, category, image_url, is_available, created_at, updated_at"
    )
    try:
        # Add ID to update_data for the WHERE clause
        update_data['id'] = menu_item_id
        result = db.execute(update_query, update_data).fetchone()
        db.commit()
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
        return MenuItemResponse(**result._asdict())
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.delete("/api/menu/{menu_item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a menu item (Admin only)")
async def delete_menu_item(menu_item_id: UUID, db: Session = Depends(get_db), current_admin: UserResponse = Depends(get_current_admin_user)):
    delete_query = text("DELETE FROM menu_items WHERE id = :id RETURNING id")
    try:
        result = db.execute(delete_query, {"id": menu_item_id}).fetchone()
        db.commit()
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
        return # 204 No Content
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# --- Reservation Endpoints ---
@app.post("/api/reservations", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED, summary="Create a new reservation")
async def create_reservation(reservation: ReservationCreate, db: Session = Depends(get_db)):
    try:
        insert_query = text(
            "INSERT INTO reservations (customer_name, customer_email, customer_phone, reservation_date, reservation_time, number_of_guests, status, notes) "
            "VALUES (:customer_name, :customer_email, :customer_phone, :reservation_date, :reservation_time, :number_of_guests, :status, :notes) "
            "RETURNING id, customer_name, customer_email, customer_phone, reservation_date, reservation_time, number_of_guests, status, notes, created_at, updated_at"
        )
        result = db.execute(insert_query, reservation.model_dump()).fetchone()
        db.commit()
        if result:
            return ReservationResponse(**result._asdict())
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create reservation")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.get("/api/reservations", response_model=List[ReservationResponse], summary="Get all reservations (Admin only)")
async def get_all_reservations(
    db: Session = Depends(get_db),
    reservation_date: Optional[date] = None, # Filter by date
    current_admin: UserResponse = Depends(get_current_admin_user)
):
    query_str = "SELECT id, customer_name, customer_email, customer_phone, reservation_date, reservation_time, number_of_guests, status, notes, created_at, updated_at FROM reservations"
    where_clauses = []
    params = {}

    if reservation_date:
        where_clauses.append("reservation_date = :reservation_date")
        params["reservation_date"] = reservation_date

    if where_clauses:
        query_str += " WHERE " + " AND ".join(where_clauses)

    query_str += " ORDER BY reservation_date ASC, reservation_time ASC"

    result = db.execute(text(query_str), params).fetchall()
    return [ReservationResponse(**item._asdict()) for item in result]

@app.get("/api/reservations/today", response_model=List[ReservationResponse], summary="Get today's reservations (Admin only)")
async def get_todays_reservations(db: Session = Depends(get_db), current_admin: UserResponse = Depends(get_current_admin_user)):
    today = date.today()
    query = text(
        "SELECT id, customer_name, customer_email, customer_phone, reservation_date, reservation_time, number_of_guests, status, notes, created_at, updated_at "
        "FROM reservations WHERE reservation_date = :today_date ORDER BY reservation_time ASC"
    )
    result = db.execute(query, {"today_date": today}).fetchall()
    return [ReservationResponse(**item._asdict()) for item in result]


@app.put("/api/reservations/{reservation_id}", response_model=ReservationResponse, summary="Update an existing reservation (Admin only)")
async def update_reservation(reservation_id: UUID, reservation: ReservationUpdate, db: Session = Depends(get_db), current_admin: UserResponse = Depends(get_current_admin_user)):
    set_clauses = []
    update_data = reservation.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key in ["customer_name", "customer_email", "customer_phone", "reservation_date", "reservation_time", "number_of_guests", "status", "notes"]:
            set_clauses.append(f"{key} = :{key}")

    if not set_clauses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    update_query = text(
        f"UPDATE reservations SET {', '.join(set_clauses)}, updated_at = NOW() "
        f"WHERE id = :id RETURNING id, customer_name, customer_email, customer_phone, reservation_date, reservation_time, number_of_guests, status, notes, created_at, updated_at"
    )
    try:
        update_data['id'] = reservation_id
        result = db.execute(update_query, update_data).fetchone()
        db.commit()
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
        return ReservationResponse(**result._asdict())
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.delete("/api/reservations/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a reservation (Admin only)")
async def delete_reservation(reservation_id: UUID, db: Session = Depends(get_db), current_admin: UserResponse = Depends(get_current_admin_user)):
    delete_query = text("DELETE FROM reservations WHERE id = :id RETURNING id")
    try:
        result = db.execute(delete_query, {"id": reservation_id}).fetchone()
        db.commit()
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
        return # 204 No Content
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.post("/api/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, summary="Create a new order for a reservation (Admin only)")
async def create_order(
    order_create: OrderCreate,
    db: Session = Depends(get_db),
    current_admin: UserResponse = Depends(get_current_admin_user)
):
    # 1. Check if reservation exists and is completed
    reservation_query = text("SELECT status FROM reservations WHERE id = :reservation_id")
    reservation_status = db.execute(reservation_query, {"reservation_id": order_create.reservation_id}).scalar_one_or_none()

    if not reservation_status:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    if reservation_status != 'completed': # Ensure reservation is 'completed'
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Order can only be created for completed reservations. Current status: {reservation_status}")

    # 2. Check if an order already exists for this reservation (UNIQUE constraint)
    existing_order_query = text("SELECT id FROM orders WHERE reservation_id = :reservation_id")
    existing_order_id = db.execute(existing_order_query, {"reservation_id": order_create.reservation_id}).scalar_one_or_none()
    if existing_order_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An order already exists for this reservation.")

    total_amount = 0.0
    order_items_to_insert = []
    inserted_order_items_response = []

    try:
        # 3. Create the main Order entry first
        insert_order_query = text(
            "INSERT INTO orders (reservation_id) VALUES (:reservation_id) "
            "RETURNING id, total_amount, order_date, created_at, updated_at"
        )
        order_result = db.execute(insert_order_query, {"reservation_id": order_create.reservation_id}).fetchone()
        db.commit() # Commit the order creation before adding items

        if not order_result:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create order.")

        new_order_id = order_result[0]

        # 4. Process each OrderItem
        for item_data in order_create.items:
            # Fetch menu item price
            menu_item_query = text("SELECT price FROM menu_items WHERE id = :menu_item_id")
            menu_item_price = db.execute(menu_item_query, {"menu_item_id": item_data.menu_item_id}).scalar_one_or_none()

            if menu_item_price is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Menu item with ID {item_data.menu_item_id} not found.")

            subtotal = float(menu_item_price) * item_data.quantity
            total_amount += subtotal

            order_items_to_insert.append({
                "order_id": new_order_id,
                "menu_item_id": item_data.menu_item_id,
                "quantity": item_data.quantity,
                "price_at_order": float(menu_item_price),
                "subtotal": subtotal
            })

        # 5. Insert OrderItems in a single batch (or individually if preferred)
        if order_items_to_insert:
            insert_order_items_query = text(
                "INSERT INTO order_items (order_id, menu_item_id, quantity, price_at_order, subtotal) VALUES "
                + ", ".join([f"(:order_id_{i}, :menu_item_id_{i}, :quantity_{i}, :price_at_order_{i}, :subtotal_{i})" for i in range(len(order_items_to_insert))])
                + " RETURNING id, order_id, menu_item_id, quantity, price_at_order, subtotal, created_at, updated_at"
            )
            # Prepare parameters for batch insert
            params = {}
            for i, item in enumerate(order_items_to_insert):
                for key, value in item.items():
                    params[f"{key}_{i}"] = value

            order_items_results = db.execute(insert_order_items_query, params).fetchall()
            inserted_order_items_response = [OrderItemResponse(**item._asdict()) for item in order_items_results]

        # 6. Update the Order's total_amount
        update_order_total_query = text(
            "UPDATE orders SET total_amount = :total_amount WHERE id = :order_id "
            "RETURNING id, total_amount, order_date, created_at, updated_at"
        )
        updated_order_result = db.execute(update_order_total_query, {"total_amount": total_amount, "order_id": new_order_id}).fetchone()
        db.commit()

        return OrderResponse(
            id=updated_order_result[0],
            reservation_id=order_create.reservation_id,
            total_amount=updated_order_result[1],
            order_date=updated_order_result[2],
            created_at=updated_order_result[3],
            updated_at=updated_order_result[4],
            items=inserted_order_items_response
        )

    except HTTPException as e: # Catch HTTPExceptions raised within the try block
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")

@app.get("/api/orders/{order_id}", response_model=OrderResponse, summary="Get an order by ID (Admin only)")
async def get_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_admin: UserResponse = Depends(get_current_admin_user)
):
    order_query = text(
        "SELECT id, reservation_id, total_amount, order_date, created_at, updated_at FROM orders WHERE id = :order_id"
    )
    order_result = db.execute(order_query, {"order_id": order_id}).fetchone()
    if not order_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order_items_query = text(
        "SELECT id, order_id, menu_item_id, quantity, price_at_order, subtotal, created_at, updated_at FROM order_items WHERE order_id = :order_id"
    )
    order_items_results = db.execute(order_items_query, {"order_id": order_id}).fetchall()
    items_response = [OrderItemResponse(**item._asdict()) for item in order_items_results]

    return OrderResponse(
        id=order_result[0],
        reservation_id=order_result[1],
        total_amount=order_result[2],
        order_date=order_result[3],
        created_at=order_result[4],
        updated_at=order_result[5],
        items=items_response
    )
# main.py (Add this new API route below your existing order endpoints)

@app.delete("/api/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an order by ID (Admin only)")
async def delete_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_admin: UserResponse = Depends(get_current_admin_user)
):
    delete_query = text("DELETE FROM orders WHERE id = :id RETURNING id")
    try:
        result = db.execute(delete_query, {"id": order_id}).fetchone()
        db.commit()
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return # 204 No Content response
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/api/reservations/{reservation_id}/order", response_model=Optional[OrderResponse], summary="Get order linked to a reservation (Admin only)")
async def get_order_by_reservation_id(
    reservation_id: UUID,
    db: Session = Depends(get_db),
    current_admin: UserResponse = Depends(get_current_admin_user)
):
    order_query = text(
        "SELECT id, reservation_id, total_amount, order_date, created_at, updated_at FROM orders WHERE reservation_id = :reservation_id"
    )
    order_result = db.execute(order_query, {"reservation_id": reservation_id}).fetchone()
    if not order_result:
        return None # No order found for this reservation

    order_items_query = text(
        "SELECT id, order_id, menu_item_id, quantity, price_at_order, subtotal, created_at, updated_at FROM order_items WHERE order_id = :order_id"
    )
    order_items_results = db.execute(order_items_query, {"order_id": order_result[0]}).fetchall()
    items_response = [OrderItemResponse(**item._asdict()) for item in order_items_results]

    return OrderResponse(
        id=order_result[0],
        reservation_id=order_result[1],
        total_amount=order_result[2],
        order_date=order_result[3],
        created_at=order_result[4],
        updated_at=order_result[5],
        items=items_response
    )

@app.put("/api/orders/{order_id}", response_model=OrderResponse, summary="Update an existing order (Admin only)")
async def update_order(
    order_id: UUID,
    order_update: OrderCreate,
    db: Session = Depends(get_db),
    current_admin: UserResponse = Depends(get_current_admin_user)
):
    # 1. Check if order exists and matches reservation_id
    order_query = text("SELECT id, reservation_id FROM orders WHERE id = :order_id")
    order_result = db.execute(order_query, {"order_id": order_id}).fetchone()
    if not order_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if str(order_result[1]) != str(order_update.reservation_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reservation ID mismatch for this order.")

    try:
        # 2. Delete all existing order_items for this order
        delete_items_query = text("DELETE FROM order_items WHERE order_id = :order_id")
        db.execute(delete_items_query, {"order_id": order_id})
        db.commit()

        # 3. Insert new order_items
        total_amount = 0.0
        order_items_to_insert = []
        for item_data in order_update.items:
            # Fetch menu item price
            menu_item_query = text("SELECT price FROM menu_items WHERE id = :menu_item_id")
            menu_item_price = db.execute(menu_item_query, {"menu_item_id": item_data.menu_item_id}).scalar_one_or_none()
            if menu_item_price is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Menu item with ID {item_data.menu_item_id} not found.")
            subtotal = float(menu_item_price) * item_data.quantity
            total_amount += subtotal
            order_items_to_insert.append({
                "order_id": order_id,
                "menu_item_id": item_data.menu_item_id,
                "quantity": item_data.quantity,
                "price_at_order": float(menu_item_price),
                "subtotal": subtotal
            })
        # Insert new order_items in batch
        if order_items_to_insert:
            insert_order_items_query = text(
                "INSERT INTO order_items (order_id, menu_item_id, quantity, price_at_order, subtotal) VALUES "
                + ", ".join([f"(:order_id_{i}, :menu_item_id_{i}, :quantity_{i}, :price_at_order_{i}, :subtotal_{i})" for i in range(len(order_items_to_insert))])
                + " RETURNING id, order_id, menu_item_id, quantity, price_at_order, subtotal, created_at, updated_at"
            )
            params = {}
            for i, item in enumerate(order_items_to_insert):
                for key, value in item.items():
                    params[f"{key}_{i}"] = value
            order_items_results = db.execute(insert_order_items_query, params).fetchall()
            inserted_order_items_response = [OrderItemResponse(**item._asdict()) for item in order_items_results]
        else:
            inserted_order_items_response = []
        # 4. Update order's total_amount
        update_order_total_query = text(
            "UPDATE orders SET total_amount = :total_amount, updated_at = NOW() WHERE id = :order_id "
            "RETURNING id, reservation_id, total_amount, order_date, created_at, updated_at"
        )
        updated_order_result = db.execute(update_order_total_query, {"total_amount": total_amount, "order_id": order_id}).fetchone()
        db.commit()
        return OrderResponse(
            id=updated_order_result[0],
            reservation_id=updated_order_result[1],
            total_amount=updated_order_result[2],
            order_date=updated_order_result[3],
            created_at=updated_order_result[4],
            updated_at=updated_order_result[5],
            items=inserted_order_items_response
        )
    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")

@app.get("/api/revenue", response_model=List[RevenueRecordResponse], summary="Get all revenue records (Admin only)")
async def get_all_revenue_records(
    db: Session = Depends(get_db),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_admin: UserResponse = Depends(get_current_admin_user)
):
    query_str = "SELECT id, order_id, reservation_id, amount, record_date, created_at, updated_at FROM revenue_records"
    where_clauses = []
    params = {}

    if start_date:
        where_clauses.append("CAST(record_date AS DATE) >= :start_date")
        params["start_date"] = start_date

    if end_date:
        where_clauses.append("CAST(record_date AS DATE) <= :end_date")
        params["end_date"] = end_date

    if where_clauses:
        query_str += " WHERE " + " AND ".join(where_clauses)

    query_str += " ORDER BY record_date DESC, created_at DESC" # Order by most recent first

    result = db.execute(text(query_str), params).fetchall()
    return [RevenueRecordResponse(**item._asdict()) for item in result]

@app.get("/api/revenue/summary", response_model=Dict[str, float], summary="Get total revenue summary (Admin only)")
async def get_total_revenue_summary(
    db: Session = Depends(get_db),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_admin: UserResponse = Depends(get_current_admin_user)
):
    query_str = "SELECT SUM(amount) FROM revenue_records"
    where_clauses = []
    params = {}

    if start_date:
        where_clauses.append("CAST(record_date AS DATE) >= :start_date")
        params["start_date"] = start_date

    if end_date:
        where_clauses.append("CAST(record_date AS DATE) <= :end_date")
        params["end_date"] = end_date

    if where_clauses:
        query_str += " WHERE " + " AND ".join(where_clauses)

    total_revenue = db.execute(text(query_str), params).scalar_one_or_none()
    return {"total_revenue": float(total_revenue) if total_revenue is not None else 0.00}

@app.get("/api/stats/most-sold-items", summary="Get most sold menu items (Admin only)")
async def get_most_sold_items(
    db: Session = Depends(get_db),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_admin: UserResponse = Depends(get_current_admin_user)
):
    # Join order_items and menu_items, group by menu_item_id, sum quantity
    query = """
        SELECT
            oi.menu_item_id,
            mi.name,
            mi.category,
            mi.price,
            SUM(oi.quantity) AS total_quantity
        FROM order_items oi
        JOIN menu_items mi ON oi.menu_item_id = mi.id
        JOIN orders o ON oi.order_id = o.id
        JOIN reservations r ON o.reservation_id = r.id
        {where_clause}
        GROUP BY oi.menu_item_id, mi.name, mi.category, mi.price
        ORDER BY total_quantity DESC, mi.name ASC
        LIMIT 20
    """
    where_clauses = []
    params = {}
    if start_date:
        where_clauses.append("r.reservation_date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where_clauses.append("r.reservation_date <= :end_date")
        params["end_date"] = end_date
    where_clause = ""
    if where_clauses:
        where_clause = "WHERE " + " AND ".join(where_clauses)
    final_query = query.format(where_clause=where_clause)
    result = db.execute(text(final_query), params).fetchall()
    return [
        {
            "menu_item_id": str(row.menu_item_id),
            "name": row.name,
            "category": row.category,
            "price": float(row.price),
            "total_quantity": int(row.total_quantity)
        }
        for row in result
    ]

# --- CORS Middleware (Crucial for Frontend Communication) ---
from fastapi.middleware.cors import CORSMiddleware

origins = [
    "http://localhost:5173",  # Your React dev server
    "https://riad-al-hout.vercel.app/" #vercel 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],    # Allows all methods (GET, POST, PUT, DELETE, OPTIONS)
    allow_headers=["*"],    # Allows all headers (including Authorization)
)

if __name__ == "__main__":
    import uvicorn
    # Ensure dotenv.load_dotenv() is called early in main.py (should already be at the top)
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=12447,
        reload=True,
        log_level="info"
    )