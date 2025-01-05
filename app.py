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
from sqlalchemy.exc import SQLAlchemyError
import uuid
import urllib.parse

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = os.urandom(24)

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # スクリプトのあるディレクトリを取得
BASE_IMAGES_DIR = os.path.join(os.getcwd(), "images") # 画像フォルダのベースディレクトリ
POST_UPLOAD_FOLDER = os.path.join(BASE_IMAGES_DIR, 'post_images/')

DEFAULT_ICON_PATH = "icon_images/face-icon.svg"  # デフォルトアイコンのパス
DEFAULT_POST_IMAGE_PATH = 'post_images/no-image-icon.svg'  # デフォルト採集記録画像のパス

SessionLocal = sessionmaker(bind=engine)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


# トップページルート
@app.route("/")
def index():
    return "<p>Flask top page!</p>"

###############################
# /mapと/post/[id]で使用する静的ファイル（画像）を受け渡すエンドポイント
###############################
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


###############################
# /mypageで使用する画像を受け渡すエンドポイント
###############################
# カレントディレクトリを取得
BASE_DIR = os.getcwd()
# 画像を提供するエンドポイント
@app.route('/images/<folder>/<path:filename>')
def serve_images(folder, filename):
    """
    images ディレクトリ内の任意のサブフォルダに対してアクセスを許可。
    サブフォルダ名: icon_images, post_images
    """
    allowed_folders = ['icon_images', 'post_images']

    if folder not in allowed_folders:
        abort(403, description="Access to this directory is not allowed.")

    images_dir = os.path.join(BASE_DIR, 'images', folder)
    requested_file_path = os.path.join(images_dir, filename)

    if not os.path.isfile(requested_file_path):
        abort(404, description="Image not found.")

    return send_from_directory(images_dir, filename)

if __name__ == '__main__':
    app.run(debug=True)

###############################
# ユーザー登録
###############################
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
        # 新しいユーザーをデータベースに挿入
        new_user_id = crud.myinsert(mymodels.Users, values)  # 修正後の関数を呼び出す

        # テスト用のパスワード（本番ではセキュアな方法を使用）
        generated_password = "1234"  # ここは適宜変更可能

        return jsonify({
            "message": "User created successfully",
            "user_id": new_user_id,  # 実際のユーザーIDを返す
            "password": generated_password
        }), 201

    except Exception as e:
        print(f"Database insert failed: {e}")
        return jsonify({"error": f"Database insert failed: {str(e)}"}), 500


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
                "icon": f"/static/images/{user.icon}" if user and user.icon else f"/static/images{DEFAULT_ICON_PATH}",
            },
            "image_url": f"/static/images/{image_url}" if image_url else f"/static/images{DEFAULT_POST_IMAGE_PATH}"
        }

        return jsonify(response)

    except Exception as e:
        logging.error(f"Error in get_post_details: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        session.close()

###############################
# マイページ表示
###############################
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
                mymodels.Users.collection_start_at,  # 追加: 採集開始日
                mymodels.Location.name.label("location_name"),
                mymodels.Posts.collected_at,
                mymodels.Posts.description,
                mymodels.Users.icon.label("user_icon"),
                func.group_concat(func.coalesce(mymodels.Species.name, '不明').distinct()).label("species_name"),
                func.group_concat(func.distinct(mymodels.Images.image_url)).label("image_urls")  
            )
            .join(mymodels.Users, mymodels.Posts.user_id == mymodels.Users.id)
            .join(mymodels.SpeciesInfo, mymodels.Posts.id == mymodels.SpeciesInfo.post_id)
            .join(mymodels.Species, mymodels.SpeciesInfo.species_id == mymodels.Species.id)
            .join(mymodels.Location, mymodels.Posts.id == mymodels.Location.post_id)
            .outerjoin(mymodels.Images, mymodels.Posts.id == mymodels.Images.post_id)
            .where(mymodels.Users.id == user_id)
            .group_by(
                mymodels.Posts.id,
                mymodels.Users.name,
                mymodels.Users.collection_start_at,  # 追加: グループ化に含める
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
                'collection_start_at': row.collection_start_at.isoformat() if row.collection_start_at else None,  # 追加: フィールドを整形
                'location_name': row.location_name,
                'collected_at': row.collected_at.isoformat() if row.collected_at else None,
                'description': row.description,
                'user_icon': row.user_icon.decode('utf-8') if isinstance(row.user_icon, bytes) else row.user_icon,  # デコードを追加
                'species_name': row.species_name or '-',
                'image_urls': row.image_urls.split(',') if row.image_urls else []  # 画像URLをリストとして返す
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



############################
# 詳細ページ
############################
@app.route('/post/<int:post_id>', methods=['GET'])
def get_post(post_id):
    session = SessionLocal()

    try:
        # 投稿情報を取得
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
                        mymodels.Species.name + ',' +
                        mymodels.SpeciesInfo.gender + ',' +
                        cast(mymodels.SpeciesInfo.count, String) + ',' +
                        cast(mymodels.SpeciesInfo.max_size, String)
                    )
                ).label("species_data"),
                func.group_concat(distinct(mymodels.Method.name)).label("methods"),
                mymodels.MethodInfo.method_other,
                func.group_concat(distinct(mymodels.Tree.name)).label("trees"),
                mymodels.TreeInfo.tree_other,
                mymodels.Environment.whether,
                mymodels.Environment.temperature,
                mymodels.Environment.crowd_level,  # crowd_levelを追加
                mymodels.Environment.is_restricted_area,  # is_restricted_areaを追加
                func.group_concat(distinct(mymodels.DangerousSpecies.name)).label("dangerous_species_names"),
                mymodels.DangerousSpeciesInfo.dangerous_species_other,
                func.group_concat(distinct(mymodels.Facility.name)).label("facilities"),
                mymodels.FacilityInfo.facility_other,
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
                mymodels.Environment.crowd_level,  # group_by に crowd_level を追加
                mymodels.Environment.is_restricted_area,  # group_by に is_restricted_area を追加
                mymodels.DangerousSpeciesInfo.dangerous_species_other,
                mymodels.FacilityInfo.facility_other,
                mymodels.Environment.free_memo
            )
        )
        post = session.execute(stmt).first()

        if not post:
            print(f"No post found with id: {post_id}")
            return jsonify({"success": False, "message": "Post not found"}), 404

        # 投稿画像を取得
        image_stmt = (
            select(
                mymodels.Images.image_url,
                mymodels.Images.position
            )
            .where(mymodels.Images.post_id == post_id)
            .order_by(mymodels.Images.position)
        )
        images = session.execute(image_stmt).fetchall()

        # 投稿画像のリストを作成
        post_images = [
            {
                "url": f"/static/images/{image.image_url}" if image.image_url else f"/static/images/{DEFAULT_POST_IMAGE_PATH}",
                "position": image.position
            }
            for image in images
        ]

        # ユーザーアイコンの処理
        user_icon = f"/static/images/{post.user_icon}" if post.user_icon else f"/static/images/{DEFAULT_ICON_PATH}"

        # レスポンスを作成
        response = {
            "post_id": post.id,
            "description": post.description,
            "collected_at": post.collected_at.isoformat() if post.collected_at else None,
            "user_name": post.user_name,
            "user_icon": user_icon,
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
            "crowd_level": post.crowd_level,
            # "is_restricted_area": post.is_restricted_area,
            "is_restricted_area": bool(post.is_restricted_area) if post.is_restricted_area is not None else None,
            "dangerous_species_names": post.dangerous_species_names,
            "dangerous_species_other": post.dangerous_species_other,
            "facilities": post.facilities,
            "facility_other": post.facility_other,
            "free_memo": post.free_memo,
            "images": post_images,
        }

        return jsonify(response)

    except Exception as e:
        print(f"Query failed: {e}")  # 明示的なエラー出力
        return jsonify({'error': str(e)}), 500

    finally:
        session.close()



###############################
# 採集記録の投稿
###############################
@app.route("/api/posts", methods=["POST"])
def create_post():
    data = request.form
    files = request.files
    print("Received data:", data)

    # 必須フィールドのチェック
    if not data.get("collectionDate") or not data.get("collectionPlace") or not data.get("user_id"):
        return jsonify({"error": "ユーザーID、画像、採集日時、採集場所は必須です"}), 400

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
            
            # MethodInfo テーブルへの挿入
            insert_method_info(data, post_id, session)
            
            # facilityInfo テーブルへの挿入
            insert_facility_info(data, post_id, session)
            
            # dangerousInfo テーブルへの挿入
            insert_dangerous_species_info(data, post_id, session)
            
            # treeInfo テーブルへの挿入
            insert_trees_info(data, post_id, session)

        return jsonify({"message": "投稿が成功しました！"}), 201

    except Exception as e:
        print(f"エラー: {e}")
        return jsonify({"error": f"投稿に失敗しました: {str(e)}"}), 500


def insert_post(data, session):
    """Posts テーブルへのデータ挿入"""
    post_data = {
    "user_id": int(data.get("user_id")),
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
    position = 1  # position を初期化
    for key in files:
        file = files[key]
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(POST_UPLOAD_FOLDER, unique_filename)
        os.makedirs(POST_UPLOAD_FOLDER, exist_ok=True)
        file.save(file_path)

        # 相対パスを取得
        relative_path = os.path.relpath(file_path, BASE_IMAGES_DIR)  # BASE_IMAGES_DIRからの相対パス

        # position を追加
        image_data = {
            "post_id": post_id,
            "image_url": relative_path,  # 相対パスを保存
            "position": position
        }
        session.execute(insert(mymodels.Images).values(image_data))

        # 次のファイルのために position をインクリメント
        position += 1



def insert_location(data, post_id, session):
    """Location テーブルへのデータ挿入"""
    place = data.get("collectionPlace")
    latitude, longitude = None, None
    prefecture, city = None, None

    if place:
        try:
            # 環境変数からGoogle Maps APIキーを取得
            api_key = "AIzaSyBVlySFxUukdMeWL_vv6UcDV2ajXKht9so"
            # api_key = os.getenv("GOOGLE_MAPS_API_KEY")
            if not api_key:
                raise ValueError("Google Maps APIキーが設定されていません")
            
            # 日本語住所をURLエンコード
            encoded_place = urllib.parse.quote(place)

            # Google Maps Geocoding APIを使用して住所情報を取得
            geocoding_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_place}&key={api_key}&language=ja"
            response = requests.get(geocoding_url)
            response_data = response.json()

            if response_data["status"] == "OK":
                location = response_data["results"][0]["geometry"]["location"]
                latitude = location["lat"]
                longitude = location["lng"]

                # 住所コンポーネントから都道府県と市区町村を抽出
                for component in response_data["results"][0]["address_components"]:
                    if "administrative_area_level_1" in component["types"]:  # 都道府県
                        prefecture = component["long_name"]
                    if "locality" in component["types"]:  # 市区町村
                        city = component["long_name"]

                print(f"Extracted Data - Prefecture: {prefecture}, City: {city}, Latitude: {latitude}, Longitude: {longitude}")
            else:
                print(f"Google Maps API エラー: {response_data['status']}")

        except Exception as e:
            print(f"Geocoding API の呼び出し中にエラーが発生しました: {e}")

    # Location データの挿入
    location_data = {
        "name": place,
        "latitude": latitude,
        "longitude": longitude,
        "prefecture": prefecture,
        "city": city,
        "post_id": post_id,
    }
    print("Location Data to Insert:", location_data)  # デバッグ用ログ

    try:
        session.execute(insert(mymodels.Location).values(location_data))
        print("Locationデータ挿入成功")
    except Exception as e:
        print(f"Locationデータ挿入エラー: {e}")

def insert_species_info(data, post_id, session):
    """SpeciesInfo テーブルへのデータ挿入"""
    # 種類と性別のデータを JSON として受け取る
    species_list = json.loads(data.get("rows", "[]"))  # rows を JSON としてデコード

    # 種類と species_id のマッピング
    species_mapping = {
        "カブトムシ": 1,
        "コクワガタ": 2,
        "ノコギリクワガタ": 3,
        "スジクワガタ": 4,
        "ヒラタクワガタ": 5,
        "ミヤマクワガタ": 6,
        "アカアシクワガタ": 7,
        "その他": 8,
    }

    # 性別の変換マッピング
    gender_mapping = {
        "オス": "♂",
        "メス": "♀",
        "両方": "両方",  # 必要なら "両方" もそのまま残す
        "": None,  # 未選択は None にする
    }

    # for species in species_list:
    #     raw_gender = species.get("gender")  # フロントエンドから受け取った生データ
    #     gender = gender_mapping.get(raw_gender, None)  # 性別を変換
        
    #     # デバッグ用のログを追加
    #     print(f"Species data received: {species}")
    #     print(f"Raw gender: {raw_gender}, Mapped gender: {gender}")
    #     # species_id を取得
    #     species_id = species_mapping.get(species.get("type"), 8)  # 見つからない場合は "その他" (ID: 8)
        
    #     # gender を変換
    #     gender = gender_mapping.get(species.get("gender"), None)
    for species in species_list:
        raw_gender = species.get("gender")
        print(f"Received gender: {raw_gender}")  # フロントエンドからの性別データを確認
        gender = gender_mapping.get(raw_gender.strip(), None)  # 空白を削除してからマッピング

        print(f"Mapped gender: {gender}")  # マッピング結果を確認

        species_id = species_mapping.get(species.get("type"), 8)

        # 挿入データの構築
        species_data = {
            "post_id": post_id,
            "species_id": species_id,  # species_id を連携
            "species_other": None if species_id != 8 else species.get("type"),  # その他の場合にのみ詳細を保存
            "gender": gender,  # 性別 (変換後の値を保存)
            "count": int(species.get("count") or 0),  # 採集数 (None の場合は 0)
            "max_size": float(species.get("maxSize") or 0),  # 最大サイズ (None の場合は 0)
        }

        # DB に挿入
        session.execute(insert(mymodels.SpeciesInfo).values(species_data))


def insert_environment(data, post_id, session):
    """Environment テーブルへのデータ挿入"""
    environment_data = {
        "post_id": post_id,
        "whether": data.get("weather", ""), # 天気
        "temperature": float(data.get("temperature") or 0),  # 気温、Noneの場合は0
        "is_restricted_area": data.get("forbiddenArea") == "該当する",  # 採集禁止エリア
        "crowd_level": {"少ない": 1, "普通": 2, "多い": 3}.get(data.get("crowdLevel"), None),  # 人の混み具合
        "free_memo": data.get("memo", ""),  # メモ
    }
    session.execute(insert(mymodels.Environment).values(environment_data))

def insert_method_info(data, post_id, session):
    """MethodInfo テーブルへのデータ挿入"""
    method_id = data.get("collectionMethod")
    method_other = data.get("collectionMethodOther") if method_id == "7" else None

    # データ挿入
    method_data = {
        "post_id": post_id,
        "method_id": int(method_id),
        "method_other": method_other,  # 「その他」の場合に自由入力値を保存
    }

    session.execute(insert(mymodels.MethodInfo).values(method_data))

def insert_trees_info(data, post_id, session):
    """TreesInfo テーブルへのデータ挿入"""
    trees_info = json.loads(data.get("trees_info", "[]"))  # JSON をデコード
    for tree in trees_info:
        tree_data = {
            "post_id": post_id,
            "tree_id": int(tree.get("id")),  # 選択した樹木のID
            "tree_other": tree.get("other", None),  # その他の場合の詳細
        }
        session.execute(insert(mymodels.TreeInfo).values(tree_data))


def insert_dangerous_species_info(data, post_id, session):
    """DangerousSpeciesInfo テーブルへのデータ挿入"""
    dangerous_species_info = json.loads(data.get("dangerous_species_info", "[]"))  # JSON をデコード
    for species in dangerous_species_info:
        dangerous_species_data = {
            "post_id": post_id,
            "dangerous_species_id": int(species.get("id")),  # 危険動物のID
            "dangerous_species_other": species.get("other"),  # その他の場合の詳細
        }
        session.execute(insert(mymodels.DangerousSpeciesInfo).values(dangerous_species_data))

def insert_facility_info(data, post_id, session):
    """FacilityInfo テーブルへのデータ挿入"""
    facility_info = json.loads(data.get("facility_info", "[]"))  # JSON をデコード
    
    # facility_info が空の場合は何もしない
    if not facility_info:
        print("No facility_info data provided.")
        return
    
    for facility in facility_info:
        facility_data = {
            "post_id": post_id,
            "facility_id": int(facility.get("id")),  # 選択した施設のID
            "facility_other": facility.get("other")  # その他の場合の詳細
        }

        session.execute(insert(mymodels.FacilityInfo).values(facility_data))
