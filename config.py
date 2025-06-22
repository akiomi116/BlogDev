# config.py
import os

# BASE_DIR はプロジェクトのルートディレクトリ (F:\dev\BrogDev) を指します
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # アプリケーションのセキュリティキー (セッション管理などに使用)
    SECRET_KEY = os.urandom(24).hex()

    # データベースのURI設定
    # SQLiteデータベースファイルが 'instance' フォルダ内に作成されます
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'akiomi.db')
    # SQLAlchemyのイベントトラッキングを無効にします (リソース節約のため)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # デバッグモードを有効にします (開発環境向け)
    DEBUG = True

    # --- 画像アップロード関連の設定 ---
    # UPLOAD_FOLDER は、アップロードされたファイルが保存される基底ディレクトリの絶対パスです。
    # 例: F:\dev\BrogDev\static\uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')

    # アップロードされた画像ファイルが保存されるディレクトリの絶対パス
    # 例: F:\dev\BrogDev\static\uploads\images
    UPLOAD_IMAGES_DIR = os.path.join(UPLOAD_FOLDER, 'images')
    
    # 生成されたサムネイルが保存されるディレクトリの絶対パス
    # 例: F:\dev\BrogDev\static\uploads\thumbnails
    UPLOAD_THUMBNAILS_DIR = os.path.join(UPLOAD_FOLDER, 'thumbnails')

    # Flaskの url_for('static', filename=...) で使用するための相対パス
    # 'static' フォルダからの相対パスになります
    # 例: 'uploads/images' (static/uploads/images に対応)
    UPLOAD_FOLDER_RELATIVE_PATH = os.path.join('uploads', 'images')
    # 例: 'uploads/thumbnails' (static/uploads/thumbnails に対応)
    THUMBNAIL_FOLDER_RELATIVE_PATH = os.path.join('uploads', 'thumbnails')

    # 許可される画像ファイルの拡張子
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'} # webp を追加
    # アップロードされるファイルの最大サイズ (バイト単位)
    MAX_CONTENT_LENGTH = 250 * 1024 * 1024 # 250MB (例: 16MB)

    # サムネイル生成に関する設定
    GENERATE_THUMBNAILS = True # サムネイルを生成するかどうか
    THUMBNAIL_SIZE = (400, 300) # サムネイルのサイズ (幅, 高さ)

    # デバッグ用の出力は不要であれば削除またはコメントアウト
    # print(f"DEBUG: SQLALCHEMY_DATABASE_URI: {SQLALCHEMY_DATABASE_URI}")
    # print(f"DEBUG: UPLOAD_FOLDER (Absolute): {UPLOAD_FOLDER}")
    # print(f"DEBUG: UPLOAD_IMAGES_DIR (Absolute): {UPLOAD_IMAGES_DIR}")
    # print(f"DEBUG: UPLOAD_THUMBNAILS_DIR (Absolute): {UPLOAD_THUMBNAILS_DIR}")
    # print(f"DEBUG: UPLOAD_FOLDER_RELATIVE_PATH (Relative from static): {UPLOAD_FOLDER_RELATIVE_PATH}")
    # print(f"DEBUG: THUMBNAIL_FOLDER_RELATIVE_PATH (Relative from static): {THUMBNAIL_FOLDER_RELATIVE_PATH}")
