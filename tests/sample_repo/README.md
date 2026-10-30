# ShopStream E-Commerce Engine

ShopStream is a lightweight modular microservices-based e-commerce platform built with Python and JavaScript.

## Architecture & Modules
- **Authentication (`auth/`)**: User registration, credential authentication, JWT session generation, password hashing, and token revocation.
- **Products & Inventory (`products/`)**: Product catalog management, real-time stock reservation, and keyword-based product search.
- **Payment Processing (`payments/`)**: Stripe checkout session orchestration, webhook signature verification, discount coupons, and refund flows.
- **Notifications (`notifications/`)**: Automated customer emails (welcome, order receipts) and mobile push notification delivery.
- **API & Middleware (`api/`)**: Rate limiting, bearer token authentication middleware, and REST routes.
- **Utilities (`utils/`)**: Cryptographic hashing, token generation, and string/email validators.
- **Frontend (`frontend/`)**: Modern client-side fetch client, login forms, and Stripe checkout handlers.

## Getting Started
Configure environment variables in `config/settings.py` and run `api/routes.py`.
