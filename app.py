from flask import Flask, request, jsonify
from flask_cors import CORS
from db_control import crud, mymodels
from db_control.crud import authenticate_user, get_last_inserted_id
from db_control.connect import engine
import json
import requests
import os
from datetime import datetime
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, or_, and_, text, distinct, func, cast, insert
from sqlalchemy.types import String
import uuid
import urllib.parse



app = Flask(__name__)
CORS(app) #全オリジンを許可

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
    position = 1  # position を初期化
    for key in files:
        file = files[key]
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file.save(file_path)

        # position を追加
        image_data = {
            "post_id": post_id,
            "image_url": file_path,
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
            api_key = os.getenv("GOOGLE_MAPS_API_KEY")
            if not api_key:
                raise ValueError("Google Maps APIキーが設定されていません")
            
            # 日本語住所をURLエンコード
            encoded_place = urllib.parse.quote(place)

            # Google Maps Geocoding APIを使用して住所情報を取得
            geocoding_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={place}&key={api_key}&language=ja"
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

    for species in species_list:
        raw_gender = species.get("gender")  # フロントエンドから受け取った生データ
        gender = gender_mapping.get(raw_gender, None)  # 性別を変換
        
        # デバッグ用のログを追加
        print(f"Species data received: {species}")
        print(f"Raw gender: {raw_gender}, Mapped gender: {gender}")
        # species_id を取得
        species_id = species_mapping.get(species.get("type"), 8)  # 見つからない場合は "その他" (ID: 8)
        
        # gender を変換
        gender = gender_mapping.get(species.get("gender"), None)

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
        "whether": data.get("weather"),  # 天気
        "temperature": float(data.get("temperature") or 0),  # 気温、Noneの場合は0
        "is_restricted_area": data.get("forbiddenArea") == "該当する",  # 採集禁止エリア
        "crowd_level": {"少ない": 1, "普通": 2, "多い": 3}.get(data.get("crowdLevel"), None),  # 人の混み具合
        "free_memo": data.get("memo"),  # メモ
    }
    session.execute(insert(mymodels.Environment).values(environment_data))


##############Yoshiki最終行##############