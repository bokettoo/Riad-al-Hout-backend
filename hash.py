# First, activate your virtual environment if you're using one
# .venv\Scripts\activate  (on Windows)
# source .venv/bin/activate (on Linux/macOS)

# Then, open a Python interpreter:
# python

from passlib.context import CryptContext
import os

# This context needs to be the same as defined in your auth.py
# If your auth.py uses os.getenv for SECRET_KEY, don't worry about it here,
# we just need the hashing context.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

plain_password = "password"

hashed_password = pwd_context.hash(plain_password)

print("Plain Password:", plain_password)
print("Hashed Password:", hashed_password)
# Exit Python shell: exit()