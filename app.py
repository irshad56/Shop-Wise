from flask import Flask, request, jsonify, send_from_directory, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
import jwt
from functools import wraps

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# Token verification decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        try:
            token = token.split(' ')[1]  # Remove 'Bearer ' prefix
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
        except:
            return jsonify({'error': 'Token is invalid'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    barcode = db.Column(db.String(50), unique=True)
    image_url = db.Column(db.String(200))
    category = db.Column(db.String(50))
    features = db.relationship('ProductFeature', backref='product', lazy=True)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    product = db.relationship('Product', backref='cart_items')

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ProductFeature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    feature_name = db.Column(db.String(100), nullable=False)
    feature_value = db.Column(db.String(200), nullable=False)
    feature_unit = db.Column(db.String(50))
    feature_category = db.Column(db.String(50))  # e.g., 'Environmental', 'Quality', 'Price'
    importance_score = db.Column(db.Float, default=1.0)  # For weighted comparison

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Root route to serve the home page
@app.route('/')
def home():
    return send_from_directory('.', 'home.html')

# Dashboard route
@app.route('/dashboard')
def dashboard():
    return send_from_directory('.', 'dashboard.html')

# Serve other HTML files
@app.route('/<path:path>')
def serve_page(path):
    if path.endswith('.html'):
        return send_from_directory('.', path)
    return send_from_directory('.', path)

# Authentication routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    user = User(
        username=data['username'],
        email=data['email'],
        password_hash=generate_password_hash(data['password'])
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    
    if user and check_password_hash(user.password_hash, data['password']):
        login_user(user)
        token = jwt.encode(
            {'user_id': user.id},
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        return jsonify({
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        }), 200
    
    return jsonify({'error': 'Invalid email or password'}), 401

# Product routes
@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'price': p.price,
        'barcode': p.barcode,
        'image_url': p.image_url,
        'category': p.category
    } for p in products])

@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'barcode': product.barcode,
        'image_url': product.image_url,
        'category': product.category
    })

@app.route('/api/products/<int:product_id>/features', methods=['GET'])
@token_required
def get_product_features(current_user, product_id):
    product = Product.query.get_or_404(product_id)
    features = ProductFeature.query.filter_by(product_id=product_id).all()
    
    return jsonify([{
        'id': f.id,
        'feature_name': f.feature_name,
        'feature_value': f.feature_value,
        'feature_unit': f.feature_unit,
        'feature_category': f.feature_category,
        'importance_score': f.importance_score
    } for f in features])

# User profile route
@app.route('/api/user/profile', methods=['GET'])
@token_required
def get_user_profile(current_user):
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'created_at': current_user.created_at.isoformat()
    })

# Activity routes
@app.route('/api/activities', methods=['GET'])
@token_required
def get_activities(current_user):
    activities = Activity.query.filter_by(user_id=current_user.id).order_by(Activity.timestamp.desc()).limit(10).all()
    return jsonify([{
        'id': activity.id,
        'activity_type': activity.activity_type,
        'description': activity.description,
        'timestamp': activity.timestamp.isoformat()
    } for activity in activities])

@app.route('/api/activities', methods=['POST'])
@token_required
def add_activity(current_user):
    data = request.get_json()
    activity = Activity(
        user_id=current_user.id,
        activity_type=data['activity_type'],
        description=data.get('description', '')
    )
    db.session.add(activity)
    db.session.commit()
    return jsonify({'message': 'Activity recorded'}), 201

# Cart routes
@app.route('/api/debug/cart', methods=['GET'])
@token_required
def debug_cart(current_user):
    try:
        cart_items = Cart.query.filter_by(user_id=current_user.id).all()
        if not cart_items:
            return jsonify({
                'message': 'Cart is empty',
                'user_id': current_user.id,
                'items': []
            })
        
        return jsonify({
            'message': 'Cart contents retrieved successfully',
            'user_id': current_user.id,
            'items': [{
                'id': item.id,
                'product_id': item.product_id,
                'quantity': item.quantity,
                'added_at': item.added_at.isoformat(),
                'product': {
                    'id': item.product.id,
                    'name': item.product.name,
                    'price': item.product.price,
                    'category': item.product.category
                }
            } for item in cart_items]
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'user_id': current_user.id
        }), 500

@app.route('/api/cart', methods=['GET'])
@token_required
def get_cart(current_user):
    try:
        cart_items = Cart.query.filter_by(user_id=current_user.id).all()
        return jsonify([{
            'id': item.id,
            'product': {
                'id': item.product.id,
                'name': item.product.name,
                'price': item.product.price,
                'image_url': item.product.image_url,
                'description': item.product.description
            },
            'quantity': item.quantity,
            'added_at': item.added_at.isoformat()
        } for item in cart_items])
    except Exception as e:
        print("Error fetching cart:", str(e))  # Debug log
        return jsonify({'error': 'Failed to fetch cart contents'}), 500

@app.route('/api/cart', methods=['POST'])
@token_required
def add_to_cart(current_user):
    try:
        data = request.get_json()
        print("Received cart data:", data)  # Debug log
        print("Current user:", current_user.id)  # Debug log

        if not data or 'product_id' not in data:
            return jsonify({'error': 'Product ID is required'}), 400

        # Check if product exists
        product = Product.query.get(data['product_id'])
        if not product:
            return jsonify({'error': 'Product not found'}), 404

        # Check if item already in cart
        existing_item = Cart.query.filter_by(
            user_id=current_user.id,
            product_id=data['product_id']
        ).first()

        if existing_item:
            # Update quantity if item exists
            existing_item.quantity += data.get('quantity', 1)
            print(f"Updated existing cart item. New quantity: {existing_item.quantity}")  # Debug log
            cart_item = existing_item
        else:
            # Add new item to cart
            cart_item = Cart(
                user_id=current_user.id,
                product_id=data['product_id'],
                quantity=data.get('quantity', 1)
            )
            db.session.add(cart_item)
            print(f"Added new cart item for product {data['product_id']}")  # Debug log

        db.session.commit()

        # Return the updated cart item with product details
        return jsonify({
            'message': 'Item added to cart successfully',
            'cart_item': {
                'id': cart_item.id,
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'price': product.price,
                    'image_url': product.image_url,
                    'description': product.description
                },
                'quantity': cart_item.quantity,
                'added_at': cart_item.added_at.isoformat()
            }
        }), 201

    except Exception as e:
        print("Error adding to cart:", str(e))  # Debug log
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/cart/<int:item_id>', methods=['DELETE'])
@token_required
def remove_from_cart(current_user, item_id):
    try:
        print(f"Attempting to remove cart item {item_id} for user {current_user.id}")  # Debug log
        
        cart_item = Cart.query.filter_by(id=item_id, user_id=current_user.id).first()
        if not cart_item:
            print(f"Cart item {item_id} not found for user {current_user.id}")  # Debug log
            return jsonify({'error': 'Cart item not found'}), 404

        # Store product info for the response
        product_info = {
            'id': cart_item.product.id,
            'name': cart_item.product.name,
            'price': cart_item.product.price
        }

        db.session.delete(cart_item)
        db.session.commit()
        
        print(f"Successfully removed cart item {item_id}")  # Debug log
        return jsonify({
            'message': 'Item removed from cart successfully',
            'removed_item': {
                'id': item_id,
                'product': product_info
            }
        }), 200

    except Exception as e:
        print(f"Error removing cart item: {str(e)}")  # Debug log
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/cart/comparison', methods=['GET'])
@token_required
def get_cart_comparison(current_user):
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    
    comparison_data = []
    for item in cart_items:
        product = Product.query.get(item.product_id)
        features = ProductFeature.query.filter_by(product_id=product.id).all()
        
        comparison_data.append({
            'product_id': product.id,
            'product_name': product.name,
            'price': product.price,
            'features': [{
                'feature_name': f.feature_name,
                'feature_value': f.feature_value,
                'feature_unit': f.feature_unit,
                'feature_category': f.feature_category,
                'importance_score': f.importance_score
            } for f in features]
        })
    
    return jsonify(comparison_data)

# Barcode route
@app.route('/api/products/barcode/<barcode>', methods=['GET'])
def get_product_by_barcode(barcode):
    product = Product.query.filter_by(barcode=barcode).first()
    if product:
        return jsonify({
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'price': product.price,
            'barcode': product.barcode,
            'image_url': product.image_url,
            'category': product.category
        })
    return jsonify({'error': 'Product not found'}), 404

# Debug route to check products
@app.route('/api/debug/products', methods=['GET'])
def debug_products():
    products = Product.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'price': p.price,
        'barcode': p.barcode,
        'image_url': p.image_url,
        'category': p.category
    } for p in products])

@app.route('/api/products/search', methods=['GET'])
@token_required
def search_products(current_user):
    query = request.args.get('q', '').strip().lower()
    if not query:
        # If no query, return all products
        products = Product.query.all()
    else:
        # Search in product name and description
        products = Product.query.filter(
            db.or_(
                Product.name.ilike(f'%{query}%'),
                Product.description.ilike(f'%{query}%'),
                Product.category.ilike(f'%{query}%')
            )
        ).all()
    
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'price': p.price,
        'barcode': p.barcode,
        'image_url': p.image_url,
        'category': p.category,
        'status': p.status if hasattr(p, 'status') else None
    } for p in products])

# Add some sample data
def add_sample_features():
    # Sample features for different product categories
    sample_features = {
        'Electronics': [
            ('Energy Efficiency', 'A+', 'Rating', 'Environmental', 1.5),
            ('Battery Life', '8 hours', 'Hours', 'Quality', 1.2),
            ('Recycled Materials', '75%', 'Percentage', 'Environmental', 1.3),
            ('Warranty', '2 years', 'Years', 'Quality', 1.0),
            ('Carbon Footprint', '120 kg', 'CO2', 'Environmental', 1.4)
        ],
        'Clothing': [
            ('Organic Materials', '100%', 'Percentage', 'Environmental', 1.5),
            ('Fair Trade Certified', 'Yes', 'Boolean', 'Ethical', 1.4),
            ('Water Usage', 'Low', 'Rating', 'Environmental', 1.3),
            ('Durability', 'High', 'Rating', 'Quality', 1.2),
            ('Recyclable', 'Yes', 'Boolean', 'Environmental', 1.1)
        ],
        'Food': [
            ('Organic Certified', 'Yes', 'Boolean', 'Quality', 1.5),
            ('Local Sourcing', 'Within 50km', 'Distance', 'Environmental', 1.4),
            ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
            ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
            ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
        ]
    }
    
    # Add features to existing products
    products = Product.query.all()
    for product in products:
        # Determine category and get corresponding features
        category = product.category or 'Electronics'  # Default to Electronics if no category
        features = sample_features.get(category, sample_features['Electronics'])
        
        # Add features to product
        for feature_name, value, unit, category, importance in features:
            feature = ProductFeature(
                product_id=product.id,
                feature_name=feature_name,
                feature_value=value,
                feature_unit=unit,
                feature_category=category,
                importance_score=importance
            )
            db.session.add(feature)
    
    db.session.commit()

# Add sample products
def add_sample_products():
    # Sample products data
    sample_products = [
        {
            'name': 'Organic Cotton T-Shirt',
            'description': 'Made from 100% organic cotton, this t-shirt is both comfortable and sustainable.',
            'price': 29.99,
            'barcode': '1234567890',
            'image_url': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab',
            'category': 'Clothing',
            'features': [
                ('Organic Materials', '100%', 'Percentage', 'Environmental', 1.5),
                ('Fair Trade Certified', 'Yes', 'Boolean', 'Ethical', 1.4),
                ('Water Usage', 'Low', 'Rating', 'Environmental', 1.3),
                ('Durability', 'High', 'Rating', 'Quality', 1.2),
                ('Recyclable', 'Yes', 'Boolean', 'Environmental', 1.1)
            ]
        },
        {
            'name': 'Conventional Cotton T-Shirt',
            'description': 'Made from conventional cotton with synthetic dyes, this t-shirt is less expensive but has higher environmental impact.',
            'price': 14.99,
            'barcode': '1234567891',
            'image_url': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab',
            'category': 'Clothing',
            'features': [
                ('Organic Materials', '0%', 'Percentage', 'Environmental', 0.5),
                ('Fair Trade Certified', 'No', 'Boolean', 'Ethical', 0.4),
                ('Water Usage', 'High', 'Rating', 'Environmental', 0.3),
                ('Durability', 'Medium', 'Rating', 'Quality', 0.8),
                ('Recyclable', 'No', 'Boolean', 'Environmental', 0.2)
            ]
        },
        {
            'name': 'Energy-Efficient LED Bulb',
            'description': 'Long-lasting LED bulb that reduces energy consumption by up to 80%.',
            'price': 12.99,
            'barcode': '2345678901',
            'image_url': 'https://images.unsplash.com/photo-1507473885765-e6ed057f782c',
            'category': 'Electronics',
            'features': [
                ('Energy Efficiency', 'A+', 'Rating', 'Environmental', 1.5),
                ('Lifespan', '25000 hours', 'Hours', 'Quality', 1.3),
                ('Recycled Materials', '85%', 'Percentage', 'Environmental', 1.4),
                ('Warranty', '3 years', 'Years', 'Quality', 1.0),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.5)
            ]
        },
        {
            'name': 'Traditional Incandescent Bulb',
            'description': 'Standard incandescent bulb with high energy consumption and shorter lifespan.',
            'price': 2.99,
            'barcode': '2345678902',
            'image_url': 'https://images.unsplash.com/photo-1507473885765-e6ed057f782c',
            'category': 'Electronics',
            'features': [
                ('Energy Efficiency', 'D', 'Rating', 'Environmental', 0.3),
                ('Lifespan', '1000 hours', 'Hours', 'Quality', 0.5),
                ('Recycled Materials', '0%', 'Percentage', 'Environmental', 0.2),
                ('Warranty', '1 year', 'Years', 'Quality', 0.5),
                ('Carbon Footprint', 'High', 'Rating', 'Environmental', 0.3)
            ]
        },
        {
            'name': 'Bamboo Cutlery Set',
            'description': 'Eco-friendly bamboo cutlery set, perfect for sustainable dining.',
            'price': 19.99,
            'barcode': '3456789012',
            'image_url': 'https://images.unsplash.com/photo-1589994965851-a8f479c573a9',
            'category': 'Kitchen',
            'features': [
                ('Biodegradable', 'Yes', 'Boolean', 'Environmental', 1.5),
                ('Durability', 'Medium', 'Rating', 'Quality', 1.2),
                ('Recyclable', 'Yes', 'Boolean', 'Environmental', 1.3),
                ('Material', 'Bamboo', 'Type', 'Environmental', 1.4),
                ('Carbon Footprint', 'Very Low', 'Rating', 'Environmental', 1.5)
            ]
        },
        {
            'name': 'Plastic Cutlery Set',
            'description': 'Disposable plastic cutlery set, convenient but environmentally harmful.',
            'price': 4.99,
            'barcode': '3456789013',
            'image_url': 'https://images.unsplash.com/photo-1589994965851-a8f479c573a9',
            'category': 'Kitchen',
            'features': [
                ('Biodegradable', 'No', 'Boolean', 'Environmental', 0.2),
                ('Durability', 'Low', 'Rating', 'Quality', 0.5),
                ('Recyclable', 'No', 'Boolean', 'Environmental', 0.1),
                ('Material', 'Plastic', 'Type', 'Environmental', 0.2),
                ('Carbon Footprint', 'Very High', 'Rating', 'Environmental', 0.2)
            ]
        },
        {
            'name': 'Recycled Paper Notebook',
            'description': 'Notebook made from 100% recycled paper, perfect for eco-conscious note-taking.',
            'price': 8.99,
            'barcode': '4567890123',
            'image_url': 'https://images.unsplash.com/photo-1512428813834-c702c7702b78',
            'category': 'Stationery',
            'features': [
                ('Recycled Content', '100%', 'Percentage', 'Environmental', 1.5),
                ('Pages', '200', 'Count', 'Quality', 1.0),
                ('Recyclable', 'Yes', 'Boolean', 'Environmental', 1.3),
                ('Material', 'Recycled Paper', 'Type', 'Environmental', 1.4),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Virgin Paper Notebook',
            'description': 'Notebook made from virgin paper, contributing to deforestation.',
            'price': 5.99,
            'barcode': '4567890124',
            'image_url': 'https://images.unsplash.com/photo-1512428813834-c702c7702b78',
            'category': 'Stationery',
            'features': [
                ('Recycled Content', '0%', 'Percentage', 'Environmental', 0.2),
                ('Pages', '200', 'Count', 'Quality', 1.0),
                ('Recyclable', 'Yes', 'Boolean', 'Environmental', 0.8),
                ('Material', 'Virgin Paper', 'Type', 'Environmental', 0.3),
                ('Carbon Footprint', 'High', 'Rating', 'Environmental', 0.4)
            ]
        },
        {
            'name': 'Solar-Powered Power Bank',
            'description': 'Portable power bank that charges using solar energy, perfect for outdoor adventures.',
            'price': 49.99,
            'barcode': '5678901234',
            'image_url': 'https://images.unsplash.com/photo-1609599006353-e629aaabfeae',
            'category': 'Electronics',
            'features': [
                ('Energy Efficiency', 'A', 'Rating', 'Environmental', 1.5),
                ('Battery Capacity', '20000mAh', 'Capacity', 'Quality', 1.4),
                ('Recycled Materials', '70%', 'Percentage', 'Environmental', 1.3),
                ('Warranty', '2 years', 'Years', 'Quality', 1.0),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.4)
            ]
        },
        {
            'name': 'Conventional Power Bank',
            'description': 'Standard power bank that relies on grid electricity for charging.',
            'price': 29.99,
            'barcode': '5678901235',
            'image_url': 'https://images.unsplash.com/photo-1609599006353-e629aaabfeae',
            'category': 'Electronics',
            'features': [
                ('Energy Efficiency', 'C', 'Rating', 'Environmental', 0.6),
                ('Battery Capacity', '20000mAh', 'Capacity', 'Quality', 1.4),
                ('Recycled Materials', '0%', 'Percentage', 'Environmental', 0.3),
                ('Warranty', '1 year', 'Years', 'Quality', 0.8),
                ('Carbon Footprint', 'High', 'Rating', 'Environmental', 0.4)
            ]
        },
        {
            'name': 'Cornflakes - Kellogg\'s',
            'description': 'Crispy cornflakes, perfect for a quick breakfast.',
            'price': 5.99,
            'barcode': '7890123477',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Breakfast',
            'features': [
                ('Brand', 'Kellogg\'s', 'Type', 'Quality', 1.5),
                ('Weight', '500 g', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '6 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Oats - Saffola',
            'description': 'Healthy oats, perfect for a nutritious breakfast.',
            'price': 6.99,
            'barcode': '7890123478',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Breakfast',
            'features': [
                ('Brand', 'Saffola', 'Type', 'Quality', 1.5),
                ('Weight', '500 g', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '6 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Toor Dal - Tata Sampann',
            'description': 'High-quality toor dal, perfect for making dal dishes.',
            'price': 7.99,
            'barcode': '7890123479',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Pulses',
            'features': [
                ('Brand', 'Tata Sampann', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Moong Dal - Aashirvaad',
            'description': 'Fine moong dal, perfect for making dal dishes.',
            'price': 6.99,
            'barcode': '7890123480',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Pulses',
            'features': [
                ('Brand', 'Aashirvaad', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Chana Dal - Fortune',
            'description': 'High-quality chana dal, perfect for making dal dishes.',
            'price': 7.99,
            'barcode': '7890123481',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Pulses',
            'features': [
                ('Brand', 'Fortune', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Urad Dal - Daawat',
            'description': 'Fine urad dal, perfect for making dal dishes.',
            'price': 6.99,
            'barcode': '7890123482',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Pulses',
            'features': [
                ('Brand', 'Daawat', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Masoor Dal - India Gate',
            'description': 'High-quality masoor dal, perfect for making dal dishes.',
            'price': 7.99,
            'barcode': '7890123483',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Pulses',
            'features': [
                ('Brand', 'India Gate', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Green Gram - Tata Sampann',
            'description': 'High-quality green gram, perfect for making dal dishes.',
            'price': 6.99,
            'barcode': '7890123484',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Pulses',
            'features': [
                ('Brand', 'Tata Sampann', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Black Gram - Aashirvaad',
            'description': 'Fine black gram, perfect for making dal dishes.',
            'price': 7.99,
            'barcode': '7890123485',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Pulses',
            'features': [
                ('Brand', 'Aashirvaad', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Rajma - Fortune',
            'description': 'High-quality rajma, perfect for making dal dishes.',
            'price': 8.99,
            'barcode': '7890123486',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Pulses',
            'features': [
                ('Brand', 'Fortune', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Kabuli Chana - Daawat',
            'description': 'Fine kabuli chana, perfect for making dal dishes.',
            'price': 7.99,
            'barcode': '7890123487',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Pulses',
            'features': [
                ('Brand', 'Daawat', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Horse Gram - India Gate',
            'description': 'High-quality horse gram, perfect for making dal dishes.',
            'price': 6.99,
            'barcode': '7890123488',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Pulses',
            'features': [
                ('Brand', 'India Gate', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Salt - Tata Salt',
            'description': 'High-quality salt, perfect for cooking.',
            'price': 1.99,
            'barcode': '7890123489',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Spices',
            'features': [
                ('Brand', 'Tata Salt', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Sugar - Catch',
            'description': 'Fine sugar, perfect for sweetening dishes.',
            'price': 2.99,
            'barcode': '7890123490',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Spices',
            'features': [
                ('Brand', 'Catch', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Jaggery - Patanjali',
            'description': 'Natural jaggery, perfect for sweetening dishes.',
            'price': 3.99,
            'barcode': '7890123491',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Spices',
            'features': [
                ('Brand', 'Patanjali', 'Type', 'Quality', 1.5),
                ('Weight', '500 g', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Cooking Soda - Anil',
            'description': 'Baking soda, perfect for cooking and cleaning.',
            'price': 1.49,
            'barcode': '7890123492',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Spices',
            'features': [
                ('Brand', 'Anil', 'Type', 'Quality', 1.5),
                ('Weight', '100 g', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Baking Powder - Pillsbury',
            'description': 'Baking powder, perfect for making cakes and pastries.',
            'price': 1.99,
            'barcode': '7890123493',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Spices',
            'features': [
                ('Brand', 'Pillsbury', 'Type', 'Quality', 1.5),
                ('Weight', '100 g', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Milk – Amul',
            'description': 'Fresh milk from Amul, known for its quality and taste.',
            'price': 4.99,
            'barcode': '7890123494',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Amul', 'Type', 'Quality', 1.5),
                ('Fat Content', '3.5%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Milk – Vijaya Blue',
            'description': 'Vijaya milk with a cool blue flavor, a favorite among kids.',
            'price': 4.49,
            'barcode': '7890123495',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Vijaya', 'Type', 'Quality', 1.5),
                ('Fat Content', '2%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Milk – Vijaya Green',
            'description': 'Vijaya milk with a refreshing green flavor, perfect for a unique taste experience.',
            'price': 4.49,
            'barcode': '7890123496',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Vijaya', 'Type', 'Quality', 1.5),
                ('Fat Content', '2%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Milk – Heritage',
            'description': 'Heritage milk, known for its rich taste and quality.',
            'price': 4.99,
            'barcode': '7890123497',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Heritage', 'Type', 'Quality', 1.5),
                ('Fat Content', '3.5%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Milk – Nandini',
            'description': 'Nandini milk, a popular choice for its freshness and taste.',
            'price': 4.49,
            'barcode': '7890123498',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Nandini', 'Type', 'Quality', 1.5),
                ('Fat Content', '3.5%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Curd – Vijaya',
            'description': 'Vijaya curd, known for its creamy texture and taste.',
            'price': 3.99,
            'barcode': '7890123499',
            'image_url': 'https://images.unsplash.com/photo-1488477181946-6428a8481b19',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Vijaya', 'Type', 'Quality', 1.5),
                ('Fat Content', '3.5%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Curd – Heritage',
            'description': 'Heritage curd, a staple in many households.',
            'price': 3.99,
            'barcode': '7890123500',
            'image_url': 'https://images.unsplash.com/photo-1488477181946-6428a8481b19',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Heritage', 'Type', 'Quality', 1.5),
                ('Fat Content', '3.5%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Curd – Milky Mist',
            'description': 'Milky Mist curd, known for its smooth texture and taste.',
            'price': 4.49,
            'barcode': '7890123501',
            'image_url': 'https://images.unsplash.com/photo-1488477181946-6428a8481b19',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Milky Mist', 'Type', 'Quality', 1.5),
                ('Fat Content', '3.5%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Curd – Aavin',
            'description': 'Aavin curd, a popular choice for its quality and taste.',
            'price': 3.99,
            'barcode': '7890123502',
            'image_url': 'https://images.unsplash.com/photo-1488477181946-6428a8481b19',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Aavin', 'Type', 'Quality', 1.5),
                ('Fat Content', '3.5%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Curd – Nandini',
            'description': 'Nandini curd, known for its rich taste and quality.',
            'price': 3.99,
            'barcode': '7890123503',
            'image_url': 'https://images.unsplash.com/photo-1488477181946-6428a8481b19',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Nandini', 'Type', 'Quality', 1.5),
                ('Fat Content', '3.5%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Butter – Amul',
            'description': 'Amul butter, known for its rich taste and quality.',
            'price': 5.99,
            'barcode': '7890123504',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Amul', 'Type', 'Quality', 1.5),
                ('Fat Content', '80%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '30 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Butter – Mother Dairy',
            'description': 'Mother Dairy butter, a popular choice for its quality and taste.',
            'price': 5.49,
            'barcode': '7890123505',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Mother Dairy', 'Type', 'Quality', 1.5),
                ('Fat Content', '80%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '30 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Butter – Nandini',
            'description': 'Nandini butter, known for its rich taste and quality.',
            'price': 5.49,
            'barcode': '7890123506',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Nandini', 'Type', 'Quality', 1.5),
                ('Fat Content', '80%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '30 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Ghee – Patanjali',
            'description': 'Patanjali ghee, known for its rich taste and quality.',
            'price': 12.99,
            'barcode': '7890123507',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Patanjali', 'Type', 'Quality', 1.5),
                ('Fat Content', '100%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '180 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Ghee – Amul',
            'description': 'Amul ghee, a popular choice for its quality and taste.',
            'price': 12.99,
            'barcode': '7890123508',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Amul', 'Type', 'Quality', 1.5),
                ('Fat Content', '100%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '180 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Ghee – Aashirvaad Svasti',
            'description': 'Aashirvaad Svasti ghee, known for its rich taste and quality.',
            'price': 12.99,
            'barcode': '7890123509',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Aashirvaad Svasti', 'Type', 'Quality', 1.5),
                ('Fat Content', '100%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '180 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Paneer – Amul',
            'description': 'Amul paneer, known for its rich taste and quality.',
            'price': 8.99,
            'barcode': '7890123510',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Amul', 'Type', 'Quality', 1.5),
                ('Fat Content', '20%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Paneer – Milky Mist',
            'description': 'Milky Mist paneer, a popular choice for its quality and taste.',
            'price': 8.49,
            'barcode': '7890123511',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Milky Mist', 'Type', 'Quality', 1.5),
                ('Fat Content', '20%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Paneer – Britannia',
            'description': 'Britannia paneer, known for its rich taste and quality.',
            'price': 8.49,
            'barcode': '7890123512',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Britannia', 'Type', 'Quality', 1.5),
                ('Fat Content', '20%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Cheese – Amul',
            'description': 'Amul cheese, known for its rich taste and quality.',
            'price': 7.99,
            'barcode': '7890123513',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Amul', 'Type', 'Quality', 1.5),
                ('Fat Content', '25%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '30 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Cheese – Go Cheese',
            'description': 'Go Cheese, a popular choice for its quality and taste.',
            'price': 7.49,
            'barcode': '7890123514',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Go Cheese', 'Type', 'Quality', 1.5),
                ('Fat Content', '25%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '30 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Cheese – Mother Dairy',
            'description': 'Mother Dairy cheese, known for its rich taste and quality.',
            'price': 7.49,
            'barcode': '7890123515',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Mother Dairy', 'Type', 'Quality', 1.5),
                ('Fat Content', '25%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '30 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Buttermilk – Amul Masti',
            'description': 'Amul Masti buttermilk, known for its refreshing taste.',
            'price': 2.99,
            'barcode': '7890123516',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Amul Masti', 'Type', 'Quality', 1.5),
                ('Fat Content', '1%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Buttermilk – Heritage',
            'description': 'Heritage buttermilk, a popular choice for its refreshing taste.',
            'price': 2.99,
            'barcode': '7890123517',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Heritage', 'Type', 'Quality', 1.5),
                ('Fat Content', '1%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Buttermilk – Vijaya',
            'description': 'Vijaya buttermilk, known for its refreshing taste.',
            'price': 2.99,
            'barcode': '7890123518',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Vijaya', 'Type', 'Quality', 1.5),
                ('Fat Content', '1%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Lassi – Amul',
            'description': 'Amul lassi, known for its rich taste and quality.',
            'price': 3.99,
            'barcode': '7890123519',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Amul', 'Type', 'Quality', 1.5),
                ('Fat Content', '3.5%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Lassi – Mother Dairy Mango',
            'description': 'Mother Dairy Mango lassi, a popular choice for its refreshing taste.',
            'price': 3.99,
            'barcode': '7890123520',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Mother Dairy', 'Type', 'Quality', 1.5),
                ('Fat Content', '3.5%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Flavored Milk – Amul Kool',
            'description': 'Amul Kool flavored milk, known for its refreshing taste.',
            'price': 3.99,
            'barcode': '7890123521',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Amul Kool', 'Type', 'Quality', 1.5),
                ('Fat Content', '2%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Flavored Milk – Cavin\'s',
            'description': 'Cavin\'s flavored milk, a popular choice for its refreshing taste.',
            'price': 3.99,
            'barcode': '7890123522',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Cavin\'s', 'Type', 'Quality', 1.5),
                ('Fat Content', '2%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Flavored Milk – Aavin',
            'description': 'Aavin flavored milk, known for its refreshing taste.',
            'price': 3.99,
            'barcode': '7890123523',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Aavin', 'Type', 'Quality', 1.5),
                ('Fat Content', '2%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Yogurt – Epigamia',
            'description': 'Epigamia yogurt, known for its rich taste and quality.',
            'price': 4.99,
            'barcode': '7890123524',
            'image_url': 'https://images.unsplash.com/photo-1488477181946-6428a8481b19',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Epigamia', 'Type', 'Quality', 1.5),
                ('Fat Content', '3.5%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Yogurt – Nestle A+',
            'description': 'Nestle A+ yogurt, a popular choice for its quality and taste.',
            'price': 4.99,
            'barcode': '7890123525',
            'image_url': 'https://images.unsplash.com/photo-1488477181946-6428a8481b19',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Nestle A+', 'Type', 'Quality', 1.5),
                ('Fat Content', '3.5%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Cream – Amul Fresh Cream',
            'description': 'Amul Fresh Cream, known for its rich taste and quality.',
            'price': 5.99,
            'barcode': '7890123526',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Amul', 'Type', 'Quality', 1.5),
                ('Fat Content', '25%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '7 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Condensed Milk – Nestle Milkmaid',
            'description': 'Nestle Milkmaid condensed milk, a popular choice for its quality and taste.',
            'price': 3.99,
            'barcode': '7890123527',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Nestle Milkmaid', 'Type', 'Quality', 1.5),
                ('Fat Content', '8%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '365 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Milk Powder – Amulya',
            'description': 'Amulya milk powder, known for its rich taste and quality.',
            'price': 6.99,
            'barcode': '7890123528',
            'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b',
            'category': 'Dairy',
            'features': [
                ('Brand', 'Amulya', 'Type', 'Quality', 1.5),
                ('Fat Content', '26%', 'Percentage', 'Quality', 1.0),
                ('Shelf Life', '365 days', 'Days', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Basmati Rice – India Gate',
            'description': 'Premium quality basmati rice from India Gate, known for its long grains and aromatic flavor.',
            'price': 12.99,
            'barcode': '7890123529',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Grains',
            'features': [
                ('Brand', 'India Gate', 'Type', 'Quality', 1.5),
                ('Weight', '5 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Basmati Rice – Daawat',
            'description': 'Premium quality basmati rice from Daawat, known for its long grains and aromatic flavor.',
            'price': 11.99,
            'barcode': '7890123530',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Grains',
            'features': [
                ('Brand', 'Daawat', 'Type', 'Quality', 1.5),
                ('Weight', '5 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Sona Masoori Rice – 24 Mantra Organic',
            'description': 'Organic sona masoori rice from 24 Mantra, known for its quality and taste.',
            'price': 10.99,
            'barcode': '7890123531',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Grains',
            'features': [
                ('Brand', '24 Mantra Organic', 'Type', 'Quality', 1.5),
                ('Weight', '5 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Wheat Flour (Atta) – Aashirvaad',
            'description': 'Premium quality wheat flour from Aashirvaad, perfect for making rotis and other Indian breads.',
            'price': 8.99,
            'barcode': '7890123532',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Flour',
            'features': [
                ('Brand', 'Aashirvaad', 'Type', 'Quality', 1.5),
                ('Weight', '5 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '6 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Maida – Pillsbury',
            'description': 'Fine quality maida from Pillsbury, perfect for making cakes and pastries.',
            'price': 7.99,
            'barcode': '7890123533',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Flour',
            'features': [
                ('Brand', 'Pillsbury', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '6 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Ragi Flour – Manna',
            'description': 'Nutritious ragi flour from Manna, perfect for making healthy rotis and porridge.',
            'price': 9.99,
            'barcode': '7890123534',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Flour',
            'features': [
                ('Brand', 'Manna', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '6 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Poha – Anil',
            'description': 'Premium quality poha from Anil, perfect for making breakfast dishes.',
            'price': 5.99,
            'barcode': '7890123535',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Breakfast',
            'features': [
                ('Brand', 'Anil', 'Type', 'Quality', 1.5),
                ('Weight', '500 g', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '6 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Suji – MTR',
            'description': 'Fine quality suji from MTR, perfect for making upma and other dishes.',
            'price': 6.99,
            'barcode': '7890123536',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Breakfast',
            'features': [
                ('Brand', 'MTR', 'Type', 'Quality', 1.5),
                ('Weight', '500 g', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '6 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Toor Dal – Tata Sampann',
            'description': 'Premium quality toor dal from Tata Sampann, perfect for making dal dishes.',
            'price': 7.99,
            'barcode': '7890123537',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Pulses',
            'features': [
                ('Brand', 'Tata Sampann', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Moong Dal – Tata Sampann',
            'description': 'Premium quality moong dal from Tata Sampann, perfect for making dal dishes.',
            'price': 7.99,
            'barcode': '7890123538',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Pulses',
            'features': [
                ('Brand', 'Tata Sampann', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Chana Dal – 24 Mantra Organic',
            'description': 'Organic chana dal from 24 Mantra, perfect for making dal dishes.',
            'price': 8.99,
            'barcode': '7890123539',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Pulses',
            'features': [
                ('Brand', '24 Mantra Organic', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Urad Dal – Organic Tattva',
            'description': 'Organic urad dal from Organic Tattva, perfect for making dal dishes.',
            'price': 8.99,
            'barcode': '7890123540',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Pulses',
            'features': [
                ('Brand', 'Organic Tattva', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Masoor Dal – Patanjali',
            'description': 'Premium quality masoor dal from Patanjali, perfect for making dal dishes.',
            'price': 7.99,
            'barcode': '7890123541',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Pulses',
            'features': [
                ('Brand', 'Patanjali', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Rajma – Tata Sampann',
            'description': 'Premium quality rajma from Tata Sampann, perfect for making rajma dishes.',
            'price': 8.99,
            'barcode': '7890123542',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Pulses',
            'features': [
                ('Brand', 'Tata Sampann', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Kabuli Chana – 24 Mantra Organic',
            'description': 'Organic kabuli chana from 24 Mantra, perfect for making chana dishes.',
            'price': 8.99,
            'barcode': '7890123543',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Pulses',
            'features': [
                ('Brand', '24 Mantra Organic', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Salt – Tata Salt',
            'description': 'Premium quality iodized salt from Tata Salt.',
            'price': 1.99,
            'barcode': '7890123544',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Spices',
            'features': [
                ('Brand', 'Tata Salt', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '24 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Sugar – Dhampur',
            'description': 'Premium quality sugar from Dhampur.',
            'price': 2.99,
            'barcode': '7890123545',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Spices',
            'features': [
                ('Brand', 'Dhampur', 'Type', 'Quality', 1.5),
                ('Weight', '1 kg', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '24 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Jaggery – 24 Mantra Organic',
            'description': 'Organic jaggery from 24 Mantra, perfect for natural sweetening.',
            'price': 3.99,
            'barcode': '7890123546',
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c',
            'category': 'Spices',
            'features': [
                ('Brand', '24 Mantra Organic', 'Type', 'Quality', 1.5),
                ('Weight', '500 g', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Tea – Tata Tea Gold',
            'description': 'Premium quality tea from Tata Tea Gold, known for its rich taste and aroma.',
            'price': 4.99,
            'barcode': '7890123547',
            'image_url': 'https://images.unsplash.com/photo-1564890369478-c89ca6d9cde9',
            'category': 'Beverages',
            'features': [
                ('Brand', 'Tata Tea Gold', 'Type', 'Quality', 1.5),
                ('Weight', '250 g', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Tea – Brooke Bond Red Label',
            'description': 'Classic tea from Brooke Bond Red Label, perfect for daily consumption.',
            'price': 3.99,
            'barcode': '7890123548',
            'image_url': 'https://images.unsplash.com/photo-1564890369478-c89ca6d9cde9',
            'category': 'Beverages',
            'features': [
                ('Brand', 'Brooke Bond Red Label', 'Type', 'Quality', 1.5),
                ('Weight', '250 g', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Coffee – Nescafé',
            'description': 'Premium instant coffee from Nescafé, known for its rich taste and aroma.',
            'price': 5.99,
            'barcode': '7890123549',
            'image_url': 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085',
            'category': 'Beverages',
            'features': [
                ('Brand', 'Nescafé', 'Type', 'Quality', 1.5),
                ('Weight', '100 g', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Instant Coffee – Bru',
            'description': 'Classic instant coffee from Bru, perfect for daily consumption.',
            'price': 4.99,
            'barcode': '7890123550',
            'image_url': 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085',
            'category': 'Beverages',
            'features': [
                ('Brand', 'Bru', 'Type', 'Quality', 1.5),
                ('Weight', '100 g', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Green Tea – Lipton',
            'description': 'Premium green tea from Lipton, known for its health benefits.',
            'price': 3.99,
            'barcode': '7890123551',
            'image_url': 'https://images.unsplash.com/photo-1564890369478-c89ca6d9cde9',
            'category': 'Beverages',
            'features': [
                ('Brand', 'Lipton', 'Type', 'Quality', 1.5),
                ('Weight', '100 g', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Juice – Tropicana Mango',
            'description': 'Refreshing mango juice from Tropicana, made from real fruits.',
            'price': 2.99,
            'barcode': '7890123552',
            'image_url': 'https://images.unsplash.com/photo-1600271886742-f049cd451bba',
            'category': 'Beverages',
            'features': [
                ('Brand', 'Tropicana', 'Type', 'Quality', 1.5),
                ('Volume', '1 L', 'Volume', 'Quality', 1.0),
                ('Shelf Life', '6 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Juice – Real Apple',
            'description': 'Pure apple juice from Real, made from fresh apples.',
            'price': 2.99,
            'barcode': '7890123553',
            'image_url': 'https://images.unsplash.com/photo-1600271886742-f049cd451bba',
            'category': 'Beverages',
            'features': [
                ('Brand', 'Real', 'Type', 'Quality', 1.5),
                ('Volume', '1 L', 'Volume', 'Quality', 1.0),
                ('Shelf Life', '6 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Coconut Water – Paper Boat',
            'description': 'Natural coconut water from Paper Boat, refreshing and healthy.',
            'price': 1.99,
            'barcode': '7890123554',
            'image_url': 'https://images.unsplash.com/photo-1600271886742-f049cd451bba',
            'category': 'Beverages',
            'features': [
                ('Brand', 'Paper Boat', 'Type', 'Quality', 1.5),
                ('Volume', '250 ml', 'Volume', 'Quality', 1.0),
                ('Shelf Life', '6 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Cola – Coca-Cola',
            'description': 'Classic cola drink from Coca-Cola, refreshing and fizzy.',
            'price': 1.49,
            'barcode': '7890123555',
            'image_url': 'https://images.unsplash.com/photo-1600271886742-f049cd451bba',
            'category': 'Beverages',
            'features': [
                ('Brand', 'Coca-Cola', 'Type', 'Quality', 1.5),
                ('Volume', '300 ml', 'Volume', 'Quality', 1.0),
                ('Shelf Life', '6 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Lemonade – Sprite',
            'description': 'Refreshing lemonade from Sprite, perfect for hot days.',
            'price': 1.49,
            'barcode': '7890123556',
            'image_url': 'https://images.unsplash.com/photo-1600271886742-f049cd451bba',
            'category': 'Beverages',
            'features': [
                ('Brand', 'Sprite', 'Type', 'Quality', 1.5),
                ('Volume', '300 ml', 'Volume', 'Quality', 1.0),
                ('Shelf Life', '6 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Energy Drink – Red Bull',
            'description': 'Energy drink from Red Bull, provides instant energy boost.',
            'price': 2.99,
            'barcode': '7890123557',
            'image_url': 'https://images.unsplash.com/photo-1600271886742-f049cd451bba',
            'category': 'Beverages',
            'features': [
                ('Brand', 'Red Bull', 'Type', 'Quality', 1.5),
                ('Volume', '250 ml', 'Volume', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        },
        {
            'name': 'Glucose Drink – Glucon-D',
            'description': 'Energy drink from Glucon-D, provides instant energy and hydration.',
            'price': 1.99,
            'barcode': '7890123558',
            'image_url': 'https://images.unsplash.com/photo-1600271886742-f049cd451bba',
            'category': 'Beverages',
            'features': [
                ('Brand', 'Glucon-D', 'Type', 'Quality', 1.5),
                ('Weight', '200 g', 'Weight', 'Quality', 1.0),
                ('Shelf Life', '12 months', 'Months', 'Quality', 1.0),
                ('Packaging', 'Recyclable', 'Type', 'Environmental', 1.3),
                ('Carbon Footprint', 'Low', 'Rating', 'Environmental', 1.2)
            ]
        }
    ]

    # Add products to database
    for product_data in sample_products:
        # Check if product already exists
        existing_product = Product.query.filter_by(barcode=product_data['barcode']).first()
        if existing_product:
            continue

        # Create new product
        product = Product(
            name=product_data['name'],
            description=product_data['description'],
            price=product_data['price'],
            barcode=product_data['barcode'],
            image_url=product_data['image_url'],
            category=product_data['category']
        )
        db.session.add(product)
        db.session.flush()  # Get the product ID

        # Add features
        for feature_name, value, unit, category, importance in product_data['features']:
            feature = ProductFeature(
                product_id=product.id,
                feature_name=feature_name,
                feature_value=value,
                feature_unit=unit,
                feature_category=category,
                importance_score=importance
            )
            db.session.add(feature)

    db.session.commit()

# Recipe Model
class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    ingredients = db.Column(db.JSON, nullable=False)  # List of ingredients
    cooking_time = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    image_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'ingredients': self.ingredients,
            'cookingTime': self.cooking_time,
            'difficulty': self.difficulty,
            'image': self.image_url
        }

# Recipe routes
@app.route('/api/recipes', methods=['GET'])
@token_required
def get_recipes(current_user):
    try:
        recipes = Recipe.query.all()
        return jsonify({
            'status': 'success',
            'recipes': [recipe.to_dict() for recipe in recipes]
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/recipes/search', methods=['GET'])
@token_required
def search_recipes(current_user):
    try:
        query = request.args.get('query', '').strip()
        match_cart = request.args.get('matchCart', 'false').lower() == 'true'
        
        # Base query
        recipes_query = Recipe.query
        
        # If matching cart ingredients is requested
        if match_cart:
            # Get user's cart items
            cart_items = Cart.query.filter_by(user_id=current_user.id).all()
            if not cart_items:
                return jsonify({
                    'status': 'success',
                    'recipes': [],
                    'message': 'No items in cart to match recipes'
                })
            
            # Get product names from cart and clean them
            cart_products = []
            for item in cart_items:
                # Clean the product name by removing brand names and common words
                product_name = item.product.name.lower()
                # Remove brand names (e.g., "Tata Sampann", "Real", etc.)
                product_name = ' '.join([word for word in product_name.split() 
                                       if not any(brand in word.lower() for brand in 
                                                ['tata', 'sampann', 'real', 'conventional'])])
                cart_products.append(product_name)
            
            print("Cart products:", cart_products)  # Debug log
            
            # Filter recipes that have at least one ingredient matching cart items
            matching_recipes = []
            for recipe in recipes_query.all():
                recipe_ingredients = [ing.lower() for ing in recipe.ingredients]
                print(f"Recipe {recipe.name} ingredients:", recipe_ingredients)  # Debug log
                
                # Check if any cart product matches any recipe ingredient
                if any(any(cart_product in recipe_ingredient or recipe_ingredient in cart_product 
                         for recipe_ingredient in recipe_ingredients) 
                      for cart_product in cart_products):
                    matching_recipes.append(recipe)
            
            recipes = matching_recipes
        else:
            # Regular search
            if query:
                recipes = recipes_query.filter(
                    Recipe.name.ilike(f'%{query}%') |
                    Recipe.description.ilike(f'%{query}%')
                ).all()
            else:
                recipes = recipes_query.all()
        
        return jsonify({
            'status': 'success',
            'recipes': [recipe.to_dict() for recipe in recipes]
        })
    except Exception as e:
        print("Error in search_recipes:", str(e))  # Debug log
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Add sample recipes
def add_sample_recipes():
    sample_recipes = [
        {
            'name': 'Vegetable Pasta',
            'description': 'A healthy pasta dish with fresh vegetables',
            'ingredients': ['pasta', 'tomatoes', 'bell peppers', 'onions', 'garlic'],
            'cooking_time': '30 mins',
            'difficulty': 'Easy',
            'image_url': 'https://images.unsplash.com/photo-1563379926898-05f4575a45d8'
        },
        {
            'name': 'Chicken Curry',
            'description': 'Traditional Indian chicken curry with spices',
            'ingredients': ['chicken', 'onions', 'tomatoes', 'garlic', 'ginger', 'spices'],
            'cooking_time': '45 mins',
            'difficulty': 'Medium',
            'image_url': 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398'
        },
        {
            'name': 'Vegetable Stir Fry',
            'description': 'Quick and healthy stir-fried vegetables',
            'ingredients': ['broccoli', 'carrots', 'bell peppers', 'soy sauce', 'ginger'],
            'cooking_time': '20 mins',
            'difficulty': 'Easy',
            'image_url': 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd'
        }
    ]
    
    for recipe_data in sample_recipes:
        existing_recipe = Recipe.query.filter_by(name=recipe_data['name']).first()
        if not existing_recipe:
            recipe = Recipe(**recipe_data)
            db.session.add(recipe)
    
    db.session.commit()

# Call add_sample_recipes when initializing the app
with app.app_context():
    db.create_all()
    add_sample_products()
    add_sample_recipes()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 