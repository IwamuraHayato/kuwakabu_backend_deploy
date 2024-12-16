from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from db_control import crud, mymodels
from db_control.crud import authenticate_user, get_last_inserted_id
from db_control.connect import engine
import json
import requests
import os
from datetime import datetime
import logging
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, or_, and_, text, distinct, func, cast, insert
from sqlalchemy.types import String
import uuid

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = os.urandom(24)

POST_UPLOAD_FOLDER = 'post_images/'
DEFAULT_ICON_PATH = "icon_images/face-icon.svg"  # デフォルトアイコンのパス
DEFAULT_POST_IMAGE_PATH = 'post_images/no-image-icon.svg'  # デフォルト採集記録画像のパス

BASE_IMAGES_DIR = os.path.join(os.getcwd(), "images") # 画像フォルダのベースディレクトリ


SessionLocal = sessionmaker(bind=engine)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# db_path = './db_control/CRM.db'

# トップページルート
# このルートはトップページにアクセスした際に呼び出され、簡単なテキストレスポンスを返します。
@app.route("/")
def index():
    return "<p>Flask top page!</p>"

@app.route('/static/images/<path:filename>')
def serve_static_images(filename):
    """
    指定された画像ファイルを返すエンドポイント。
    ファイルが存在しない場合はデフォルト画像を返す。
    """
    requested_path = os.path.join(BASE_IMAGES_DIR, filename)
    if os.path.isfile(requested_path):
        return send_from_directory(BASE_IMAGES_DIR, filename)
    else:
        # ファイルが存在しない場合、デフォルト画像を返す
        if "icon_images" in filename:
            return send_from_directory(BASE_IMAGES_DIR, DEFAULT_ICON_PATH)
        elif "post_images" in filename:
            return send_from_directory(BASE_IMAGES_DIR, DEFAULT_POST_IMAGE_PATH)
        abort(404)

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
# ユーザー照会
###############################
@app.route("/authenticate", methods=["POST"])
def authenticate():
    # リクエストボディの取得
    data = request.json

    # 必要なフィールドを取得
    user_id = data.get("id")
    password = data.get("password")

    # 入力バリデーション
    if not user_id or not password:
        return jsonify({"success": False, "message": "IDとパスワードを入力してください"}), 400

    # 認証関数の呼び出し
    result = authenticate_user(user_id, password)

    # 結果を返却
    if result["success"]:
        return jsonify(result), 200  # 認証成功
    else:
        return jsonify(result), 401  # 認証失敗

###############################
# マップ検索用
###############################
@app.route('/map/posts', methods=['GET'])
def get_posts():
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    search = request.args.get('search', type=str)

    session = SessionLocal()

    try:
        # PostsとLocationをJOIN
        # SpeciesInfo, SpeciesをLEFT JOIN
        stmt = (
            select(mymodels.Posts, mymodels.Location, mymodels.Species.name)
            .join(mymodels.Location, mymodels.Posts.id == mymodels.Location.post_id)
            .join(mymodels.SpeciesInfo, mymodels.Posts.id == mymodels.SpeciesInfo.post_id, isouter=True)
            .join(mymodels.Species, mymodels.SpeciesInfo.species_id == mymodels.Species.id, isouter=True)
        )

        # searchパラメータが指定されている場合
        if search:
            search_terms = search.split()  # スペースで単語を分割
            conditions = []  # 条件を格納するリスト

            # 各単語で検索条件を作成
            for term in search_terms:
                like_pattern = f"%{term}%"
                conditions.append(
                    or_(
                        mymodels.Location.name.like(like_pattern),
                        mymodels.Location.prefecture.like(like_pattern),
                        mymodels.Location.city.like(like_pattern),
                        mymodels.Posts.description.like(like_pattern),
                        mymodels.Species.name.like(like_pattern)
                    )
                )

            # AND条件で全ての単語を満たすようにフィルタリング
            stmt = stmt.where(and_(*conditions))

        # 投稿データを取得
        results = session.execute(stmt).all()

        # 最大のpost_idを取得
        if search:
            max_post_id_query = (
                session.query(mymodels.Posts.id)
                .join(mymodels.Location, mymodels.Posts.id == mymodels.Location.post_id)
            )
            # 同じAND条件でフィルタリング
            for condition in conditions:
                max_post_id_query = max_post_id_query.filter(condition)
            max_post_id = max_post_id_query.order_by(mymodels.Posts.id.desc()).first()
        else:
            max_post_id = (
                session.query(mymodels.Posts.id)
                .order_by(mymodels.Posts.id.desc())
                .first()
            )

        # 検索結果が空の場合の処理
        if not results:
            return jsonify({
                "posts": [],
                "max_post": None,
                "message": "検索結果がありませんでした。"
            }), 200

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

    except Exception as e:
        print(f"Error fetching posts: {e}")
        return jsonify({"error": "データの取得中にエラーが発生しました"}), 500
    finally:
        session.close()


###############################
# マップ吹き出し用
###############################
@app.route('/map/post/<int:post_id>', methods=['GET'])
def get_post_details(post_id):
    session = SessionLocal()
    try:
        stmt = (
            select(
                mymodels.Posts,
                mymodels.Location,
                mymodels.Species.name,
                mymodels.Users,
                mymodels.Images.image_url
            )
            .join(mymodels.Location, mymodels.Posts.id == mymodels.Location.post_id)
            .join(mymodels.SpeciesInfo, mymodels.Posts.id == mymodels.SpeciesInfo.post_id, isouter=True)
            .join(mymodels.Species, mymodels.SpeciesInfo.species_id == mymodels.Species.id, isouter=True)
            .join(mymodels.Users, mymodels.Posts.user_id == mymodels.Users.id, isouter=True)
            .join(mymodels.Images, and_(
                mymodels.Images.post_id == mymodels.Posts.id,
                mymodels.Images.position == 1
            ), isouter=True)
            .where(mymodels.Posts.id == post_id)
        )

        result = session.execute(stmt).all()

        if not result:
            return jsonify({"success": False, "message": "Post not found"}), 404

        post, location, species_name, user, image_url = result[0]

        # レスポンスの生成
        response = {
            "id": post.id,
            "description": post.description,
            "collected_at": post.collected_at.strftime("%Y-%m-%d") if post.collected_at else None,
            "location": {
                "name": location.name,
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
            "species_names": list(set([r[2] for r in result if r[2]])),
            "user": {
                "name": user.name if user else "匿名",
                "icon": f"/static/images/{user.icon}" if user and user.icon else f"/static/images/{DEFAULT_ICON_PATH}",
            },
            "image_url": f"/static/images/{image_url}" if image_url else f"/static/images/{DEFAULT_POST_IMAGE_PATH}"
        }

        return jsonify(response)

    except Exception as e:
        logging.error(f"Error in get_post_details: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

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

        # クエリの実行
        rows = session.execute(stmt).fetchall()

        # デバッグ用: クエリ結果を出力
        print("Query result:")
        for row in rows:
            print(row)  # 全体の行を出力
            for key, value in row._mapping.items():
                print(f"Field: {key}, Value: {value}, Type: {type(value)}")  # 各フィールドの型を確認

        # 結果を整形
        result = [
            {
                'id': row.id,
                'user_name': row.user_name,
                'location_name': row.location_name,
                'collected_at': row.collected_at.isoformat() if row.collected_at else None,
                'description': row.description,
                'user_icon': row.user_icon.decode('utf-8') if isinstance(row.user_icon, bytes) else row.user_icon,  # デコードを追加
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
                func.group_concat(
                    distinct(
                        mymodels.Species.name+','+
                        mymodels.SpeciesInfo.gender+','+
                        cast(mymodels.SpeciesInfo.count, String)+','+
                        cast(mymodels.SpeciesInfo.max_size, String)
                        )).label("species_data"),
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
            .outerjoin(mymodels.Users, mymodels.Posts.user_id == mymodels.Users.id)
            .outerjoin(mymodels.Location, mymodels.Posts.id == mymodels.Location.post_id)
            .outerjoin(mymodels.SpeciesInfo, mymodels.Posts.id == mymodels.SpeciesInfo.post_id)
            .outerjoin(mymodels.Species, mymodels.SpeciesInfo.species_id == mymodels.Species.id)
            .outerjoin(mymodels.MethodInfo, mymodels.Posts.id == mymodels.MethodInfo.post_id)
            .outerjoin(mymodels.Method, mymodels.MethodInfo.method_id == mymodels.Method.id)
            .outerjoin(mymodels.TreeInfo, mymodels.Posts.id == mymodels.TreeInfo.post_id)
            .outerjoin(mymodels.Tree, mymodels.TreeInfo.tree_id == mymodels.Tree.id)
            .outerjoin(mymodels.Environment, mymodels.Posts.id == mymodels.Environment.post_id)
            .outerjoin(mymodels.DangerousSpeciesInfo, mymodels.Posts.id == mymodels.DangerousSpeciesInfo.post_id)
            .outerjoin(mymodels.DangerousSpecies, mymodels.DangerousSpeciesInfo.dangerous_species_id == mymodels.DangerousSpecies.id)
            .outerjoin(mymodels.FacilityInfo, mymodels.Posts.id == mymodels.FacilityInfo.post_id)
            .outerjoin(mymodels.Facility, mymodels.FacilityInfo.facility_id == mymodels.Facility.id)
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

########### Yoshiki 追加（投稿）####################
@app.route("/api/posts", methods=["POST"])
def create_post():
    data = request.form
    files = request.files
    print("Received data:", data)

    # 必須フィールドのチェック
    if not data.get("collectionDate") or not data.get("collectionPlace"):
        return jsonify({"error": "画像と採集日時と採集場所は必須です"}), 400

    try:
        with crud.session_scope() as session:
            # Posts テーブルへの挿入
            post_id = insert_post(data, session)

            # Images テーブルへの挿入
            save_images(files, post_id, session)

            # Location テーブルへの挿入
            insert_location(data, post_id, session)

            # Environment テーブルへの挿入
            insert_environment(data, post_id, session)

            # SpeciesInfo テーブルへの挿入
            insert_species_info(data, post_id, session)

        return jsonify({"message": "投稿が成功しました！"}), 201

    except Exception as e:
        print(f"エラー: {e}")
        return jsonify({"error": f"投稿に失敗しました: {str(e)}"}), 500


def insert_post(data, session):
    """Posts テーブルへのデータ挿入"""
    post_data = {
    "user_id": 1,  # 仮のユーザーID
    "description": data.get("memo"),
    "collected_at": datetime.strptime(data.get("collectionDate"), "%Y-%m-%dT%H:%M"),
    "created_at": datetime.now(),
    "updated_at": datetime.now(),
    }
    session.execute(insert(mymodels.Posts).values(post_data))

    # 最後に挿入された ID を取得
    post_id = get_last_inserted_id(session, mymodels.Posts)
    return post_id


def save_images(files, post_id, session):
    """Images テーブルへのデータ挿入"""
    for key in files:
        file = files[key]
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(POST_UPLOAD_FOLDER, unique_filename)
        os.makedirs(POST_UPLOAD_FOLDER, exist_ok=True)
        file.save(file_path)

        image_data = {
            "post_id": post_id,
            "image_url": file_path,
        }
        session.execute(insert(mymodels.Images).values(image_data))


def insert_location(data, post_id, session):
    """Location テーブルへのデータ挿入"""
    location_data = {
        "name": data.get("collectionPlace"),
        "latitude": None,  # Google Maps API で取得する場合、ここに処理を追加
        "longitude": None,
        "post_id": post_id,
    }
    session.execute(insert(mymodels.Location).values(location_data))


def insert_environment(data, post_id, session):
    """Environment テーブルへのデータ挿入"""
    environment_data = {
        "post_id": post_id,
        "whether": data.get("weather"),
        "temperature": float(data.get("temperature") or 0),  # None の場合は 0 に
        "is_restricted_area": data.get("forbiddenArea") == "該当する",
        "crowd_level": {"少ない": 1, "普通": 2, "多い": 3}.get(data.get("crowdLevel"), None),
        "free_memo": data.get("memo"),
    }
    session.execute(insert(mymodels.Environment).values(environment_data))


def insert_species_info(data, post_id, session):
    """SpeciesInfo テーブルへのデータ挿入"""
    species_list = json.loads(data.get("rows", "[]"))  # rows を JSON としてデコード
    for species in species_list:
        species_data = {
            "post_id": post_id,
            "species_other": species.get("type"),
            "gender": species.get("gender"),
            "count": int(species.get("count") or 0),  # None の場合は 0 に
            "max_size": float(species.get("maxSize") or 0),  # None の場合は 0 に
        }
        session.execute(insert(mymodels.SpeciesInfo).values(species_data))

##############Yoshiki最終行##############
