# F:\dev\BrogDev\app\admin\__init__.py

from flask import Blueprint

# ブループリントインスタンスを作成
bp = Blueprint('blog_admin_bp', __name__, template_folder='templates', static_folder='static', url_prefix='/admin')

# ★重要★ このインポートは、bpが定義された後に行う必要があります。二重登録を避けるためです。
from . import routes
