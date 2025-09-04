from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_moment import Moment
from flask_babel import Babel
from flask_mail import Mail

from flask_security import Security, SQLAlchemyUserDatastore
from flask_principal import Principal

# 各拡張機能のインスタンスを生成
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
moment = Moment()
babel = Babel()
mail = Mail()

security = Security()
principals = Principal()

# Datastoreはアプリ初期化時にモデルを渡して生成
user_datastore = None


def init_security(app, user_model, role_model):
    """
    FlaskアプリにSecurityを正しく初期化するための関数。
    パスワードフィールドが password_hash であることを明示する。
    """
    global user_datastore
    user_datastore = SQLAlchemyUserDatastore(
        db, user_model, role_model, password_field='password_hash'
    )
    security.init_app(app, datastore=user_datastore)
    principals.init_app(app)
