import os
from datetime import date
from typing import List, Optional, Literal
from uuid import UUID

from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
from models import (
    MenuItemResponse, MenuItemCreate, MenuItemUpdate,
    ReservationResponse, ReservationCreate, ReservationUpdate,
    UserResponse, Token, ErrorResponse, UserCreate # <--- ENSURE Token is now here, and UserCreate too!
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

# --- CORS Middleware (Crucial for Frontend Communication) ---
from fastapi.middleware.cors import CORSMiddleware

origins = [
    "http://localhost:5173",  # Your React dev server
    # Add your Vercel frontend URL here when deployed, e.g., "https://your-frontend-app.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],    # Allows all methods (GET, POST, PUT, DELETE, OPTIONS)
    allow_headers=["*"],    # Allows all headers (including Authorization)
)