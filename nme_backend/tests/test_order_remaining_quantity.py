from sqlalchemy import text

from app.database import SessionLocal
from app.models import Order, Product, Trade, User


def test_remaining_quantity_is_set_for_new_orders_and_trade_model_works():
    with SessionLocal() as db:
        buyer = User(
            company_name='Acme',
            name='Buyer',
            email='remaining-buyer@example.com',
            password='secret',
            role='BUYER',
        )
        seller = User(
            company_name='Acme',
            name='Seller',
            email='remaining-seller@example.com',
            password='secret',
            role='SELLER',
        )
        db.add_all([buyer, seller])
        db.commit()
        db.refresh(buyer)
        db.refresh(seller)

        product = Product(
            seller_id=seller.id,
            metal='Copper',
            grade='C1100',
            quantity=100,
            unit='TON',
            price=2500,
            status='available',
        )
        db.add(product)
        db.commit()
        db.refresh(product)

        buy_order = Order(
            product_id=product.id,
            buyer_id=buyer.id,
            seller_id=None,
            quantity=100,
            price=2500,
            side='buy',
            status='PENDING',
            remaining_quantity=100,
        )
        sell_order = Order(
            product_id=product.id,
            buyer_id=None,
            seller_id=seller.id,
            quantity=30,
            price=2500,
            side='sell',
            status='PENDING',
            remaining_quantity=30,
        )
        db.add_all([buy_order, sell_order])
        db.commit()
        db.refresh(buy_order)
        db.refresh(sell_order)

        assert buy_order.remaining_quantity == 100
        assert sell_order.remaining_quantity == 30

        trade = Trade(
            product_id=product.id,
            buy_order_id=buy_order.id,
            sell_order_id=sell_order.id,
            quantity=10,
            price=2500,
        )
        db.add(trade)
        db.commit()
        db.refresh(trade)

        assert trade.quantity == 10
        assert trade.price == 2500
        assert trade.product_id == product.id

        table_exists = db.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
        ).scalar_one_or_none()
        assert table_exists == 'trades'
