from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_moment import Moment
from flask_babel import Babel
from flask_mail import Mail
from flask_admin import Admin  # Flask-Admin をインポート

# 各拡張機能のインスタンスを生成
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()
moment = Moment()
babel = Babel()
mail = Mail()
# Flask-Admin のインスタンスを生成。nameは管理画面のタイトル、template_modeはBootstrapのバージョン指定
admin = Admin(name='ブログ管理', template_mode='bootstrap4')