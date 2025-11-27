"""Seed the database with realistic enterprise data."""
import random
from datetime import datetime, timedelta
from decimal import Decimal
from faker import Faker
from .connection import init_db, get_session
from .models import Brand, Category, Watch, Customer, Order, OrderItem, Inventory, Supplier

fake = Faker()


def seed_database():
    """Seed the database with comprehensive mock data."""
    print("Initializing database...")
    init_db()
    
    session = get_session()
    
    try:
        # Check if data already exists
        if session.query(Brand).count() > 0:
            print("Database already seeded!")
            return
        
        print("Seeding brands...")
        brands_data = [
            {"name": "Rolex", "country": "Switzerland", "founded_year": 1905, "website": "rolex.com"},
            {"name": "Omega", "country": "Switzerland", "founded_year": 1848, "website": "omegawatches.com"},
            {"name": "Patek Philippe", "country": "Switzerland", "founded_year": 1839, "website": "patek.com"},
            {"name": "TAG Heuer", "country": "Switzerland", "founded_year": 1860, "website": "tagheuer.com"},
            {"name": "Breitling", "country": "Switzerland", "founded_year": 1884, "website": "breitling.com"},
            {"name": "Cartier", "country": "France", "founded_year": 1847, "website": "cartier.com"},
            {"name": "IWC", "country": "Switzerland", "founded_year": 1868, "website": "iwc.com"},
            {"name": "Audemars Piguet", "country": "Switzerland", "founded_year": 1875, "website": "audemarspiguet.com"},
        ]
        brands = [Brand(**data, description=f"Luxury watch manufacturer from {data['country']}") for data in brands_data]
        session.add_all(brands)
        session.commit()
        
        print("Seeding categories...")
        categories_data = [
            {"name": "Luxury", "description": "High-end luxury timepieces"},
            {"name": "Sport", "description": "Sporty and durable watches"},
            {"name": "Dress", "description": "Elegant dress watches"},
            {"name": "Diving", "description": "Professional diving watches"},
            {"name": "Aviation", "description": "Pilot and aviation watches"},
            {"name": "Chronograph", "description": "Watches with stopwatch functionality"},
        ]
        categories = [Category(**data) for data in categories_data]
        session.add_all(categories)
        session.commit()
        
        print("Seeding watches...")
        watches = []
        watch_models = [
            ("Submariner", "Diving"), ("Daytona", "Chronograph"), ("Datejust", "Dress"),
            ("Speedmaster", "Chronograph"), ("Seamaster", "Diving"), ("Constellation", "Luxury"),
            ("Nautilus", "Luxury"), ("Calatrava", "Dress"), ("Aquanaut", "Sport"),
            ("Carrera", "Chronograph"), ("Monaco", "Sport"), ("Aquaracer", "Diving"),
            ("Navitimer", "Aviation"), ("Superocean", "Diving"), ("Chronomat", "Chronograph"),
            ("Santos", "Luxury"), ("Tank", "Dress"), ("Ballon Bleu", "Luxury"),
            ("Portugieser", "Dress"), ("Pilot", "Aviation"), ("Aquatimer", "Diving"),
            ("Royal Oak", "Luxury"), ("Royal Oak Offshore", "Sport"), ("Code 11.59", "Luxury"),
        ]
        
        materials = ["Stainless Steel", "Gold", "Platinum", "Titanium", "Ceramic", "Rose Gold"]
        movements = ["Automatic", "Quartz", "Manual"]
        
        for i, (model, cat_name) in enumerate(watch_models):
            brand = random.choice(brands)
            category = next(c for c in categories if c.name == cat_name)
            base_price = random.randint(3000, 80000)
            
            watch = Watch(
                model_name=f"{brand.name} {model}",
                sku=f"WTH-{brand.name[:3].upper()}-{i+1000}",
                brand_id=brand.id,
                category_id=category.id,
                price=Decimal(base_price),
                cost=Decimal(base_price * 0.4),
                description=f"Premium {model} watch from {brand.name}",
                case_material=random.choice(materials),
                movement_type=random.choice(movements),
                water_resistance=f"{random.choice([50, 100, 200, 300])}m",
                diameter_mm=random.uniform(38, 45),
                release_date=fake.date_between(start_date="-5y", end_date="today"),
                is_limited_edition=random.random() < 0.2,
                limited_quantity=random.randint(100, 500) if random.random() < 0.2 else None,
            )
            watches.append(watch)
        
        session.add_all(watches)
        session.commit()
        
        print("Seeding inventory...")
        inventories = []
        for watch in watches:
            inventory = Inventory(
                watch_id=watch.id,
                quantity_in_stock=random.randint(0, 50),
                quantity_reserved=random.randint(0, 5),
                reorder_level=random.randint(3, 10),
                warehouse_location=f"WH-{random.choice(['A', 'B', 'C'])}-{random.randint(1, 20)}",
                last_restocked=fake.date_time_between(start_date="-90d", end_date="now"),
            )
            inventories.append(inventory)
        session.add_all(inventories)
        session.commit()
        
        print("Seeding customers...")
        customers = []
        for _ in range(200):
            total_value = Decimal(random.randint(0, 150000))
            customer = Customer(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.unique.email(),
                phone=fake.phone_number(),
                address=fake.street_address(),
                city=fake.city(),
                state=fake.state(),
                country=random.choice(["USA", "UK", "Germany", "France", "Japan", "UAE"]),
                postal_code=fake.postcode(),
                customer_since=fake.date_time_between(start_date="-3y", end_date="now"),
                vip_status=total_value > 50000,
                total_lifetime_value=total_value,
            )
            customers.append(customer)
        session.add_all(customers)
        session.commit()
        
        print("Seeding orders...")
        orders = []
        order_items = []
        statuses = ["Pending", "Confirmed", "Shipped", "Delivered", "Cancelled"]
        payment_methods = ["Credit Card", "Wire Transfer", "PayPal", "Crypto"]
        
        for i in range(500):
            customer = random.choice(customers)
            order_date = fake.date_time_between(start_date="-1y", end_date="now")
            status = random.choices(statuses, weights=[5, 10, 15, 65, 5])[0]
            
            # Create order items
            num_items = random.randint(1, 3)
            selected_watches = random.sample(watches, num_items)
            
            subtotal = Decimal(0)
            items = []
            for watch in selected_watches:
                quantity = 1
                discount = random.choice([0, 0, 0, 5, 10, 15])
                unit_price = watch.price
                item_subtotal = unit_price * quantity * (1 - Decimal(discount) / 100)
                subtotal += item_subtotal
                
                item = OrderItem(
                    watch_id=watch.id,
                    quantity=quantity,
                    unit_price=unit_price,
                    discount_percent=discount,
                    subtotal=item_subtotal,
                )
                items.append(item)
            
            tax = subtotal * Decimal("0.08")
            shipping = Decimal(random.choice([0, 25, 50]))
            total = subtotal + tax + shipping
            
            order = Order(
                order_number=f"ORD-{2024}-{i+10000}",
                customer_id=customer.id,
                order_date=order_date,
                status=status,
                subtotal=subtotal,
                tax=tax,
                shipping=shipping,
                total=total,
                payment_method=random.choice(payment_methods),
                shipping_address=f"{customer.address}, {customer.city}, {customer.state}",
            )
            orders.append(order)
            session.add(order)
            session.flush()
            
            for item in items:
                item.order_id = order.id
                order_items.append(item)
        
        session.add_all(order_items)
        session.commit()
        
        print("Seeding suppliers...")
        suppliers = []
        for _ in range(15):
            supplier = Supplier(
                name=fake.company(),
                contact_person=fake.name(),
                email=fake.company_email(),
                phone=fake.phone_number(),
                address=fake.address(),
                country=random.choice(["Switzerland", "Germany", "Italy", "Japan", "China"]),
                rating=round(random.uniform(3.5, 5.0), 1),
                payment_terms=random.choice(["Net 30", "Net 60", "Net 90", "COD"]),
            )
            suppliers.append(supplier)
        session.add_all(suppliers)
        session.commit()
        
        print(f"✅ Database seeded successfully!")
        print(f"   - {len(brands)} brands")
        print(f"   - {len(categories)} categories")
        print(f"   - {len(watches)} watches")
        print(f"   - {len(customers)} customers")
        print(f"   - {len(orders)} orders")
        print(f"   - {len(order_items)} order items")
        print(f"   - {len(suppliers)} suppliers")
        
    except Exception as e:
        session.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
