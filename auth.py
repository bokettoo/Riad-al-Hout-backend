import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db # Import get_db to get a session
from models import UserInDB, TokenData, UserResponse # Assuming UserInDB exists

# --- Configuration ---
# Load environment variables
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 43200))  # 30 days

if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is not set for JWT.")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2PasswordBearer for token extraction from headers
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")

# --- Password Utilities ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# --- JWT Token Utilities ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- User Retrieval and Verification ---
def get_user(db: Session, username: str) -> Optional[UserInDB]:
    # In a real app, you might have an ORM model for User
    # For now, let's assume direct DB query or a simple User class
    from sqlalchemy import text # Using raw SQL for simplicity if no ORM model defined

    query = text("SELECT id, username, hashed_password, role, created_at, updated_at FROM users WHERE username = :username")
    result = db.execute(query, {"username": username}).fetchone()

    if result:
        # Map raw result to UserInDB Pydantic model
        user_data = {
            "id": result[0],
            "username": result[1],
            "hashed_password": result[2],
            "role": result[3],
            "created_at": result[4],
            "updated_at": result[5],
        }
        return UserInDB(**user_data)
    return None

def authenticate_user(db: Session, username: str, password: str) -> Optional[UserResponse]:
    user_in_db = get_user(db, username)
    if not user_in_db or not verify_password(password, user_in_db.hashed_password):
        return None
    # Return UserResponse (without hashed_password)
    return UserResponse(
        id=user_in_db.id,
        username=user_in_db.username,
        role=user_in_db.role,
        created_at=user_in_db.created_at,
        updated_at=user_in_db.updated_at
    )

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: Literal["admin", "customer"] = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception

    user = get_user(db, username=token_data.username) # Retrieve user from DB again
    if user is None or user.role != token_data.role: # Basic role check
        raise credentials_exception
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        created_at=user.created_at,
        updated_at=user.updated_at
    )

async def get_current_admin_user(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted for this user role"
        )
    return current_user