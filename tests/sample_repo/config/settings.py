"""Application settings and runtime configuration for ShopStream."""

import os

APP_NAME = "ShopStream"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
SERVER_PORT = int(os.getenv("PORT", "5000"))
DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///shopstream.db")

# Security and Auth
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-shopstream-key")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Payment Gateway
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY", "pk_test_shopstream123")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_shopstream456")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_test789")

# Email & Notifications
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.shopstream.internal")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SUPPORT_EMAIL = "support@shopstream.io"
