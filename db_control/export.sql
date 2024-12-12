SET foreign_key_checks = 0;
BEGIN TRANSACTION;

-- imagesテーブル
CREATE TABLE IF NOT EXISTS `images` (
    id INT AUTO_INCREMENT PRIMARY KEY,       -- 画像ID (主キー、自動インクリメント)
    post_id INT NOT NULL,                    -- 投稿ID (外部キー)
    image_url VARCHAR(255) NOT NULL,         -- 画像URL
    position INT,                            -- 表示順序またはポジション
    FOREIGN KEY (post_id) REFERENCES posts(id) -- 外部キー制約: postsテーブルのIDを参照
);

-- environmentテーブル
CREATE TABLE `environment` (
    id INT AUTO_INCREMENT PRIMARY KEY,       -- 環境情報ID (主キー、自動インクリメント)
    post_id INT NOT NULL,                    -- 投稿ID (外部キー)
    whether VARCHAR(255),                    -- 天候
    temperature DOUBLE,                      -- 温度
    is_restricted_area TINYINT(1),           -- 採集禁止エリアフラグ (true/false)
    crowd_level INT,                         -- 混雑レベル (1=少, 2=普通, 3=多)
    free_memo TEXT,                          -- 自由記述メモ
    FOREIGN KEY (post_id) REFERENCES posts(id) -- 外部キー制約: postsテーブル
);

-- データ挿入
INSERT INTO `environment` (id, post_id, whether, temperature, is_restricted_area, crowd_level, free_memo) VALUES
(1, 2, '晴れ', 32.0, 0, 1, 'クヌギ御神木。クワカブもスズメバチもいつも出会える。'),
(2, 3, '晴れ', 32.0, 0, 1, 'クヌギノコの木、ノコの穴場'),
(3, 4, '晴れ', 33.0, 0, 1, '涼しい時間帯なら近くで散歩している人もいて、安心'),
(4, 5, '晴れ', 32.0, 0, 1, 'ペットボトル型バナナトラップを夜中に4か所付けて朝にはどれも満員！常楽寺の駐車場をお借りしました。'),
(5, 6, '晴れ', 33.0, 0, 2, 'ミュージアム入口近辺のハルニレを蹴ったらノコシャワー！周囲の子供たちも必死に拾っていました（笑）'),
(6, 7, '晴れ', 30.0, 0, 1, 'この公園は採集禁止！観察を楽しむ！ヒラタ♂の死骸も発見。');

-- species_infoテーブルの作成
CREATE TABLE `species_info` (
    id INT AUTO_INCREMENT PRIMARY KEY,       -- 種情報ID (主キー、自動インクリメント)
    post_id INT NOT NULL,                    -- 投稿ID (外部キー)
    species_id INT,                          -- 種ID (外部キー)
    species_other VARCHAR(255),              -- その他の種 (自由記述)
    gender VARCHAR(10),                      -- 性別 (male, female, unknown)
    count INT,                               -- 採集数
    max_size DOUBLE,                         -- 最大サイズ (cm)
    FOREIGN KEY (post_id) REFERENCES posts(id), -- 外部キー制約: postsテーブル
    FOREIGN KEY (species_id) REFERENCES species(id) -- 外部キー制約: speciesテーブル
);

-- データの挿入
INSERT INTO `species_info` (id, post_id, species_id, species_other, gender, count, max_size) VALUES
(1, 2, 1, NULL, '♂', 2, NULL),
(2, 2, 1, NULL, '♀', 4, NULL),
(3, 2, 3, NULL, '♂', 1, 44.0),
(4, 3, 3, NULL, '♂', 1, 55.0),
(5, 3, 3, NULL, '♀', 1, NULL),
(6, 4, 1, NULL, '♀', 1, NULL),
(7, 4, 3, NULL, '♂', 2, NULL),
(8, 4, 3, NULL, '♀', 2, NULL),
(9, 4, 2, NULL, '♂', 4, NULL),
(10, 5, 1, NULL, '♂', 20, NULL),
(11, 5, 1, NULL, '♀', 20, NULL),
(12, 5, 3, NULL, '♂', 1, NULL),
(13, 5, 3, NULL, '♀', 2, 76.0),
(14, 5, 2, NULL, '♂', 4, 55.0),
(15, 6, 3, NULL, '♂', 5, 65.1),
(16, 6, 3, NULL, '♀', 3, 33.7),
(17, 7, 1, NULL, '♂', 6, NULL),
(18, 7, 1, NULL, '♀', 4, NULL),
(19, 7, 3, NULL, '♂', 3, NULL),
(20, 7, 3, NULL, '♀', 2, NULL),
(21, 7, 2, NULL, '♂', 2, NULL),
(22, 7, 2, NULL, '♀', 1, 72.0),
(23, 7, 4, NULL, '♂', 1, NULL),
(24, 7, 4, NULL, '♀', 1, 65.0);

-- speciesテーブルの作成
CREATE TABLE `species` (
    id INT AUTO_INCREMENT PRIMARY KEY,      -- 種ID (主キー、自動インクリメント)
    name VARCHAR(255) NOT NULL              -- 種の名前
);

-- データの挿入
INSERT INTO `species` (id, name) VALUES
(1, 'カブトムシ'),
(2, 'コクワガタ'),
(3, 'ノコギリクワガタ'),
(4, 'スジクワガタ'),
(5, 'ヒラタクワガタ'),
(6, 'ミヤマクワガタ'),
(7, 'アカアシクワガタ'),
(8, 'その他');

-- methodテーブルの作成
CREATE TABLE `method` (
    id INT AUTO_INCREMENT PRIMARY KEY,      -- 採集方法ID (主キー、自動インクリメント)
    name VARCHAR(255) NOT NULL              -- 採集方法名
);

-- データの挿入
INSERT INTO `method` (id, name) VALUES
(1, '樹液'),
(2, '木蹴り'),
(3, '果実トラップ'),
(4, 'ライトトラップ'),
(5, '朽木探索'),
(6, '材割'),
(7, 'その他');

-- treeテーブルの作成
CREATE TABLE `tree` (
    id INT AUTO_INCREMENT PRIMARY KEY,      -- 樹種ID (主キー、自動インクリメント)
    name VARCHAR(255) NOT NULL              -- 樹種名
);

-- データの挿入
INSERT INTO `tree` (id, name) VALUES
(1, 'クヌギ'),
(2, 'コナラ'),
(3, 'カシ'),
(4, 'クリ'),
(5, 'アキニレ'),
(6, 'ハルニレ'),
(7, 'タブ'),
(8, 'ヤナギ'),
(9, 'オニグルミ'),
(10, 'シマトネリコ');

-- dangerous_speciesテーブルの作成
CREATE TABLE `dangerous_species` (
    id INT AUTO_INCREMENT PRIMARY KEY,      -- 危険生物ID (主キー、自動インクリメント)
    name VARCHAR(255) NOT NULL              -- 危険生物名
);

-- データの挿入
INSERT INTO `dangerous_species` (id, name) VALUES
(1, 'スズメバチ'),
(2, 'マダニ'),
(3, 'イノシシ'),
(4, 'クマ'),
(5, 'ヘビ'),
(6, 'その他');

-- facilityテーブルの作成
CREATE TABLE `facility` (
    id INT AUTO_INCREMENT PRIMARY KEY,      -- 施設ID (主キー、自動インクリメント)
    name VARCHAR(255) NOT NULL              -- 施設名
);

-- データの挿入
INSERT INTO `facility` (id, name) VALUES
(1, '自販機'),
(2, 'トイレ'),
(3, '駐車場'),
(4, 'コンビニ'),
(5, '遊具'),
(6, 'その他');

-- method_infoテーブルの作成
CREATE TABLE `method_info` (
    id INT AUTO_INCREMENT PRIMARY KEY,      -- 採集方法情報ID (主キー、自動インクリメント)
    post_id INT NOT NULL,                   -- 投稿ID (外部キー)
    method_id INT,                          -- 採集方法ID (外部キー)
    method_other VARCHAR(255),              -- その他の採集方法 (自由記述)
    FOREIGN KEY (post_id) REFERENCES posts(id),      -- 外部キー制約: postsテーブル
    FOREIGN KEY (method_id) REFERENCES method(id)    -- 外部キー制約: methodテーブル
);

-- データの挿入
INSERT INTO `method_info` (id, post_id, method_id, method_other) VALUES
(1, 2, 1, NULL),
(2, 3, 1, NULL),
(3, 4, 1, NULL),
(4, 5, 3, NULL),
(5, 6, 2, NULL),
(6, 7, NULL, NULL),
(7, 4, 2, NULL);

-- tree_infoテーブルの作成
CREATE TABLE `tree_info` (
    id INT AUTO_INCREMENT PRIMARY KEY,      -- 樹種情報ID (主キー、自動インクリメント)
    post_id INT NOT NULL,                   -- 投稿ID (外部キー)
    tree_id INT,                            -- 樹種ID (外部キー)
    tree_other VARCHAR(255),                -- その他の樹種 (自由記述)
    FOREIGN KEY (post_id) REFERENCES posts(id),      -- 外部キー制約: postsテーブル
    FOREIGN KEY (tree_id) REFERENCES tree(id)        -- 外部キー制約: treeテーブル
);

-- データの挿入
INSERT INTO `tree_info` (id, post_id, tree_id, tree_other) VALUES
(1, 2, 1, NULL),
(2, 3, 1, NULL),
(3, 4, 1, NULL),
(4, 4, 2, NULL),
(5, 5, 1, NULL),
(6, 6, 6, NULL),
(7, 7, 1, NULL),
(8, 7, 2, NULL);

-- dangerous_species_infoテーブルの作成
CREATE TABLE `dangerous_species_info` (
    id INT AUTO_INCREMENT PRIMARY KEY,               -- 危険生物情報ID (主キー、自動インクリメント)
    post_id INT NOT NULL,                            -- 投稿ID (外部キー)
    dangerous_species_id INT,                        -- 危険生物ID (外部キー)
    dangerous_species_other VARCHAR(255),            -- その他の危険生物 (自由記述)
    FOREIGN KEY (post_id) REFERENCES posts(id),      -- 外部キー制約: postsテーブル
    FOREIGN KEY (dangerous_species_id) REFERENCES dangerous_species(id) -- 外部キー制約: dangerous_speciesテーブル
);

-- データの挿入
INSERT INTO `dangerous_species_info` (id, post_id, dangerous_species_id, dangerous_species_other) VALUES
(1, 2, 1, NULL),
(2, 3, 1, NULL),
(3, 4, 1, NULL),
(4, 5, 1, NULL),
(5, 7, 1, NULL);

-- facility_infoテーブルの作成
CREATE TABLE `facility_info` (
    id INT AUTO_INCREMENT PRIMARY KEY,               -- 施設情報ID (主キー、自動インクリメント)
    post_id INT NOT NULL,                            -- 投稿ID (外部キー)
    facility_id INT,                                 -- 施設ID (外部キー)
    facility_other VARCHAR(255),                    -- その他の施設 (自由記述)
    FOREIGN KEY (post_id) REFERENCES posts(id),      -- 外部キー制約: postsテーブル
    FOREIGN KEY (facility_id) REFERENCES facility(id) -- 外部キー制約: facilityテーブル
);

-- データの挿入
INSERT INTO `facility_info` (id, post_id, facility_id, facility_other) VALUES
(1, 2, 3, NULL),
(2, 2, 2, NULL),
(3, 3, 3, NULL),
(4, 3, 2, NULL),
(5, 4, 3, NULL),
(6, 4, 2, NULL),
(7, 5, 3, NULL),
(8, 6, 3, NULL),
(9, 6, 2, NULL),
(10, 7, 4, NULL),
(11, 2, 1, NULL),
(12, 3, 1, NULL),
(13, 6, 1, NULL);

-- usersテーブルの作成
CREATE TABLE `users` (
    id INT AUTO_INCREMENT PRIMARY KEY,       -- ユーザーID (主キー、自動インクリメント)
    name VARCHAR(255) NOT NULL,              -- ユーザー名
    icon BLOB,                               -- ユーザーアイコン
    collection_start_at DATE NOT NULL,       -- コレクション開始日
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- 作成日時
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, -- 更新日時
    password VARCHAR(255) NOT NULL DEFAULT '1234' -- パスワード
);

-- データの挿入
INSERT INTO `users` (id, name, icon, collection_start_at, created_at, updated_at, password) VALUES
(1, 'test', NULL, '2024-12-03', '2024-12-04 01:13:37', '2024-12-04 01:13:37', '1234'),
(2, 'そうすけ', NULL, '2024-08-13', '2024-12-04 01:14:14', '2024-12-04 01:14:14', '1234'),
(3, 'テスト', NULL, '2024-08-13', '2024-12-04 20:56:15', '2024-12-04 20:56:15', '1234'),
(4, 'hayato', NULL, '2024-09-11', '2024-12-04 21:17:19', '2024-12-04 21:17:19', '1234'),
(5, 'jin', NULL, '2024-12-03', '2024-12-04 21:55:22', '2024-12-04 21:55:22', '1234'),
(6, 'がたろー', NULL, '2024-12-01', '2024-12-06 18:28:39', '2024-12-06 18:28:39', '1234');

-- locationテーブルの作成
CREATE TABLE `location` (
    id INT AUTO_INCREMENT PRIMARY KEY,       -- ロケーションID (主キー、自動インクリメント)
    name VARCHAR(255),                       -- 地名
    prefecture VARCHAR(255),                 -- 都道府県
    city VARCHAR(255),                       -- 市区町村
    latitude DOUBLE,                         -- 緯度
    longitude DOUBLE,                        -- 経度
    post_id INT NOT NULL,                    -- 投稿ID (外部キー)
    FOREIGN KEY (post_id) REFERENCES posts(id) -- 外部キー制約: postsテーブル
);

-- データの挿入
INSERT INTO `location` (id, name, prefecture, city, latitude, longitude, post_id) VALUES
(1, '邑楽町多々良沼公園', '群馬県', '邑楽町', 36.256686940000002, 139.491792612158, 2),
(2, '邑楽町多々良沼公園', '群馬県', '邑楽町', 36.256965000000000, 139.491404999999, 3),
(3, '多々良沼周辺', '群馬県', '邑楽町', 36.252926822163403, 139.492373909677, 4),
(4, '木戸町常楽寺裏', '群馬県', '木戸町', 36.278824574074902, 139.514012186983, 5),
(5, 'ミュージアムパーク茨城県自然博物館', '茨城県', '坂東市', 36.004010484607796, 139.916483425271, 6),
(6, '野山北・六道山公園', '東京都', '武蔵村山市', 35.7638717847669, 139.382785899999, 7);

-- postsテーブルの作成
CREATE TABLE IF NOT EXISTS `posts` (
    id INT AUTO_INCREMENT PRIMARY KEY,       -- 投稿ID (主キー、自動インクリメント)
    user_id INT NOT NULL,                    -- ユーザーID (外部キー)
    description TEXT,                        -- 投稿説明
    collected_at DATE,                       -- 採集日 (日付型)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 作成日時
    deleted_at DATETIME,                     -- 削除日時 (NULL可能)
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, -- 更新日時
    FOREIGN KEY (user_id) REFERENCES users(id) -- 外部キー制約: usersテーブル
);

-- データの挿入
INSERT INTO `posts` (id, user_id, description, collected_at, created_at, deleted_at, updated_at) VALUES
(2, 6, '圧巻の御神木、高確率でカブクワ何かしらいる！スズメバチも！', '2019-07-21', '2024-11-29 13:47:36', NULL, '2024-11-29 13:47:36'),
(3, 6, '不思議とノコが集まる木、掘ったり木蹴ったりすると…', '2019-07-21', '2024-11-29 13:48:48', NULL, '2024-11-29 13:48:48'),
(4, 6, '子供も安心の木蹴りスポット', '2023-08-15', '2024-11-29 13:49:54', NULL, '2024-11-29 13:49:54'),
(5, 6, 'バナナトラップでカブトムシうじゃうじゃ！もちろんトラップは全数回収。', '2019-07-21', '2024-11-29 13:49:54', NULL, '2024-11-29 13:49:54'),
(6, 6, 'ハルニレ蹴ったら、ノコシャワー！', '2021-07-17', '2024-11-29 13:50:53', NULL, '2024-11-29 13:50:53'),
(7, 6, 'いろんな昆虫の観察を楽しめる', '2020-08-01', '2024-11-29 13:51:48', NULL, '2024-11-29 13:51:48');

SET foreign_key_checks = 1;
