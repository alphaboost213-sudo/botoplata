from sqlalchemy import Column, Integer, String, Float, Boolean, BigInteger
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True)
    username = Column(String, nullable=True)
    balance = Column(Float, default=0.0)
    total_exchanges = Column(Integer, default=0)
    total_volume = Column(Float, default=0.0)
    accepted_tos = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    referrer_id = Column(BigInteger, nullable=True)
    is_verified = Column(Boolean, default=False)

class Direction(Base):
    __tablename__ = 'directions'
    id = Column(Integer, primary_key=True)
    valute_from = Column(String)
    type_from = Column(String)
    valute_to = Column(String)
    type_to = Column(String)
    rate = Column(Float)
    min_amount = Column(Float)
    max_amount = Column(Float)
    admin_requisites = Column(String)
    is_active = Column(Boolean, default=True)
    is_auto_rate = Column(Boolean, default=False)
    margin_percent = Column(Float, default=0.0)
    reserve = Column(Float, default=0.0)

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    direction_id = Column(Integer)
    amount_give = Column(Float)
    amount_receive = Column(Float)
    rate = Column(Float)
    user_requisites = Column(String)
    receipt_file_id = Column(String, nullable=True)
    status = Column(String, default="pending")

class BotSettings(Base):
    __tablename__ = 'bot_settings'
    id = Column(Integer, primary_key=True)
    base_currency = Column(String, default="RUB")

class Settings(Base):
    __tablename__ = 'settings'
    key = Column(String, primary_key=True)
    value = Column(Float, default=10.0)

class TraderCabOrder(Base):
    __tablename__ = 'tradercab_orders'
    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, nullable=False)
    merchant_external_id = Column(String, unique=True)
    tradercab_order_id = Column(String, unique=True)
    amount_rub = Column(Float, default=0.0)
    payment_method = Column(String)
    status = Column(String, default="PENDING")
    requisite_field = Column(String, nullable=True)
    requisite_holder = Column(String, nullable=True)
    requisite_bank = Column(String, nullable=True)
    created_at = Column(String, nullable=True)
    expires_at = Column(String, nullable=True)
    finalized_at = Column(String, nullable=True)
