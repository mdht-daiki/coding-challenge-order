# 認可仕様（X-API-KEY）

## 目的

・すべての業務 API を

**共有型 API キー**で保護する。

・開発〜検証〜本番で

**キー差し替え**を容易にする。

---

## 対象範囲

・`/customers` `/products` `/orders` 系

**すべてのメソッド**。

・例外（無認可で許可）

`GET /health`

`GET /docs` `/openapi.json`（任意）

---

## インタフェース

・HTTP ヘッダ

`X-API-KEY: <key>`

・型

英数字 32〜64 桁。

例：`X-API-KEY: sk_live_2f6c...`

・同時有効キー

**2 本まで**（ローテーション用）。

`primary` と `secondary`。

---

## 判定とステータス

・ヘッダ欠落

→ **401 Unauthorized**

`{ "code": "NO_API_KEY", "message": "X-API-KEY is required" }`

・不一致

→ **403 Forbidden**

`{ "code": "INVALID_API_KEY", "message": "invalid api key" }`

・一致

→ ハンドラ実行。

※ エラーフォーマットは

既存の `{code, message}` に準拠。

---

## セキュリティ要件

・**タイミング攻撃対策**

キー比較は

**constant-time compare** を使用。

・**ログ**

平文キーは残さない。

先頭 4 文字＋ハッシュの一部のみ記録。

例：`key=sk_liv****** (sha1:ab12…)`

・**保存**

キーは環境変数または秘密管理。

`.env` に保存する場合も

**リポジトリに含めない**。

・**CORS**

本仕様はサーバ側判定。

CORS 設定とは独立。

---

## 運用（ローテーション）

1. `SECONDARY_KEY` に新キーを登録。
2. デプロイ。
3. クライアントを新キーへ切替。
4. `PRIMARY_KEY` を新キーに入替。
5. `SECONDARY_KEY` を空に戻す。

・**猶予期間**

最長 7 日（目安）。

---

## 実装場所（FastAPI）

・**依存（Depends）またはミドルウェア**で

ハンドラの前に検査。

・推奨構成

`auth.py` に `verify_api_key` を定義。

`APIRouter` 単位で `dependencies=[Depends(verify_api_key)]`。

・例外ルート（/health, /docs）は

`dependencies` を付与しない、

またはスキップ条件を入れる。

---

## 監査ログ

・出力項目

`time` `path` `method` `ip`

`api_key_hash`（平文不可）

`result`（ok / 401 / 403）

・個人情報と**混在させない**。

---

## 負荷・可用性

・キー照合は O(1)。

・レート制限は**拡張項目**（任意）。

`429 Too Many Requests` を併用可。

---

## テスト観点（pytest）

### 正常系

- T-OK-1
  `X-API-KEY=PRIMARY` で
  任意 API に 200。
- T-OK-2
  `X-API-KEY=SECONDARY` 設定時、
  同様に 200。

### 異常系

- T-ERR-1 欠落
  ヘッダなし → **401** / `NO_API_KEY`。
- T-ERR-2 不一致
  ランダムキー → **403** / `INVALID_API_KEY`。
- T-ERR-3 余計なヘッダのみ
  `Authorization: Bearer ...` だけ → **401**。

### 例外ルート

- T-FREE-1
  `/health` はヘッダ無しで **200**。

### ログ・副作用

- T-LOG-1
  エラー時レスポンスに**キー平文が含まれない**。

### パフォーマンス（任意）

- T-PERF-1
  100 リクエスト平均<数 ms（ローカル）。

## 環境変数（例）

```
PRIMARY_API_KEY=sk_live_abcd1234...
SECONDARY_API_KEY=

```
