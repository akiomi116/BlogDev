# config.py
import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.urandom(24).hex()
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'akiomi.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = True  # デバッグモードを有効にする

    # 画像アップロード関連の設定を更新
    # 静的ファイルの提供元は 'static' ディレクトリなので、パスは 'static' から始める
    # 'uploads' を 'uploras' に変更し、画像をオリジナルとサムネイルに分ける
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads', 'images')
    THUMBNAIL_FOLDER = os.path.join(basedir, 'static', 'uploads', 'thumbnails')

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 250 * 1024 * 1024  # 16MB (例: 50メガバイト)

    # サムネイル生成に関する設定
    GENERATE_THUMBNAILS = True # サムネイルを生成するかどうか
    THUMBNAIL_SIZE = (400, 300) # サムネイルのサイズ (幅, 高さ)
    
    print(f"DEBUG: SQLALCHEMY_DATABASE_URI: {SQLALCHEMY_DATABASE_URI}")
    print(f"DEBUG: UPLOAD_FOLDER: {UPLOAD_FOLDER}")
    print(f"DEBUG: THUMBNAIL_FOLDER: {THUMBNAIL_FOLDER}")