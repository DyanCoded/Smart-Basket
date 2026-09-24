import os

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/smart_basket"
)
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
