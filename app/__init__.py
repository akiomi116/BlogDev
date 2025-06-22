# F:\dev\BrogDev\app/__init__.py

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import markdown # Jinja2フィルター内で使用するため
import pytz # datetime.now(pytz.utc) を使用するため

from flask import Flask, render_template, url_for, request, current_app, send_from_directory, g
from flask_login import current_user

import config # config モジュールをインポート

# app.extensions から拡張機能をインポート
from app.extensions import db, migrate, login_manager, csrf, babel, mail 

# ブループリントをインポート
from app.admin import bp as blog_admin_bp 
from app.routes.home import home_bp
from app.routes.auth import bp as auth_bp 
from app.routes.posts import public_posts_bp 


# アプリケーションファクトリ関数
def create_app(config_class=config.Config):
    # Flaskアプリケーションのインスタンスを作成
    # static_folder を明示的に設定し、プロジェクトのルートにある 'static' フォルダを指すようにする
    # config.BASE_DIR を使用
    app = Flask(__name__, static_folder=os.path.join(config.BASE_DIR, 'static')) 
    
    app.config.from_object(config_class)
    
    # アップロードディレクトリが存在することを確認し、なければ作成します
    os.makedirs(app.config['UPLOAD_IMAGES_DIR'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_THUMBNAILS_DIR'], exist_ok=True)

    # デバッグ情報のロギング (app.logger を使用して、ファイルやコンソールに出力されるようにする)
    app.logger.info(f"DEBUG: Flask app root path: {app.root_path}")
    app.logger.info(f"DEBUG: Flask app static folder: {app.static_folder}")
    app.logger.info(f"DEBUG: Flask app static URL path: {app.static_url_path}") # static_url_path は自動で /static になるので直接参照
    app.logger.info(f"DEBUG: Flask app template folder: {app.template_folder}")
    app.logger.info(f"DEBUG: Flask app instance path: {app.instance_path}")
    app.logger.debug(f"DEBUG: SQLALCHEMY_DATABASE_URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    app.logger.debug(f"DEBUG: UPLOAD_FOLDER (Absolute): {app.config.get('UPLOAD_FOLDER')}")
    app.logger.debug(f"DEBUG: UPLOAD_IMAGES_DIR (Absolute): {app.config.get('UPLOAD_IMAGES_DIR')}")
    app.logger.debug(f"DEBUG: UPLOAD_THUMBNAILS_DIR (Absolute): {app.config.get('UPLOAD_THUMBNAILS_DIR')}")
    app.logger.debug(f"DEBUG: UPLOAD_FOLDER_RELATIVE_PATH (Relative from static): {app.config.get('UPLOAD_FOLDER_RELATIVE_PATH')}")
    app.logger.debug(f"DEBUG: THUMBNAIL_FOLDER_RELATIVE_PATH (Relative from static): {app.config.get('THUMBNAIL_FOLDER_RELATIVE_PATH')}")


    # 拡張機能の初期化
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    babel.init_app(app) # Babelの初期化
    mail.init_app(app)
    
    # ログインマネージャーの設定
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'このページにアクセスするにはログインしてください。'
    login_manager.login_message_category = 'info'

    # User Loader の設定
    from app.models import User 
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, user_id)

    # ロギングの設定
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/akiomi_blog.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        # stdout へのロギング設定 (Gunicorn などでコンソール出力を見るため)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler) 
        app.logger.setLevel(logging.INFO) 
        app.logger.info('Akiomi Blog startup')

    # コンテキストプロセッサ: 全てのテンプレートで 'current_year' を利用可能にする
    @app.context_processor
    def inject_globals():
        return dict(current_year=datetime.now(pytz.utc).year)

    # Babel: リクエストごとに現在の言語を設定 (必要であればコメント解除して実装)
    # @babel.localeselector 
    # def get_locale():
    #     # ユーザーのロケール設定、またはリクエストヘッダーから取得
    #     # ここではシンプルに 'ja' を返す例
    #     return 'ja'

    # MarkdownをHTMLに変換するJinja2フィルターを登録
    app.jinja_env.filters['markdown'] = lambda text: markdown.markdown( 
        text,
        extensions=[
            'fenced_code',      
            'tables',           
            'nl2br',            
            'sane_lists',       
            'codehilite',       
            'extra',            
        ]
    )

    # 各種ブループリントの登録
    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth') 
    app.register_blueprint(public_posts_bp) 
    app.register_blueprint(blog_admin_bp, url_prefix='/admin')
    

    # 静的ファイル配信のためのカスタムエンドポイント (uploadsフォルダ用)
    @app.route('/uploads/images/<path:filename>')
    def serve_uploaded_images(filename): 
        return send_from_directory(current_app.config['UPLOAD_IMAGES_DIR'], filename) 

    @app.route('/uploads/thumbnails/<path:filename>')
    def serve_uploaded_thumbnails(filename): 
        return send_from_directory(current_app.config['UPLOAD_THUMBNAILS_DIR'], filename) 


    # エラーハンドリング (例: 404 Not Found)
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # CLI コマンドの登録
    from app import cli 
    app.cli.add_command(cli.init) 

    # URLマップのデバッグ出力 (アプリケーションコンテキスト内で実行されるようにする)
    with app.app_context():
        print("\n--- Flask URL Map ---")
        for rule in app.url_map.iter_rules():
            print(f"Endpoint: {rule.endpoint}, Methods: {rule.methods}, Rule: {rule.rule}")
        print("---------------------\n")
    
        # データベーステーブルの作成 (開発時に便利ですが、本番環境では migrate コマンドを使用すべきです)
        db.create_all() 

    return app
