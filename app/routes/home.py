# F:\dev\BrogDev\app\routes\home.py

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user # current_user を使用するためにインポートを確認
from app.models import Post, Comment # Comment モデルを追加
from app.extensions import db
from app.forms import CommentForm # CommentForm のインポートを確認
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

home_bp = Blueprint('home', __name__)

# ホームページ（最新の投稿を表示）
@home_bp.route('/')
@home_bp.route('/index')
def index():
    logger.debug("DEBUG(home): index route accessed.")
    posts = Post.query.order_by(Post.created_at.desc()).all()
    # current_year をテンプレートに渡す (フッター用)
    current_year = datetime.now().year
    return render_template('home/index.html', posts=posts, current_year=current_year)

# 投稿詳細ページ
@home_bp.route('/post/<uuid:post_id>', methods=['GET', 'POST'])
def post_detail(post_id):
    logger.debug(f"DEBUG(home): Accessed post detail for post_id: {post_id}")
    post = db.session.get(Post, post_id)
    if post is None:
        current_app.logger.warning(f"Attempted to access non-existent post with ID: {post_id}")
        abort(404)
    
    comments = Comment.query.options(db.joinedload(Comment.comment_author)).filter_by(post_id=post.id).all()
    
    comment_form = CommentForm()

    if request.method == 'POST': # validate_on_submit() の前にまずPOSTリクエストであることを確認
        current_app.logger.debug(f"DEBUG: POST request received for post_id: {post_id}")
        current_app.logger.debug(f"DEBUG: Form data: {request.form}")
        current_app.logger.debug(f"DEBUG: current_user.is_authenticated: {current_user.is_authenticated}")

        if not current_user.is_authenticated:
            flash('コメントを投稿するにはログインが必要です。', 'danger')
            current_app.logger.warning("WARNING: Unauthenticated user attempted to post comment.")
            return redirect(url_for('auth.login', next=request.url))

        if comment_form.validate_on_submit():
            current_app.logger.debug("DEBUG: Comment form validation successful.")
            try:
                comment = Comment(
                    body=comment_form.body.data,
                    user_id=current_user.id,
                    post_id=post.id,
                    is_approved=False
                )
                db.session.add(comment)
                db.session.commit()
                flash('コメントが正常に投稿されました。承認後表示されます。', 'success')
                current_app.logger.info(f"User {current_user.username} (ID: {current_user.id}) posted a comment on post {post_id}. Content: {comment_form.body.data[:50]}...")
                return redirect(url_for('home.post_detail', post_id=post.id))
            except Exception as e:
                db.session.rollback()
                flash(f'コメントの投稿中にエラーが発生しました: {e}', 'danger')
                current_app.logger.error(f"Error posting comment for post {post_id} by user {current_user.id}: {e}", exc_info=True)
        else:
            current_app.logger.warning(f"WARNING: Comment form validation failed. Errors: {comment_form.errors}")
            # フォームのバリデーションエラーをflashメッセージで表示すると分かりやすい
            for field, errors in comment_form.errors.items():
                for error in errors:
                    flash(f'フォームエラー - {field}: {error}', 'danger')

    # GET リクエストまたは POST 失敗時の処理
    # 承認済みのコメントのみ表示
    comments = Comment.query.filter_by(post_id=post.id, is_approved=True).order_by(Comment.created_at.desc()).all()
    
    # current_year をテンプレートに渡す (フッター用)
    current_year = datetime.now().year
    
    return render_template('home/post_detail.html', post=post, comments=comments, comment_form=comment_form, current_year=current_year)


# カテゴリ別投稿一覧
@home_bp.route('/category/<uuid:category_id>')
def posts_by_category(category_id):
    category = db.session.get(Category, category_id)
    if category is None:
        abort(404)
    # 関連する投稿をフィルタリング
    posts = Post.query.filter_by(category_id=category_id).order_by(Post.created_at.desc()).all()
    current_year = datetime.now().year
    return render_template('home/category_posts.html', category=category, posts=posts, current_year=current_year)

# タグ別投稿一覧
@home_bp.route('/tag/<uuid:tag_id>')
def posts_by_tag(tag_id):
    tag = db.session.get(Tag, tag_id)
    if tag is None:
        abort(404)
    # タグと関連する投稿を取得
    posts = tag.posts.order_by(Post.created_at.desc()).all() # Tagモデルに`posts`リレーションがあると仮定
    current_year = datetime.now().year
    return render_template('home/tag_posts.html', tag=tag, posts=posts, current_year=current_year)

# 検索結果ページ
@home_bp.route('/search')
def search_results():
    query = request.args.get('query', '')
    if query:
        # タイトルまたはコンテンツにクエリが含まれる投稿を検索
        posts = Post.query.filter(
            (Post.title.ilike(f'%{query}%')) | (Post.body.ilike(f'%{query}%'))
        ).order_by(Post.created_at.desc()).all()
        flash(f"「{query}」の検索結果", 'info')
    else:
        posts = []
        flash('検索キーワードが入力されていません。', 'warning')
    current_year = datetime.now().year
    return render_template('home/search_results.html', posts=posts, query=query, current_year=current_year)

# その他の共通処理（例: エラーハンドリング）
# 403 Forbidden エラーハンドリング
@home_bp.app_errorhandler(403)
def forbidden(e):
    current_app.logger.warning(f"ACCESS_DENIED: User {current_user.id if current_user.is_authenticated else 'anonymous'} ({current_user.role.name if current_user.is_authenticated and hasattr(current_user, 'role') and current_user.role else 'no role'}) attempted to access {request.path} without sufficient role.")
    return render_template('errors/403.html', current_year=datetime.now().year), 403

# 404 Not Found エラーハンドリング
@home_bp.app_errorhandler(404)
def page_not_found(e):
    current_app.logger.warning(f"PAGE_NOT_FOUND: {request.path}")
    return render_template('errors/404.html', current_year=datetime.now().year), 404

# 500 Internal Server Error エラーハンドリング
@home_bp.app_errorhandler(500)
def internal_server_error(e):
    current_app.logger.exception(f"INTERNAL_SERVER_ERROR: {e}")
    return render_template('errors/500.html', current_year=datetime.now().year), 500