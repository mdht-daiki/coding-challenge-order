# MyProject

学習用の業務システム開発課題リポジトリ。

## 目的

ChatGPT により生成された詳細設計シートに基づき、勝手に仕様を変えずに実装・テストまで完了させる力を示す。

詳細設計シートは[こちら](docs/詳細設計.md)

## セットアップ

```bash
python -m venv venv
# Linux/macOS
source venv/bin/activate
export API_KEY=test-secret
export API_KEY_HASH_SECRET=hash-secret

# Windows
venv\Scripts\activate
set API_KEY=test-secret
set API_KEY_HASH_SECRET=hash-secret

pip install -r requirements.txt
```

## テスト

```bash
pytest -q
```
