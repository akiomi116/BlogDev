# F:\dev\BrogDev\app\routes\categories.py

from flask import Blueprint, render_template, abort
from app.models import Category, Post # Category と Post モデルをインポート
import uuid # UUID を使用する場合に備えてインポート

# categories_bp ブループリントを定義
# このブループリントは公開サイトのカテゴリ関連機能に特化します。
# 管理機能に関する url_prefix や template_folder は設定しません。
categories_bp = Blueprint('categories', __name__)

# カテゴリごとの投稿一覧を表示するルート
# URLルールは /category/<uuid:category_id> とし、UUID型のIDを受け取ります。
@categories_bp.route('/category/<uuid:category_id>')
def posts_by_category(category_id):
    # UUIDでカテゴリを検索。見つからなければ404エラーを返す。
    category = Category.query.filter_by(id=category_id).first_or_404()

    # そのカテゴリに属する公開済み投稿を取得
    # Postモデルに is_published フィールドがある場合を想定
    posts = Post.query.filter_by(category_id=category.id, is_published=True).order_by(Post.timestamp.desc()).all()

    # テンプレートをレンダリング。公開サイト用のテンプレートパスを指定。
    # 例: app/templates/home/posts_by_category.html
    return render_template('home/posts_by_category.html', category=category, posts=posts)

# その他、公開サイトで必要なカテゴリ関連のルートがあればここに追加します。
# 例: すべてのカテゴリを一覧表示するルートなど

# 注意:
# ここには、以前の `flask routes` 出力で見られた管理機能（/admin/categories/categories/...）
# に関連するルートは一切記述しません。それらは `app/admin/routes.py` に集約されています。