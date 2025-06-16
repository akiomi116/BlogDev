from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_moment import Moment
from flask_babel import Babel
from flask_mail import Mail

# 各拡張機能のインスタンスを生成
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()
moment = Moment()
babel = Babel()
mail = Mail()
