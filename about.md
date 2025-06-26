# "Neptune's Bounty" Backend Specification

## Project Overview

"Neptune's Bounty" is a high-end seafood restaurant requiring a robust and efficient backend to manage menu items, customer reservations, and administrative access. This document outlines the API specifications for the frontend, leveraging a **Python FastAPI backend** and a **PostgreSQL database**.

## Backend Technologies

* **API Framework:** FastAPI (Python)
* **Database:** PostgreSQL (self-managed or cloud-hosted by the developer - *not* part of this codebase, but connected to).
* **Authentication:** JWT (JSON Web Tokens) for API security.
* **File Storage:** (To be handled by a separate service, e.g., AWS S3, Cloudinary, etc., as the Python backend will only store URLs to images, not the images themselves). *This aspect requires a decision on your part and will need frontend integration with that chosen service.*
* **Deployment:** Vercel (as serverless functions).

## Authentication & Authorization (Custom Backend Logic)

* **User Roles:** `admin`, `customer`.
* **Admin Login API:**
    * **Endpoint:** `/api/token`
    * **Method:** `POST`
    * **Request Body (form-urlencoded):** `username`, `password`
    * **Response (JSON):**
        ```json
        {
          "access_token": "eyJ...",
          "token_type": "bearer",
          "user_role": "admin"
        }
        ```
    * **Error Handling:** `401 Unauthorized` for incorrect credentials.
* **Token Usage:** Frontend will send JWT access tokens in the `Authorization: Bearer <token>` header for protected routes.
* **Protected Routes:** Endpoints marked as `(Admin only)` require a valid JWT for an `admin` user.

## Data Models (PostgreSQL Tables - Defined in `sql_schema.sql`)

* **`users` Table:**
    * `id`: UUID (Primary Key)
    * `username`: VARCHAR(50) (Unique, NOT NULL)
    * `hashed_password`: VARCHAR(255) (NOT NULL - Stores bcrypt hash)
    * `role`: VARCHAR(50) (NOT NULL, DEFAULT 'customer', e.g., 'admin', 'customer')
    * `created_at`: TIMESTAMPTZ
    * `updated_at`: TIMESTAMPTZ
* **`menu_items` Table:**
    * `id`: UUID (Primary Key)
    * `name`: VARCHAR(255) (NOT NULL)
    * `description`: TEXT (NULLABLE)
    * `price`: NUMERIC(10, 2) (NOT NULL)
    * `category`: VARCHAR(100) (NULLABLE)
    * `image_url`: TEXT (NULLABLE - URL to external image storage)
    * `is_available`: BOOLEAN (NOT NULL, DEFAULT TRUE)
    * `created_at`: TIMESTAMPTZ
    * `updated_at`: TIMESTAMPTZ
* **`reservations` Table:**
    * `id`: UUID (Primary Key)
    * `customer_name`: VARCHAR(255) (NOT NULL)
    * `customer_email`: VARCHAR(255) (NOT NULL)
    * `customer_phone`: VARCHAR(50) (NOT NULL)
    * `reservation_date`: DATE (NOT NULL)
    * `reservation_time`: TIME (NOT NULL)
    * `number_of_guests`: INTEGER (NOT NULL)
    * `status`: VARCHAR(50) (NOT NULL, DEFAULT 'Pending', CHECK IN ('Pending', 'Approved', 'Cancelled'))
    * `notes`: TEXT (NULLABLE)
    * `created_at`: TIMESTAMPTZ
    * `updated_at`: TIMESTAMPTZ

## API Endpoints (FastAPI)

* **Base URL:** `[YOUR_VERCEL_APP_URL]/api/` (e.g., `https://your-backend.vercel.app/api/`)

### Authentication

* `POST /api/token` (Login) - Public
* `POST /api/users` (Create User) - Admin only (for now)

### Menu Items

* `GET /api/menu` (Get all menu items) - Public
* `GET /api/menu/{menu_item_id}` (Get specific menu item) - Public
* `POST /api/menu` (Create menu item) - Admin only
* `PUT /api/menu/{menu_item_id}` (Update menu item) - Admin only
* `DELETE /api/menu/{menu_item_id}` (Delete menu item) - Admin only

### Reservations

* `POST /api/reservations` (Create reservation) - Public
* `GET /api/reservations` (Get all reservations, with optional `reservation_date` and `status_filter` query params) - Admin only
* `GET /api/reservations/today` (Get today's reservations) - Admin only
* `PUT /api/reservations/{reservation_id}` (Update reservation) - Admin only
* `DELETE /api/reservations/{reservation_id}` (Delete reservation) - Admin only

## Error Handling

* FastAPI will return standard HTTP status codes (400, 401, 403, 404, 500) with JSON `{"detail": "Error message"}`.
* Specific error codes might be included if defined in `models.py`.

## Deployment

* **PostgreSQL Setup:** The developer must provision a PostgreSQL database instance (e.g., via a cloud provider like Render, ElephantSQL, or AWS RDS).
* **Vercel Deployment:**
    1.  Create a new Vercel project linked to your backend Git repository.
    2.  In Vercel Project Settings, set up Environment Variables: `DATABASE_URL` and `SECRET_KEY` as "Secrets".
    3.  Vercel will detect `vercel.json` and deploy `main.py` as a serverless function.

**CRITICAL NOTE ON IMAGE STORAGE:**
This backend will **NOT** handle direct image file uploads. It will store only the `image_url` (a string) in the database. You *must* integrate a separate image storage service (e.g., AWS S3, Cloudinary, Imgur, or even remain with Supabase Storage as a standalone service if you configure it correctly) from your **frontend** to upload images. The frontend will then send the obtained public URL to this backend when creating/updating menu items.

