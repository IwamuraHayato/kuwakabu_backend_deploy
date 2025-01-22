from dotenv import load_dotenv
import os

# .env.local ファイルを読み込む
load_dotenv('.env.local')

# 環境変数を出力して確認
print("AZURE_STORAGE_ACCOUNT_NAME:", os.getenv('AZURE_STORAGE_ACCOUNT_NAME'))
print("AZURE_STORAGE_ACCOUNT_KEY:", os.getenv('AZURE_STORAGE_ACCOUNT_KEY'))
print("AZURE_STORAGE_CONTAINER_NAME:", os.getenv('AZURE_STORAGE_CONTAINER_NAME'))
