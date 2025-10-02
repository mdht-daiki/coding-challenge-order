# 目的

・インメモリ実装を、

**SQLite + SQLAlchemy** に置き換えるための、

スキーマと ORM 設計を提示。

・**後方互換**を意識して、

API I/F と振る舞いは

変えない前提。

---

# エンティティと関係

・Customer 1 — \* Order。

・Order 1 — \* OrderItem。

・Product 1 — \* OrderItem（参照）。

・削除は

**物理削除**（今回）。

将来論理削除に拡張可。

---

# テーブル定義（SQLite DDL）

```sql
-- 文字列PKはアプリ採番（例: C_xxx / P_xxx / O_xxx）
PRAGMA foreign_keys = ON;

CREATE TABLE customers (
  cust_id      TEXT PRIMARY KEY,
  name         TEXT NOT NULL,
  email        TEXT NOT NULL UNIQUE,
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE products (
  prod_id      TEXT PRIMARY KEY,
  name         TEXT NOT NULL,
  unit_price   INTEGER NOT NULL CHECK (unit_price >= 1),
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE orders (
  order_id     TEXT PRIMARY KEY,
  cust_id      TEXT NOT NULL,
  order_date   TEXT NOT NULL, -- 'YYYY-MM-DD'
  total_amount INTEGER NOT NULL CHECK (total_amount >= 0),
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (cust_id) REFERENCES customers(cust_id) ON DELETE RESTRICT
);

CREATE TABLE order_items (
  order_id     TEXT NOT NULL,
  line_no      INTEGER NOT NULL,
  prod_id      TEXT NOT NULL,
  qty          INTEGER NOT NULL CHECK (qty >= 1),
  unit_price   INTEGER NOT NULL CHECK (unit_price >= 1),
  line_amount  INTEGER NOT NULL CHECK (line_amount >= 0),
  PRIMARY KEY (order_id, line_no),
  FOREIGN KEY (order_id) REFERENCES orders(order_id)   ON DELETE CASCADE,
  FOREIGN KEY (prod_id)  REFERENCES products(prod_id) ON DELETE RESTRICT
);

-- 検索用インデックス
CREATE INDEX idx_orders_cust_date ON orders (cust_id, order_date DESC);
CREATE INDEX idx_order_items_prod ON order_items (prod_id);

```

---

# 重要制約と理由

・`email UNIQUE`

重複時は **409** を返す根拠。

・`CHECK (qty >= 1)` / `CHECK (unit_price >= 1)`

**400** バリデーションの最終防波堤。

・`orders.cust_id → customers.cust_id`

存在しない顧客に紐づく注文を禁止。

・`ON DELETE CASCADE`（order → items）

注文削除で明細も一括削除。

---

# SQLAlchemy ORM モデル（宣言的）

```python
# models.py
from __future__ import annotations
from datetime import date, datetime
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy import String, Integer, ForeignKey, CheckConstraint

class Base(DeclarativeBase):
    pass

class Customer(Base):
    __tablename__ = "customers"
    cust_id: Mapped[str] = mapped_column(String, primary_key=True)
    name:    Mapped[str] = mapped_column(String, nullable=False)
    email:   Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    updated_at: Mapped[str] = mapped_column(String, default=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    orders: Mapped[list["Order"]] = relationship(back_populates="customer")

class Product(Base):
    __tablename__ = "products"
    prod_id:    Mapped[str] = mapped_column(String, primary_key=True)
    name:       Mapped[str] = mapped_column(String, nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(String, default=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    updated_at: Mapped[str] = mapped_column(String, default=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    __table_args__ = (CheckConstraint("unit_price >= 1", name="ck_product_price_ge1"),)

class Order(Base):
    __tablename__ = "orders"
    order_id:     Mapped[str] = mapped_column(String, primary_key=True)
    cust_id:      Mapped[str] = mapped_column(ForeignKey("customers.cust_id"), nullable=False)
    order_date:   Mapped[str] = mapped_column(String, nullable=False)  # 'YYYY-MM-DD'
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at:   Mapped[str] = mapped_column(String, default=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    updated_at:   Mapped[str] = mapped_column(String, default=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    customer:     Mapped["Customer"] = relationship(back_populates="orders")
    items:        Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    __table_args__ = (CheckConstraint("total_amount >= 0", name="ck_order_total_ge0"),)

class OrderItem(Base):
    __tablename__ = "order_items"
    order_id:    Mapped[str] = mapped_column(ForeignKey("orders.order_id"), primary_key=True)
    line_no:     Mapped[int] = mapped_column(primary_key=True)
    prod_id:     Mapped[str] = mapped_column(ForeignKey("products.prod_id"), nullable=False)
    qty:         Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price:  Mapped[int] = mapped_column(Integer, nullable=False)
    line_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    order:       Mapped["Order"] = relationship(back_populates="items")
    product:     Mapped["Product"] = relationship()
    __table_args__ = (
        CheckConstraint("qty >= 1", name="ck_item_qty_ge1"),
        CheckConstraint("unit_price >= 1", name="ck_item_price_ge1"),
        CheckConstraint("line_amount >= 0", name="ck_item_amount_ge0"),
    )

```

---

# セッションとトランザクション

・アプリ層では

**ユースケース単位で 1 トランザクション**。

・注文登録は

Order と OrderItem を

**同一セッションで commit**。

・合計は

**アプリ側で計算**し、

`CHECK`で最低限を担保。

---

# 採番方針

・アプリで

`C_8hex` / `P_8hex` / `O_8hex` を生成。

・DB 側は

自然キーに依存しない。

---

# 代表的クエリ（SQL）

・注文検索（降順、ページング）。

```sql
SELECT order_id, order_date, total_amount
FROM orders
WHERE cust_id = :custId
  AND order_date BETWEEN :from AND :to
ORDER BY order_date DESC
LIMIT :size OFFSET (:page * :size);

```

・明細ロード（注文詳細用）。

```sql
SELECT line_no, prod_id, qty, unit_price, line_amount
FROM order_items
WHERE order_id = :orderId
ORDER BY line_no ASC;

```

---

# リポジトリ IF（擬似）

```python
# repository.py（抜粋）
from typing import Protocol, Sequence
from datetime import date

class CustomerRepo(Protocol):
    def get(self, cust_id: str): ...
    def get_by_email(self, email: str): ...
    def save(self, c: Customer): ...

class ProductRepo(Protocol):
    def get(self, prod_id: str): ...
    def save(self, p: Product): ...

class OrderRepo(Protocol):
    def get(self, order_id: str): ...
    def save(self, o: Order): ...
    def search(self, cust_id: str, from_date: date, to_date: date, page: int, size: int) -> tuple[int, Sequence[Order]]: ...

```

---

# 例外マッピング（DB→HTTP）

・`UNIQUE constraint failed: customers.email`

→ 409 Conflict（`EMAIL_DUP`）。

・`FOREIGN KEY constraint failed`

→ 404 Not Found（`CUST_NOT_FOUND` or `PROD_NOT_FOUND`）。

・`CHECK constraint failed`

→ 400 Bad Request（`BAD_QTY` `BAD_PRICE` など）。

・その他 DBError

→ 500 Internal Server Error（ログのみ詳細）。

---

# マイグレーション方針

・初期は

`Base.metadata.create_all(engine)`。

・将来 Alembic 導入：

`alembic init` → 自動生成 + 手修正。

・**後方互換**：

列追加は `NULL許容 + 既定値` を優先。

破壊的変更は

段階的マイグレーション（影響 PR を分離）。

---

# シーディング（任意）

・最小データ：

顧客 1、商品 2。

・テスト用ヘルパで

**毎テスト独立**（トランザクションロールバック

または in-memory DB 再作成）。

---

# パフォーマンス注意

・検索は

`idx_orders_cust_date` を必ず活用。

・明細は

**N+1 回避**：詳細取得 API では

`JOIN`または関連 eager load 検討。

・大量明細注文では

`executemany` を使うか、

ORM のバルクインサート検討。

---

# テスト観点（DB 版での追加）

・ユニーク制約が

**DB で本当に効く**か。

・FK 違反時に

**404 へ正しく変換**されるか。

・`ON DELETE CASCADE` の挙動確認。

・`CHECK` 違反が

**400 にマッピング**されるか。

---

# 導入手順（差し替えの流れ）

1. `models.py` と `repository_sqlalchemy.py` を追加。
2. `storage.py` の DI を

   **SQLAlchemy 実装**に切り替え。

3. `DATABASE_URL=sqlite:///./app.db` を設定。
4. `Base.metadata.create_all(engine)` を起動時に実行。
5. 既存 pytest を

   **全緑**に戻す（I/F は不変）。
