from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cust_id: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    prod_id: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    name_norm: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    unit_price: Mapped[int] = mapped_column(Integer)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    cust_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("customers.cust_id", ondelete="RESTRICT"), index=True
    )
    order_date: Mapped[date] = mapped_column(Date)
    total_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("orders.order_id", ondelete="CASCADE"), index=True
    )
    line_no: Mapped[int] = mapped_column(Integer)
    prod_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("products.prod_id", ondelete="RESTRICT")
    )
    qty: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[int] = mapped_column(Integer)
    line_amount: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("order_id", "line_no", name="uq_order_line"),)
