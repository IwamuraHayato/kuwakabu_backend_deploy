# backend/db_control/connect.py
# uname() error回避
from dotenv import load_dotenv
import os
import platform
print(platform.uname())

load_dotenv()

from sqlalchemy import create_engine

# MySQL接続設定
# ここでMySQLの接続情報を指定
DB_USER = "tech0gen8student"          # MySQLのユーザー名
DB_PASSWORD = "5iTbVNuqQu8z16"      # MySQLのパスワード
DB_HOST = "tech0-gen-8-step3-rdb-16.mysql.database.azure.com" # MySQLのホスト (例: localhost または IP アドレス)
DB_PORT = "3306"                   # MySQLのポート (通常は3306)
DB_NAME = "kuwakabu_db"      # 接続するデータベース名

# SSL証明書のパス
SSL_CERT_PATH = os.getenv('SSL_CERT_PATH')
# SSL_CERT_PATH = "/Users/ymiki/Library/Mobile Documents/com~apple~CloudDocs/tech0/STEP3/STEP3-2/team/certificates/DigiCertGlobalRootCA.crt.pem"

# MySQL接続文字列を作成
mysql_url = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?ssl_ca={SSL_CERT_PATH}"
)


# デバッグ用のログ出力
print(f"MySQL connection URL: {mysql_url}")

# SQLAlchemyエンジンを作成
engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    echo=True,
    connect_args={
        "ssl": {
            "ca": SSL_CERT_PATH,  # SSL証明書のパスを指定
        }
    }
)
