# Flask Backend for E-commerce Application

This is the backend API for the e-commerce application, built with Flask and SQLAlchemy.

## Features

- User Authentication (Register/Login)
- Product Management
- Shopping Cart
- Activity Tracking
- Barcode Scanning Support
- RESTful API Endpoints

## Setup Instructions

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
- Windows:
```bash
venv\Scripts\activate
```
- Unix/MacOS:
```bash
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Initialize the database:
```bash
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

5. Run the application:
```bash
python app.py
```

The server will start at `http://localhost:5000`

## API Endpoints

### Authentication
- POST `/api/register` - Register a new user
- POST `/api/login` - Login user

### Products
- GET `/api/products` - Get all products
- GET `/api/products/<id>` - Get specific product
- GET `/api/products/barcode/<barcode>` - Get product by barcode

### Cart
- GET `/api/cart` - Get user's cart
- POST `/api/cart` - Add item to cart

### Activities
- GET `/api/activities` - Get user's activities
- POST `/api/activities` - Record new activity

## Database Models

- User: Stores user information
- Product: Stores product details
- Cart: Manages shopping cart items
- Activity: Tracks user activities

## Security

- Passwords are hashed using Werkzeug's security functions
- JWT tokens are used for authentication
- CORS is enabled for frontend integration 