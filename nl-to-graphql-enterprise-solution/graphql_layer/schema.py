"""GraphQL schema definition using Strawberry."""
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
import strawberry
from strawberry.types import Info


@strawberry.type
class Brand:
    id: int
    name: str
    country: Optional[str]
    founded_year: Optional[int]
    description: Optional[str]
    website: Optional[str]


@strawberry.type
class Category:
    id: int
    name: str
    description: Optional[str]


@strawberry.type
class Watch:
    id: int
    model_name: str
    sku: str
    brand_id: int
    category_id: int
    price: float
    cost: float
    description: Optional[str]
    case_material: Optional[str]
    movement_type: Optional[str]
    water_resistance: Optional[str]
    diameter_mm: Optional[float]
    release_date: Optional[date]
    is_limited_edition: bool
    limited_quantity: Optional[int]
    
    @strawberry.field
    def brand(self, info: Info) -> Optional[Brand]:
        from database import get_session
        from database.models import Brand as BrandModel
        session = get_session()
        brand = session.query(BrandModel).filter_by(id=self.brand_id).first()
        session.close()
        if brand:
            return Brand(
                id=brand.id,
                name=brand.name,
                country=brand.country,
                founded_year=brand.founded_year,
                description=brand.description,
                website=brand.website,
            )
        return None
    
    @strawberry.field
    def category(self, info: Info) -> Optional[Category]:
        from database import get_session
        from database.models import Category as CategoryModel
        session = get_session()
        category = session.query(CategoryModel).filter_by(id=self.category_id).first()
        session.close()
        if category:
            return Category(id=category.id, name=category.name, description=category.description)
        return None


@strawberry.type
class Customer:
    id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    postal_code: Optional[str]
    customer_since: datetime
    vip_status: bool
    total_lifetime_value: float


@strawberry.type
class OrderItem:
    id: int
    order_id: int
    watch_id: int
    quantity: int
    unit_price: float
    discount_percent: float
    subtotal: float
    
    @strawberry.field
    def watch(self, info: Info) -> Optional[Watch]:
        from database import get_session
        from database.models import Watch as WatchModel
        session = get_session()
        watch = session.query(WatchModel).filter_by(id=self.watch_id).first()
        session.close()
        if watch:
            return convert_watch_to_graphql(watch)
        return None


@strawberry.type
class Order:
    id: int
    order_number: str
    customer_id: int
    order_date: datetime
    status: str
    subtotal: float
    tax: float
    shipping: float
    total: float
    payment_method: Optional[str]
    shipping_address: Optional[str]
    notes: Optional[str]
    
    @strawberry.field
    def customer(self, info: Info) -> Optional[Customer]:
        from database import get_session
        from database.models import Customer as CustomerModel
        session = get_session()
        customer = session.query(CustomerModel).filter_by(id=self.customer_id).first()
        session.close()
        if customer:
            return convert_customer_to_graphql(customer)
        return None
    
    @strawberry.field
    def items(self, info: Info) -> List[OrderItem]:
        from database import get_session
        from database.models import OrderItem as OrderItemModel
        session = get_session()
        items = session.query(OrderItemModel).filter_by(order_id=self.id).all()
        session.close()
        return [convert_order_item_to_graphql(item) for item in items]


@strawberry.type
class Inventory:
    id: int
    watch_id: int
    quantity_in_stock: int
    quantity_reserved: int
    reorder_level: int
    warehouse_location: Optional[str]
    last_restocked: Optional[datetime]
    
    @strawberry.field
    def watch(self, info: Info) -> Optional[Watch]:
        from database import get_session
        from database.models import Watch as WatchModel
        session = get_session()
        watch = session.query(WatchModel).filter_by(id=self.watch_id).first()
        session.close()
        if watch:
            return convert_watch_to_graphql(watch)
        return None


@strawberry.type
class Supplier:
    id: int
    name: str
    contact_person: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    country: Optional[str]
    rating: Optional[float]
    payment_terms: Optional[str]


@strawberry.type
class RevenueByMonth:
    month: str
    revenue: float
    order_count: int


@strawberry.type
class TopSellingWatch:
    watch_id: int
    model_name: str
    brand_name: str
    total_quantity_sold: int
    total_revenue: float


@strawberry.type
class InventoryStatus:
    watch_id: int
    model_name: str
    brand_name: str
    quantity_in_stock: int
    quantity_reserved: int
    needs_reorder: bool


@strawberry.type
class OrderStatistics:
    total_orders: int
    total_revenue: float
    average_order_value: float
    min_order_value: float
    max_order_value: float
    total_items_sold: int


# Helper conversion functions
def convert_watch_to_graphql(watch) -> Watch:
    return Watch(
        id=watch.id,
        model_name=watch.model_name,
        sku=watch.sku,
        brand_id=watch.brand_id,
        category_id=watch.category_id,
        price=float(watch.price),
        cost=float(watch.cost),
        description=watch.description,
        case_material=watch.case_material,
        movement_type=watch.movement_type,
        water_resistance=watch.water_resistance,
        diameter_mm=watch.diameter_mm,
        release_date=watch.release_date,
        is_limited_edition=watch.is_limited_edition,
        limited_quantity=watch.limited_quantity,
    )


def convert_customer_to_graphql(customer) -> Customer:
    return Customer(
        id=customer.id,
        first_name=customer.first_name,
        last_name=customer.last_name,
        email=customer.email,
        phone=customer.phone,
        address=customer.address,
        city=customer.city,
        state=customer.state,
        country=customer.country,
        postal_code=customer.postal_code,
        customer_since=customer.customer_since,
        vip_status=customer.vip_status,
        total_lifetime_value=float(customer.total_lifetime_value),
    )


def convert_order_to_graphql(order) -> Order:
    return Order(
        id=order.id,
        order_number=order.order_number,
        customer_id=order.customer_id,
        order_date=order.order_date,
        status=order.status,
        subtotal=float(order.subtotal),
        tax=float(order.tax),
        shipping=float(order.shipping),
        total=float(order.total),
        payment_method=order.payment_method,
        shipping_address=order.shipping_address,
        notes=order.notes,
    )


def convert_order_item_to_graphql(item) -> OrderItem:
    return OrderItem(
        id=item.id,
        order_id=item.order_id,
        watch_id=item.watch_id,
        quantity=item.quantity,
        unit_price=float(item.unit_price),
        discount_percent=item.discount_percent,
        subtotal=float(item.subtotal),
    )


def convert_inventory_to_graphql(inventory) -> Inventory:
    return Inventory(
        id=inventory.id,
        watch_id=inventory.watch_id,
        quantity_in_stock=inventory.quantity_in_stock,
        quantity_reserved=inventory.quantity_reserved,
        reorder_level=inventory.reorder_level,
        warehouse_location=inventory.warehouse_location,
        last_restocked=inventory.last_restocked,
    )


@strawberry.type
class Query:
    @strawberry.field
    def brands(self, limit: Optional[int] = None) -> List[Brand]:
        from database import get_session
        from database.models import Brand as BrandModel
        session = get_session()
        query = session.query(BrandModel)
        if limit:
            query = query.limit(limit)
        brands = query.all()
        session.close()
        return [Brand(
            id=b.id, name=b.name, country=b.country, 
            founded_year=b.founded_year, description=b.description, website=b.website
        ) for b in brands]
    
    @strawberry.field
    def categories(self) -> List[Category]:
        from database import get_session
        from database.models import Category as CategoryModel
        session = get_session()
        categories = session.query(CategoryModel).all()
        session.close()
        return [Category(id=c.id, name=c.name, description=c.description) for c in categories]
    
    @strawberry.field
    def watches(
        self, 
        limit: Optional[int] = None,
        brand_id: Optional[int] = None,
        category_id: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> List[Watch]:
        from database import get_session
        from database.models import Watch as WatchModel
        session = get_session()
        query = session.query(WatchModel)
        
        if brand_id:
            query = query.filter(WatchModel.brand_id == brand_id)
        if category_id:
            query = query.filter(WatchModel.category_id == category_id)
        if min_price:
            query = query.filter(WatchModel.price >= min_price)
        if max_price:
            query = query.filter(WatchModel.price <= max_price)
        if limit:
            query = query.limit(limit)
        
        watches = query.all()
        session.close()
        return [convert_watch_to_graphql(w) for w in watches]
    
    @strawberry.field
    def watch(self, id: int) -> Optional[Watch]:
        from database import get_session
        from database.models import Watch as WatchModel
        session = get_session()
        watch = session.query(WatchModel).filter_by(id=id).first()
        session.close()
        return convert_watch_to_graphql(watch) if watch else None
    
    @strawberry.field
    def customers(
        self, 
        limit: Optional[int] = None,
        vip_only: Optional[bool] = False,
        min_lifetime_value: Optional[float] = None,
    ) -> List[Customer]:
        from database import get_session
        from database.models import Customer as CustomerModel
        session = get_session()
        query = session.query(CustomerModel)
        
        if vip_only:
            query = query.filter(CustomerModel.vip_status == True)
        if min_lifetime_value:
            query = query.filter(CustomerModel.total_lifetime_value >= min_lifetime_value)
        if limit:
            query = query.limit(limit)
        
        customers = query.all()
        session.close()
        return [convert_customer_to_graphql(c) for c in customers]
    
    @strawberry.field
    def orders(
        self,
        limit: Optional[int] = None,
        customer_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[Order]:
        from database import get_session
        from database.models import Order as OrderModel
        session = get_session()
        query = session.query(OrderModel)
        
        if customer_id:
            query = query.filter(OrderModel.customer_id == customer_id)
        if status:
            query = query.filter(OrderModel.status == status)
        
        query = query.order_by(OrderModel.order_date.desc())
        
        if limit:
            query = query.limit(limit)
        
        orders = query.all()
        session.close()
        return [convert_order_to_graphql(o) for o in orders]
    
    @strawberry.field
    def inventory(self, watch_id: Optional[int] = None) -> List[Inventory]:
        from database import get_session
        from database.models import Inventory as InventoryModel
        session = get_session()
        query = session.query(InventoryModel)
        
        if watch_id:
            query = query.filter(InventoryModel.watch_id == watch_id)
        
        inventories = query.all()
        session.close()
        return [convert_inventory_to_graphql(i) for i in inventories]
    
    @strawberry.field
    def top_selling_watches(self, limit: int = 10) -> List[TopSellingWatch]:
        from database import get_session
        from database.models import OrderItem, Watch, Brand
        from sqlalchemy import func
        
        session = get_session()
        results = (
            session.query(
                Watch.id,
                Watch.model_name,
                Brand.name.label("brand_name"),
                func.sum(OrderItem.quantity).label("total_quantity"),
                func.sum(OrderItem.subtotal).label("total_revenue"),
            )
            .join(OrderItem, Watch.id == OrderItem.watch_id)
            .join(Brand, Watch.brand_id == Brand.id)
            .group_by(Watch.id, Watch.model_name, Brand.name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(limit)
            .all()
        )
        session.close()
        
        return [
            TopSellingWatch(
                watch_id=r[0],
                model_name=r[1],
                brand_name=r[2],
                total_quantity_sold=r[3],
                total_revenue=float(r[4]),
            )
            for r in results
        ]
    
    @strawberry.field
    def revenue_by_month(self, months: int = 12) -> List[RevenueByMonth]:
        from database import get_session
        from database.models import Order
        from sqlalchemy import func, extract
        from datetime import datetime, timedelta
        
        session = get_session()
        cutoff_date = datetime.now() - timedelta(days=months * 30)
        
        results = (
            session.query(
                func.strftime("%Y-%m", Order.order_date).label("month"),
                func.sum(Order.total).label("revenue"),
                func.count(Order.id).label("order_count"),
            )
            .filter(Order.order_date >= cutoff_date)
            .filter(Order.status != "Cancelled")
            .group_by(func.strftime("%Y-%m", Order.order_date))
            .order_by(func.strftime("%Y-%m", Order.order_date))
            .all()
        )
        session.close()
        
        return [
            RevenueByMonth(month=r[0], revenue=float(r[1]), order_count=r[2])
            for r in results
        ]
    
    @strawberry.field
    def inventory_status(self, low_stock_only: bool = False) -> List[InventoryStatus]:
        from database import get_session
        from database.models import Inventory, Watch, Brand
        
        session = get_session()
        query = (
            session.query(Inventory, Watch, Brand)
            .join(Watch, Inventory.watch_id == Watch.id)
            .join(Brand, Watch.brand_id == Brand.id)
        )
        
        if low_stock_only:
            query = query.filter(Inventory.quantity_in_stock <= Inventory.reorder_level)
        
        results = query.all()
        session.close()
        
        return [
            InventoryStatus(
                watch_id=inv.watch_id,
                model_name=watch.model_name,
                brand_name=brand.name,
                quantity_in_stock=inv.quantity_in_stock,
                quantity_reserved=inv.quantity_reserved,
                needs_reorder=inv.quantity_in_stock <= inv.reorder_level,
            )
            for inv, watch, brand in results
        ]
    
    @strawberry.field
    def order_statistics(self, status: Optional[str] = None) -> OrderStatistics:
        from database import get_session
        from database.models import Order, OrderItem
        from sqlalchemy import func
        
        session = get_session()
        
        # Build base query
        query = session.query(Order)
        
        # Filter by status if provided (e.g., exclude "Cancelled")
        if status:
            query = query.filter(Order.status == status)
        else:
            # By default, exclude cancelled orders
            query = query.filter(Order.status != "Cancelled")
        
        # Get aggregate statistics
        stats = session.query(
            func.count(Order.id).label("total_orders"),
            func.sum(Order.total).label("total_revenue"),
            func.avg(Order.total).label("average_order_value"),
            func.min(Order.total).label("min_order_value"),
            func.max(Order.total).label("max_order_value"),
        ).filter(Order.status != "Cancelled" if not status else Order.status == status).first()
        
        # Get total items sold
        total_items = session.query(
            func.sum(OrderItem.quantity)
        ).join(Order).filter(
            Order.status != "Cancelled" if not status else Order.status == status
        ).scalar() or 0
        
        session.close()
        
        return OrderStatistics(
            total_orders=stats.total_orders or 0,
            total_revenue=float(stats.total_revenue or 0),
            average_order_value=float(stats.average_order_value or 0),
            min_order_value=float(stats.min_order_value or 0),
            max_order_value=float(stats.max_order_value or 0),
            total_items_sold=int(total_items),
        )


schema = strawberry.Schema(query=Query)
