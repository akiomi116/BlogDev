# F:\dev\BrogDev\app\routes\posts.py

from flask import Blueprint, render_template, url_for, abort
from app.extensions import db
from app.models import Post, Category, Tag, Image # Post, Category, Tag, Image をインポート
import os
import logging

logger = logging.getLogger(__name__)

# public_posts Blueprint の定義
public_posts_bp = Blueprint(
    'public_posts', # ブループリント名
    __name__,
    url_prefix='/posts', # URLプレフィックスを /posts に設定 (例: /posts/list, /posts/category/...)
    # Blueprintのtemplate_folderは、そのBlueprintが定義されているファイルの相対パスで指定
    # '..' を使って 'app' ディレクトリに上がり、そこから 'templates/posts' を指定
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates', 'posts')
)

# --- 公開されている記事一覧を表示するルート ---
@public_posts_bp.route('/') # /posts/ にアクセスした場合
@public_posts_bp.route('/list') # /posts/list にアクセスした場合 (より明確なパス)
def list_posts():
    """公開されている投稿の一覧を表示します。"""
    # is_published=True で公開済みの投稿のみを取得
    posts = Post.query.filter_by(is_published=True).order_by(Post.created_at.desc()).all()
    logger.debug("DEBUG: Public posts list accessed.")
    # render_templateのパスはBlueprintのtemplate_folderからの相対パスになります
    return render_template('list_public.html', posts=posts, title="記事一覧")


# 例: カテゴリごとの記事一覧を表示するルート (将来的に追加する場合)
# @public_posts_bp.route('/category/<uuid:category_id>')
# def posts_by_category(category_id):
#     category = Category.query.get_or_404(category_id)
#     posts = Post.query.filter_by(category_id=category_id, is_published=True).order_by(Post.created_at.desc()).all()
#     return render_template('posts_by_category.html', category=category, posts=posts)

# 例: タグごとの記事一覧を表示するルート (将来的に追加する場合)
# @public_posts_bp.route('/tag/<uuid:tag_id>')
# def posts_by_tag(tag_id):
#     tag = Tag.query.get_or_404(tag_id)
#     posts = db.session.query(Post).filter(Post.tags.any(id=tag_id), Post.is_published==True).order_by(Post.created_at.desc()).all()
#     return render_template('posts_by_tag.html', tag=tag, posts=posts)

# 注意: `post_detail` ルートは `app/routes/home.py` に移動され、公開側の詳細表示はそちらで一元管理されます。