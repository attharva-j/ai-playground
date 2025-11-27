"""Database models for the watch retail enterprise system."""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, 
    Text, Boolean, Numeric, Date
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Brand(Base):
    """Watch brand/manufacturer."""
    __tablename__ = "brands"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    country = Column(String(100))
    founded_year = Column(Integer)
    description = Column(Text)
    website = Column(String(255))
    
    watches = relationship("Watch", back_populates="brand")


class Category(Base):
    """Watch category (e.g., Luxury, Sport, Dress)."""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    
    watches = relationship("Watch", back_populates="category")


class Watch(Base):
    """Watch product model."""
    __tablename__ = "watches"
    
    id = Column(Integer, primary_key=True)
    model_name = Column(String(200), nullable=False)
    sku = Column(String(50), unique=True, nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    cost = Column(Numeric(10, 2), nullable=False)
    description = Column(Text)
    case_material = Column(String(100))
    movement_type = Column(String(100))  # Automatic, Quartz, Manual
    water_resistance = Column(String(50))
    diameter_mm = Column(Float)
    release_date = Column(Date)
    is_limited_edition = Column(Boolean, default=False)
    limited_quantity = Column(Integer)
    
    brand = relationship("Brand", back_populates="watches")
    category = relationship("Category", back_populates="watches")
    order_items = relationship("OrderItem", back_populates="watch")
    inventory = relationship("Inventory", back_populates="watch", uselist=False)


class Customer(Base):
    """Customer information."""
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20))
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    customer_since = Column(DateTime, default=datetime.utcnow)
    vip_status = Column(Boolean, default=False)
    total_lifetime_value = Column(Numeric(12, 2), default=0)
    
    orders = relationship("Order", back_populates="customer")


class Order(Base):
    """Customer order."""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    order_number = Column(String(50), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), nullable=False)  # Pending, Confirmed, Shipped, Delivered, Cancelled
    subtotal = Column(Numeric(12, 2), nullable=False)
    tax = Column(Numeric(12, 2), nullable=False)
    shipping = Column(Numeric(12, 2), nullable=False)
    total = Column(Numeric(12, 2), nullable=False)
    payment_method = Column(String(50))
    shipping_address = Column(Text)
    notes = Column(Text)
    
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    """Individual items in an order."""
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    watch_id = Column(Integer, ForeignKey("watches.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    discount_percent = Column(Float, default=0)
    subtotal = Column(Numeric(12, 2), nullable=False)
    
    order = relationship("Order", back_populates="items")
    watch = relationship("Watch", back_populates="order_items")


class Inventory(Base):
    """Inventory tracking for watches."""
    __tablename__ = "inventory"
    
    id = Column(Integer, primary_key=True)
    watch_id = Column(Integer, ForeignKey("watches.id"), nullable=False, unique=True)
    quantity_in_stock = Column(Integer, nullable=False, default=0)
    quantity_reserved = Column(Integer, default=0)
    reorder_level = Column(Integer, default=5)
    warehouse_location = Column(String(100))
    last_restocked = Column(DateTime)
    
    watch = relationship("Watch", back_populates="inventory")


class Supplier(Base):
    """Supplier information."""
    __tablename__ = "suppliers"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    contact_person = Column(String(100))
    email = Column(String(255))
    phone = Column(String(20))
    address = Column(Text)
    country = Column(String(100))
    rating = Column(Float)  # 1-5 rating
    payment_terms = Column(String(100))
