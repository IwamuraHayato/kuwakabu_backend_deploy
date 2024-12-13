from flask import Flask, request, jsonify
from flask_cors import CORS
from db_control import crud, mymodels
from db_control.connect import engine
import json
import requests
import os
from datetime import datetime
import logging
# # import sqlite3
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, or_, and_
from sqlalchemy import text
from sqlalchemy.sql import func  # funcをインポート
import sqlalchemy  # sqlalchemy全体をインポート
from sqlalchemy import distinct

from sqlalchemy import text
from sqlalchemy.sql import func  # funcをインポート
import sqlalchemy  # sqlalchemy全体をインポート
from sqlalchemy import distinct


app = Flask(__name__)
# CORS(app)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}}) # 開発用：3000番ポートからのすべてのオリジンを許可

app.config['SECRET_KEY'] = os.urandom(24)

UPLOAD_FOLDER = './images/post_images/'

SessionLocal = sessionmaker(bind=engine)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# db_path = './db_control/CRM.db'

# トップページルート
# このルートはトップページにアクセスした際に呼び出され、簡単なテキストレスポンスを返します。
@app.route("/")
def index():
    return "<p>Flask top page!</p>"


@app.route("/user", methods=['POST'])
def create_user():
    values = request.get_json()
    print("Received values:", values)  # デバッグ用

    if not values.get("name"):
        return jsonify({"error": "Name is required"}), 400
    if not values.get("collection_start_at"):
        return jsonify({"error": "Collection start date is required"}), 400

    values["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    values["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        crud.myinsert(mymodels.Users, values)
    except Exception as e:
        print(f"Database insert failed: {e}")
        return jsonify({"error": f"Database insert failed: {str(e)}"}), 500

    return jsonify({"message": "User created successfully"}), 201

###############################
# 新規追加箇所: マップ検索用
###############################
@app.route('/map/posts', methods=['GET'])
def get_posts():
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    search = request.args.get('search', type=str)

    session = SessionLocal()

    # PostsとLocationをJOIN
    # SpeciesInfo, SpeciesをLEFT JOIN
    stmt = (
        select(mymodels.Posts, mymodels.Location, mymodels.Species.name)
        .join(mymodels.Location, mymodels.Posts.id == mymodels.Location.post_id)
        .join(mymodels.SpeciesInfo, mymodels.Posts.id == mymodels.SpeciesInfo.post_id, isouter=True)
        .join(mymodels.Species, mymodels.SpeciesInfo.species_id == mymodels.Species.id, isouter=True)
    )

    # searchパラメータが指定されている場合はLIKE検索で絞り込み
    if search:
        like_pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                mymodels.Location.name.like(like_pattern),
                mymodels.Location.prefecture.like(like_pattern),
                mymodels.Location.city.like(like_pattern),
                mymodels.Posts.description.like(like_pattern),
                mymodels.Species.name.like(like_pattern),
                mymodels.Location.name.like(like_pattern),
                mymodels.Location.prefecture.like(like_pattern),
                mymodels.Location.city.like(like_pattern),
                mymodels.Posts.description.like(like_pattern),
                mymodels.Species.name.like(like_pattern)
            )
        )
    # 投稿データを取得
    results = session.execute(stmt).all()

    # 最大のpost_idを取得
    if search:
        max_post_id = (
            session.query(mymodels.Posts.id)
            .join(mymodels.Location, mymodels.Posts.id == mymodels.Location.post_id)
            .filter(
                or_(
                    mymodels.Location.name.like(like_pattern),
                    mymodels.Location.prefecture.like(like_pattern),
                    mymodels.Location.city.like(like_pattern),
                    mymodels.Posts.description.like(like_pattern),
                    mymodels.Species.name.like(like_pattern),
                    mymodels.Location.name.like(like_pattern),
                    mymodels.Location.prefecture.like(like_pattern),
                    mymodels.Location.city.like(like_pattern),
                    mymodels.Posts.description.like(like_pattern),
                    mymodels.Species.name.like(like_pattern)
                )
            )
            .order_by(mymodels.Posts.id.desc())
            .first()
        )
    else:
        max_post_id = (
            session.query(mymodels.Posts.id)
            .order_by(mymodels.Posts.id.desc())
            .first()
        )
    # searchが指定されていない場合は、すべての投稿を返す（条件なし）
    # 緯度経度が指定されている場合でも、すべての投稿を返す（現在地検索の場合は中心を指定するだけ）

    results = session.execute(stmt).all()
    session.close()

    # post_idをキーとした辞書にまとめる
    posts_dict = {}
    for post, loc, species_name in results:
        if post.id not in posts_dict:
            posts_dict[post.id] = {
                "id": post.id,
                "user_id": post.user_id,
                "description": post.description,
                "collected_at": post.collected_at.isoformat() if post.collected_at else None,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "location_name": loc.name,
                "prefecture": loc.prefecture,
                "city": loc.city,
                "species_names": []
            }
        # species_nameがある場合のみ追加
        if species_name:
            posts_dict[post.id]["species_names"].append(species_name)

    # 辞書をリストに変換
    posts_json = list(posts_dict.values())
    return jsonify({
        "posts": posts_json,
        "max_post": max_post_id[0] if max_post_id else None
    })


@app.route('/map/post/<int:post_id>', methods=['GET'])
def get_post_details(post_id):
    session = SessionLocal()
    try:
        # 追加: images テーブルとの結合
        stmt = (
            select(
                mymodels.Posts, 
                mymodels.Location, 
                mymodels.Species.name, 
                mymodels.Users, 
                mymodels.Images.image_url  # 修正: 正しいカラム名に変更
            )
            .join(mymodels.Location, mymodels.Posts.id == mymodels.Location.post_id)
            .join(mymodels.SpeciesInfo, mymodels.Posts.id == mymodels.SpeciesInfo.post_id, isouter=True)
            .join(mymodels.Species, mymodels.SpeciesInfo.species_id == mymodels.Species.id, isouter=True)
            .join(mymodels.Users, mymodels.Posts.user_id == mymodels.Users.id, isouter=True)
            .join(mymodels.Images, and_(
                mymodels.Images.post_id == mymodels.Posts.id, 
                mymodels.Images.position == 1  # position=1 の画像
            ), isouter=True)  # isouter=True により、関連するレコードがなくてもエラーにならない
            .where(mymodels.Posts.id == post_id)
        )

        result = session.execute(stmt).all()

        # 結果がない場合
        if not result:
            return jsonify({"success": False, "message": "Post not found"}), 404

        # データの整形
        post, location, species_name, user, image_url = result[0]  # image_url が None でも対応可能
        response = {
            "id": post.id,
            "description": post.description,
            # "collected_at": post.collected_at.isoformat() if post.collected_at else None,
            "collected_at": post.collected_at.strftime("%Y-%m-%d") if post.collected_at else None,
            "location": {
                "name": location.name,
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
            "species_names": list(set([r[2] for r in result if r[2]])),  # 重複排除
            "user": {
                "name": user.name if user else "匿名",
                "icon": user.icon if user and user.icon else "/src/face-icon.svg",  # デフォルトアイコンを返す
            },
            "image_url": image_url if image_url else "/src/no-image-icon.svg"  # 画像がない場合は no-image画像 を返す
        }

        return jsonify(response)
    finally:
        session.close()


######### がたろー mypage  #########

@app.route('/mypage', methods=['GET'])
def get_user_posts():
    user_id = request.args.get('user_id', type=int)
    if user_id is None:
        return jsonify({'error': 'user_id is required'}), 400

    session = SessionLocal()

    try:
        # group_concat_max_len を設定
        session.execute(text("SET SESSION group_concat_max_len = 100000;"))

        # SQLAlchemy ORMでクエリを作成
        stmt = (
            select(
                mymodels.Posts.id,
                mymodels.Users.name.label("user_name"),
                mymodels.Location.name.label("location_name"),
                mymodels.Posts.collected_at,
                mymodels.Posts.description,
                mymodels.Users.icon.label("user_icon"),
                func.group_concat(func.coalesce(mymodels.Species.name, '不明').distinct()).label("species_name")
            )
            .join(mymodels.Users, mymodels.Posts.user_id == mymodels.Users.id)
            .join(mymodels.SpeciesInfo, mymodels.Posts.id == mymodels.SpeciesInfo.post_id)
            .join(mymodels.Species, mymodels.SpeciesInfo.species_id == mymodels.Species.id)
            .join(mymodels.Location, mymodels.Posts.id == mymodels.Location.post_id)
            .where(mymodels.Users.id == user_id)
            .group_by(
                mymodels.Posts.id,
                mymodels.Users.name,
                mymodels.Location.name,
                mymodels.Posts.collected_at,
                mymodels.Posts.description,
                mymodels.Users.icon
            )
        )


        rows = session.execute(stmt).fetchall()

        result = [
            {
                'id': row.id,
                'user_name': row.user_name,
                'location_name': row.location_name,
                'collected_at': row.collected_at.isoformat() if row.collected_at else None,
                'description': row.description,
                'user_icon': row.user_icon or '-',
                'species_name': row.species_name or '-'
            }
            for row in rows
        ]
        return jsonify(result)
    except sqlalchemy.exc.OperationalError as oe:
        print(f"Operational error: {oe}")
        return jsonify({'error': 'Database operational error'}), 500
    except Exception as e:
        print(f"Unhandled error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

@app.route('/post/<int:post_id>', methods=['GET'])
def get_post(post_id):
    session = SessionLocal()

    try:
        stmt = (
            select(
                mymodels.Posts.id,
                mymodels.Posts.description,
                mymodels.Posts.collected_at,
                mymodels.Users.name.label("user_name"), 
                mymodels.Users.icon.label("user_icon"),
                mymodels.Location.name.label("location_name"), 
                mymodels.Location.latitude,
                mymodels.Location.longitude,
                func.group_concat(distinct(mymodels.Species.name)).label("species_data"),
                func.group_concat(distinct(mymodels.Method.name)).label("methods"),
                mymodels.MethodInfo.method_other,
                func.group_concat(distinct(mymodels.Tree.name)).label("trees"),
                mymodels.TreeInfo.tree_other,
                mymodels.Environment.whether,
                mymodels.Environment.temperature,
                func.group_concat(distinct(mymodels.DangerousSpecies.name)).label("dangerous_species_names"),
                mymodels.DangerousSpeciesInfo.dangerous_species_other,
                func.group_concat(distinct(mymodels.Facility.name)).label("facilities"),
                mymodels.FacilityInfo.facility_other,
                mymodels.Environment.is_restricted_area,
                mymodels.Environment.free_memo,
            )
            .join(mymodels.Users, mymodels.Posts.user_id == mymodels.Users.id)
            .join(mymodels.Location, mymodels.Posts.id == mymodels.Location.post_id)
            .join(mymodels.SpeciesInfo, mymodels.Posts.id == mymodels.SpeciesInfo.post_id)
            .join(mymodels.Species, mymodels.SpeciesInfo.species_id == mymodels.Species.id)
            .join(mymodels.MethodInfo, mymodels.Posts.id == mymodels.MethodInfo.post_id)
            .join(mymodels.Method, mymodels.MethodInfo.method_id == mymodels.Method.id)
            .join(mymodels.TreeInfo, mymodels.Posts.id == mymodels.TreeInfo.post_id)
            .join(mymodels.Tree, mymodels.TreeInfo.tree_id == mymodels.Tree.id)
            .join(mymodels.Environment, mymodels.Posts.id == mymodels.Environment.post_id)
            .join(mymodels.DangerousSpeciesInfo, mymodels.Posts.id == mymodels.DangerousSpeciesInfo.post_id)
            .join(mymodels.DangerousSpecies, mymodels.DangerousSpeciesInfo.dangerous_species_id == mymodels.DangerousSpecies.id)
            .join(mymodels.FacilityInfo, mymodels.Posts.id == mymodels.FacilityInfo.post_id)
            .join(mymodels.Facility, mymodels.FacilityInfo.facility_id == mymodels.Facility.id)
            .where(mymodels.Posts.id == post_id)
            .group_by(
                mymodels.Posts.id,
                mymodels.Posts.description,
                mymodels.Posts.collected_at,
                mymodels.Users.name,
                mymodels.Users.icon,
                mymodels.Location.name,
                mymodels.Location.latitude,
                mymodels.Location.longitude,
                mymodels.MethodInfo.method_other,
                mymodels.TreeInfo.tree_other,
                mymodels.Environment.whether,
                mymodels.Environment.temperature,
                mymodels.DangerousSpeciesInfo.dangerous_species_other,
                mymodels.FacilityInfo.facility_other,
                mymodels.Environment.is_restricted_area,
                mymodels.Environment.free_memo
            )
        )

        post = session.execute(stmt).first()

        if not post:
            print(f"No post found with id: {post_id}")
            return jsonify({"success": False, "message": "Post not found"}), 404

        response = {
            "post_id": post.id,
            "description": post.description,
            "collected_at": post.collected_at.isoformat() if post.collected_at else None,
            "user_name": post.user_name,
            "user_icon": post.user_icon,
            "location_name": post.location_name,
            "latitude": post.latitude,
            "longitude": post.longitude,
            "species_data": post.species_data,
            "methods": post.methods,
            "method_other": post.method_other,
            "trees": post.trees,
            "tree_other": post.tree_other,
            "whether": post.whether,
            "temperature": post.temperature,
            "dangerous_species_names": post.dangerous_species_names,
            "dangerous_species_other": post.dangerous_species_other,
            "facilities": post.facilities,
            "facility_other": post.facility_other,
            "is_restricted_area": post.is_restricted_area,
            "free_memo": post.free_memo,
        }

        return jsonify(response)

    except Exception as e:
        print(f"Query failed: {e}")  # 明示的なエラー出力
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()
