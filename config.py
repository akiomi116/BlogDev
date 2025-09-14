# config.py
import os

# BASE_DIR はプロジェクトのルートディレクトリ (F:\dev\BrogDev) を指します
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # アプリケーションのセキュリティキー (セッション管理などに使用)
    
    # 良い例1: 環境変数から取得する (本番環境推奨)
    # 環境変数に SECRET_KEY="ここにランダムで長い固定の文字列" を設定しておく必要があります。
    # 例: PowerShellなら $env:SECRET_KEY = "your_secret_key_here"
    # SECRET_KEY = os.environ.get('SECRET_KEY')

    # 良い例2: デバッグ/開発用に、コード内に固定の文字列を直接書く (本番環境では非推奨)
    # 非常に長く、推測されにくい文字列にしてください。
    
    SECRET_KEY = 'ihsnAki9'

    # SESSION_COOKIE_SAMESITE = "None"
    SESSION_COOKIE_SECURE = False 

    # SECURITY_REGISTERABLE = True # ユーザー登録を許可する場合
    # SECURITY_CONFIRMABLE = False # ユーザー確認メールを必須にしない場合
    # SECURITY_TRACKABLE = True # ユーザーログイン/ログアウト追跡

    # Flask-Security-Too の認証関連設定
    # Flask-Security-Too のデバッグログを有効にする
    SECURITY_TRACKABLE = True # ユーザーのログイン/ログアウトを追跡
    SECURITY_PASSWORD_SALT = 'a_random_salt_for_password_hashing' # パスワードソルトも設定

    # 明示的なURL設定 (デフォルトで通常は不要ですが、念のため確認)
    SECURITY_URL_PREFIX = "/security" # デフォルト
    SECURITY_LOGIN_URL = "/login"     # デフォルト
    SECURITY_LOGOUT_URL = "/logout"   # デフォルト
    SECURITY_POST_LOGIN_VIEW = "/index" # ログイン後のリダイレクト先
    SECURITY_POST_LOGOUT_VIEW = "/"   # ログアウト後のリダイレクト先
    SECURITY_UNAUTHORIZED_VIEW = "/login" # 認証されていない場合のビュー

    # セッション関連のデバッグ
    SECURITY_FLASH_MESSAGES = True # Flashメッセージを有効にする（エラー表示のため）
    # SESSION_COOKIE_SAMESITE = "None" # config.pyで既に設定済み
    # SESSION_COOKIE_SECURE = False   # config.pyで既に設定済み
    
  
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
