import os

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/smart_basket"
)
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# JWT Authentication & Household Security
JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY", "change_this_to_a_secure_random_secret_in_production"
)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
