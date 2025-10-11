from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import date
from typing import Tuple

from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.errors import BadRequest, Conflict
from ..db import models as m
from ..db.database import Base, get_engine, get_sessionmaker
from ..ports import CustomersRepo, OrdersRepo, ProductsRepo, UoW
from ..schemas import (
    CustomerWithId,
    OrderCreateResponse,
    OrderItemCreateResponse,
    ProductWithId,
)


class SqlAlchemyUoW(UoW, AbstractContextManager):
    def __init__(self):
        # 初回のみテーブル作成
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        self._Session = get_sessionmaker()
        self._session: Session | None = None
        # repos
        self.customers = _CustomersRepo(self)
        self.products = _ProductsRepo(self)
        self.orders = _OrdersRepo(self)

    # Session ライフサイクル
    @property
    def session(self) -> Session:
        if self._session is None:
            self._session = self._Session()
        return self._session

    def commit(self) -> None:
        if self._session:
            self._session.commit()

    def rollback(self) -> None:
        if self._session:
            self._session.rollback()

    def close(self) -> None:
        if self._session:
            self._session.close()
            self._session = None

    def __exit__(self, exc_type, exc, tb):
        if exc:
            self.rollback()
        self.close()


class _CustomersRepo(CustomersRepo):
    def __init__(self, uow: SqlAlchemyUoW):
        self.uow = uow

    def by_id(self, cust_id: str) -> CustomerWithId | None:
        s = select(m.Customer).where(m.Customer.cust_id == cust_id)
        row = self.uow.session.execute(s).scalar_one_or_none()
        if not row:
            return None
        return CustomerWithId(cust_id=cust_id, name=row.name, email=row.email)

    def exists_email(self, email: str) -> bool:
        c = (
            select(func.count())
            .select_from(m.Customer)
            .where(m.Customer.email == email)
        )
        return self.uow.session.execute(c).scalar_one() > 0

    def exists_id(self, cust_id: str) -> bool:
        c = (
            select(func.count())
            .select_from(m.Customer)
            .where(m.Customer.cust_id == cust_id)
        )
        return self.uow.session.execute(c).scalar_one() > 0

    def save(self, c: CustomerWithId) -> None:
        try:
            self.uow.session.execute(
                insert(m.Customer).values(cust_id=c.cust_id, name=c.name, email=c.email)
            )
        except IntegrityError as e:
            raise Conflict("EMAIL_DUP", "email already exists") from e


class _ProductsRepo(ProductsRepo):
    def __init__(self, uow: SqlAlchemyUoW):
        self.uow = uow

    def by_id(self, prod_id: str) -> ProductWithId | None:
        s = select(m.Product).where(m.Product.prod_id == prod_id)
        row = self.uow.session.execute(s).scalar_one_or_none()
        if not row:
            return None
        return ProductWithId(
            prod_id=row.prod_id, name=row.name, unit_price=row.unit_price
        )

    def exists_id(self, prod_id: str) -> bool:
        c = (
            select(func.count())
            .select_from(m.Product)
            .where(m.Product.prod_id == prod_id)
        )
        return self.uow.session.execute(c).scalar_one() > 0

    def by_name_norm_exists(self, name_norm: str) -> bool:
        c = (
            select(func.count())
            .select_from(m.Product)
            .where(m.Product.name_norm == name_norm)
        )
        return self.uow.session.execute(c).scalar_one() > 0

    def save(self, p: ProductWithId) -> None:
        try:
            self.uow.session.execute(
                insert(m.Product).values(
                    prod_id=p.prod_id,
                    name=p.name,
                    name_norm=p.name.strip().lower(),
                    unit_price=p.unit_price,
                )
            )
        except IntegrityError as e:
            raise Conflict("NAME_DUP", "product name duplicated") from e


class _OrdersRepo(OrdersRepo):
    def __init__(self, uow: SqlAlchemyUoW):
        self.uow = uow

    def by_id(self, order_id: str) -> OrderCreateResponse | None:
        s = select(m.Order).where(m.Order.order_id == order_id)
        row = self.uow.session.execute(s).scalar_one_or_none()
        if not row:
            return None
        # 明細
        s2 = (
            select(m.OrderItem)
            .where(m.OrderItem.order_id == order_id)
            .order_by(m.OrderItem.line_no)
        )
        lines = self.uow.session.execute(s2).scalars().all()
        items = [
            OrderItemCreateResponse(
                line_no=line.line_no,
                prod_id=line.prod_id,
                qty=line.qty,
                unit_price=line.unit_price,
                line_amount=line.line_amount,
            )
            for line in lines
        ]
        return OrderCreateResponse(
            order_id=row.order_id,
            order_date=row.order_date,
            total_amount=row.total_amount,
            items=items,
        )

    def exists_id(self, order_id: str) -> bool:
        c = (
            select(func.count())
            .select_from(m.Order)
            .where(m.Order.order_id == order_id)
        )
        return self.uow.session.execute(c).scalar_one() > 0

    def save(self, o: OrderCreateResponse, cust_id: str) -> None:
        try:
            self.uow.session.execute(
                insert(m.Order).values(
                    order_id=o.order_id,
                    cust_id=cust_id,
                    order_date=o.order_date,
                    total_amount=o.total_amount,
                )
            )
            for it in o.items:
                self.uow.session.execute(
                    insert(m.OrderItem).values(
                        order_id=o.order_id,
                        line_no=it.line_no,
                        prod_id=it.prod_id,
                        qty=it.qty,
                        unit_price=it.unit_price,
                        line_amount=it.line_amount,
                    )
                )
        except IntegrityError as e:
            raise BadRequest("DB_INTEGRITY", "integrity error") from e

    def search(
        self,
        cust_id: str | None,
        frm: date | None,
        to: date | None,
        page: int,
        size: int,
    ) -> Tuple[list[OrderCreateResponse], int]:
        q = select(m.Order)
        if cust_id:
            q = q.where(m.Order.cust_id == cust_id)
        if frm:
            q = q.where(m.Order.order_date >= frm)
        if to:
            q = q.where(m.Order.order_date <= to)
        q = q.order_by(m.Order.order_date.desc())

        total = self.uow.session.execute(
            select(func.count()).select_from(q.subquery())
        ).scalar_one()

        rows = (
            self.uow.session.execute(q.offset(page * size).limit(size)).scalars().all()
        )

        results: list[OrderCreateResponse] = [
            OrderCreateResponse(
                order_id=r.order_id,
                order_date=r.order_date,
                total_amount=r.total_amount,
                items=[],
            )
            for r in rows
        ]
        return results, total
