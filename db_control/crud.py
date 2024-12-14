# backend/db_control/crud.py
# uname() error回避
import platform
print("platform", platform.uname())

import uuid #yoshiki追加

from sqlalchemy import create_engine, insert, delete, update, select
import sqlalchemy
from sqlalchemy.orm import sessionmaker
import json
import pandas as pd

from db_control.connect import engine
from db_control.mymodels import *

from contextlib import contextmanager #yoshiki追加
from db_control.connect import engine #yoshiki追加
from sqlalchemy.sql import text  # text をインポート#yoshiki追加

def myinsert(mymodel, values):
    # session構築
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        with session.begin():
            session.execute(insert(mymodel).values(values))
        return "inserted"
    except sqlalchemy.exc.IntegrityError as e:
        print(f"一意制約違反により、挿入に失敗しました: {e}")
        session.rollback()
        raise  # 詳細なエラーログを得るため例外を再スロー
    except Exception as e:
        print(f"不明なエラーにより、挿入に失敗しました: {e}")
        session.rollback()
        raise  # 他のエラーも再スローして追跡可能にする
 
# def myselect(mymodel, customer_id):
#     # session構築
#     Session = sessionmaker(bind=engine)
#     session = Session()
#     query = session.query(mymodel).filter(mymodel.customer_id == customer_id)
#     try:
#         # トランザクションを開始
#         with session.begin():
#             result = query.all()
#         # 結果をオブジェクトから辞書に変換し、リストに追加
#         result_dict_list = []
#         for customer_info in result:
#             result_dict_list.append({
#                 "customer_id": customer_info.customer_id,
#                 "customer_name": customer_info.customer_name,
#                 "age": customer_info.age,
#                 "gender": customer_info.gender
#             })
#         # リストをJSONに変換
#         result_json = json.dumps(result_dict_list, ensure_ascii=False)
#     except sqlalchemy.exc.IntegrityError:
#         print("一意制約違反により、挿入に失敗しました")

#     # セッションを閉じる
#     session.close()
#     return result_json

def myselectAll(mymodel):
    # session構築
    Session = sessionmaker(bind=engine)
    session = Session()
    query = select(mymodel)
    try:
        with session.begin():
            query = session.query(mymodel)
            df = pd.read_sql(query.statement, con=engine)
            result_json = df.to_json(orient='records', force_ascii=False)
    except Exception as e:
        print(f"エラー: {e}")
        result_json = None

    # セッションを閉じる
    session.close()
    return result_json

def myupdate(mymodel, values):
    # session構築
    Session = sessionmaker(bind=engine)
    session = Session()

    # デバッグ出力で values の内容を確認
    print("Debug: values =", values)

    customer_id = values.pop("customer_id")


 
    # query = "お見事！E0002の原因はこのクエリの実装ミスです。正しく実装しましょう"
    query = update(mymodel).where(mymodel.customer_id==customer_id).values(**values)
    try:
        # トランザクションを開始
        with session.begin():
            result = session.execute(query)
    except sqlalchemy.exc.IntegrityError:
        print("一意制約違反により、挿入に失敗しました")
        session.rollback()
    # セッションを閉じる
    session.close()
    return "put"

def mydelete(mymodel, customer_id):
    # session構築
    Session = sessionmaker(bind=engine)
    session = Session()
    query = delete(mymodel).where(mymodel.customer_id==customer_id)
    try:
        # トランザクションを開始
        with session.begin():
            result = session.execute(query)
    except sqlalchemy.exc.IntegrityError:
        print("一意制約違反により、挿入に失敗しました")
        session.rollback()
 
    # セッションを閉じる
    session.close()
    return customer_id + " is deleted"


# Yoshiki 追加データベースセッションの管理用コンテキストマネージャ
@contextmanager
def session_scope():
    """データベースセッションを管理するためのコンテキストマネージャ"""
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session  # セッションを呼び出し元に返す
        session.commit()  # トランザクションをコミット
    except Exception as e:
        session.rollback()  # エラー発生時にロールバック
        raise e  # エラーを再スロー
    finally:
        session.close()  # セッションを閉じる

def get_last_inserted_id(session, model):
    """指定されたモデルに対する最後の挿入 ID を取得"""
    try:
        # ID を取得（PostgreSQL や MySQL 用のコード）
        result = session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
        return result
    except Exception as e:
        print(f"エラー: 最後の挿入 ID を取得できませんでした: {e}")
        raise   
# Yoshiki終了

# ユーザー認証処理
def authenticate_user(user_id: int, password: str):
    """
    ユーザーIDとパスワードで認証を行う関数
    :param user_id: 認証対象のユーザーID
    :param password: 認証対象のパスワード
    :return: 認証結果（成功時はユーザー情報、失敗時はNone）
    """
    # セッションを構築
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # ユーザーをデータベースから取得
        query = select(Users).where(Users.id == user_id)
        user = session.execute(query).scalar_one_or_none()
        if not user:
            return {"success": False, "message": "ユーザーが見つかりません"}
        # パスワードが一致するか確認
        if user.password != password:
            return {"success": False, "message": "パスワードが間違っています"}
        # 認証成功時のレスポンス
        return {
            "success": True,
            "user": {
                "id": user.id,
                "name": user.name,
                "collection_start_at": user.collection_start_at,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            },
        }
    except Exception as e:
        print(f"エラー: {e}")
        return {"success": False, "message": "内部エラーが発生しました"}
    finally:
        session.close()  # セッションを必ず閉じる
