# 目標（DoD）

・成功／失敗の

**観点網羅率 100%**（下の表）

・HTTP コードと

**エラーコードの一貫性**確認

・**降順・ページング**の

端（最初／最後／はみ出し）の確認

・**size 上限（100）**の取り扱い統一

・**テストデータ独立性**（各テストが自立して通る）

---

# フォルダと命名

tests/

test_customers_api.py

test_products_api.py

test_orders_post.py

test_orders_search.py

conftest.py（共通 fixture）

命名は

**何をテストするかが読める動詞＋対象**で。

---

# 共通 fixture（例）

・`client`：TestClient

・`cust_factory`：顧客作成ヘルパ

・`prod_factory`：商品作成ヘルパ

・`order_factory`：注文作成ヘルパ

・`freeze_today`：today 固定（並び順の安定化に役立つ）

---

# 観点一覧（ケース ID 付き）

## A. 顧客登録（POST /customers）

A-1 正常

新規 name ＋ email

→ 200 / custId 付与。

A-2 email 重複

同一 email を再登録

→ 409 / code=EMAIL_DUP。

A-3 入力不足

name なし、email あり

→ 400。

A-4 email 形式不正

`foo@bar` 以外の不正形式

→ 400。

A-5 name 境界

最小 1 文字、最大 100 文字、101 文字

→ 200 / 200 / 400。

A-6 余分項目

仕様外プロパティ同梱

→ 400 もしくは無視（**方針を固定**）。

A-7 冪等の扱い（参考）

同一 payload 再送で

**二重登録されないか**（今回 UUID なら**別注文**が妥当、顧客は 409）。

---

## B. 商品登録（POST /products）

B-1 正常

name ＋ unitPrice≥1

→ 200 / prodId。

B-2 単価 0

unitPrice=0

→ 400。

B-3 単価負

unitPrice=-1

→ 400。

B-4 name 境界

1 文字 / 100 文字 / 101 文字

→ 200 / 200 / 400。

---

## C. 注文登録（POST /orders）

C-1 正常

存在 custId、存在 prodId、qty≥1

→ 200 / lineAmount、totalAmount 正しい。

C-2 不在顧客

custId 未登録

→ 404 / code=CUST_NOT_FOUND。

C-3 不在商品

prodId 未登録

→ 404 / code=PROD_NOT_FOUND。

C-4 qty=0

→ 400 / code=BAD_QTY。

C-5 items 空配列

→ 400 / code=EMPTY_ITEMS。

C-6 複数明細の合計

2 商品混在

lineAmount の和 = totalAmount。

C-7 日付の体裁

orderDate が YYYY-MM-DD

（`date.today()` 固定の場合は

freeze して比較）。

C-8 大量明細（性能）

items 100 件

→ 200 / p95 200ms 以内（目安）。

---

## D. 注文検索（GET /orders）

D-1 正常（基本）

custId 指定、from≤to

→ 200 / list[], totalCount 整合。

D-2 降順

複数注文の orderDate 降順で

**安定している**。

D-3 ページング基本

page=0,size=1 で 1 件、

page=1,size=1 で次の 1 件。

D-4 ページング端

最終ページ、

範囲外 page で空配列＆totalCount 維持。

D-5 size 上限

size=101 の扱い

（**400 で弾く** or **100 に丸める**のどちらかに**統一**）。

D-6 期間反転

from>to

→ 400 / code=BAD_RANGE。

D-7 顧客不在

custId 未登録

→ 404。

D-8 件数 0

該当なし

→ 200 / list=[], totalCount=0。

---

# 実装レベルの補助観点

・**エラーフォーマット一貫性**

全 API で `{code, message}` になっているか。

・**Content-Type**

JSON 以外の POST は 415 or 400 にするか。

・**未定義パス／メソッド**

405/404 の既定挙動の確認。

・**タイムゾーン**

日付比較の基準（UTC かローカルか）。

今回は date のみなので固定で OK。

・**ログ**

エラー時にスタックトレースを

外へ漏らさない（JSON に含めない）。

# pytest の書き方（最小パターン）

・**parametrize** で境界／異常を圧縮。

・**factory fixture** で前提データを簡潔に。

・**id=…** を付けて可読性 UP。

（コード断片：説明用なので短く）

```python
import pytest

@pytest.mark.parametrize(
    "name,length,expected",
    [
        ("a", 1, 200),
        ("x"*100, 100, 200),
        ("x"*101, 101, 400),
    ],
    ids=["min", "max-ok", "overflow"],
)
def test_customer_name_boundary(client, name, length, expected):
    r = client.post("/customers", json={"name": name, "email": "b@example.com"})
    assert r.status_code == expected

```

---

# 失敗の“見える化”（診断のために）

・**レスポンス本文の断言**

`assert r.json()["code"] == "EMAIL_DUP"` のように

**code／message**を含めて断言。

・**順序検証**

`list` の `orderDate` を抜き出し、

`sorted(..., reverse=True)` と一致確認。

・**ページング検証**

`page=0` と `page=1` の `orderId` が

**重複していない**ことを確認。

---

# カバレッジの目安

・**ブランチ網羅**重視。

（行カバではなく**分岐**が通っているか）

・最小目安

ユースケースまわり 80%

ハンドラ／例外 80%

ストレージ 70%
