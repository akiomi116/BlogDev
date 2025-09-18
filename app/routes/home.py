# F:\dev\BrogDev\app\routes\home.py

from flask import Blueprint, render_template, current_app, url_for, redirect, flash, request, abort
from app.models import Post, Category, Tag, Comment, Image
from app.extensions import db
from flask_login import current_user # current_user を使用するためにインポートを確認
from app.forms import CommentForm, DeleteForm
import logging
from datetime import datetime
import pytz # datetime.now() にタイムゾーン情報を付与するため

logger = logging.getLogger(__name__)

# ブループリントの定義
home_bp = Blueprint('home', __name__)

# ホームページ（最新の投稿を表示）
@home_bp.route('/')
@home_bp.route('/index')
def index():
    
    #logger.debug("DEBUG(home): index route accessed.")
    page = request.args.get('page', 1, type=int)
    posts_pagination = Post.query.filter_by(is_published=True).order_by(Post.created_at.desc()).paginate(
        page=page, per_page=current_app.config.get('POSTS_PER_PAGE', 10), error_out=False
    )
    posts = posts_pagination.items 
    
    csrf_form = DeleteForm()
    
    next_url = url_for('home.index', page=posts_pagination.next_num) if posts_pagination.has_next else None
    prev_url = url_for('home.index', page=posts_pagination.prev_num) if posts_pagination.has_prev else None
    
    current_year = datetime.now(pytz.utc).year 
    
    return render_template('home/index.html', 
                           posts=posts, 
                           posts_pagination=posts_pagination, 
                           title='ホーム',
                           next_url=next_url,
                           prev_url=prev_url,
                           csrf_form=csrf_form,
                           current_year=current_year)

# 投稿詳細ページ
@home_bp.route('/post/<uuid:post_id>', methods=['GET', 'POST'])
def post_detail(post_id):
    #logger.debug(f"DEBUG(home): Accessed post detail for post_id: {post_id}")
    post = db.session.get(Post, post_id)
    if post is None or not post.is_published: 
        current_app.logger.warning(f"Attempted to access non-existent or unpublished post with ID: {post_id}")
        abort(404)
    
    comment_form = CommentForm()
    delete_form = DeleteForm() 

    if request.method == 'POST':
        #current_app.logger.debug(f"DEBUG: POST request received for post_id: {post_id}")
        #current_app.logger.debug(f"DEBUG: Form data: {request.form}")
        #current_app.logger.debug(f"DEBUG: current_user.is_authenticated: {current_user.is_authenticated}")

        if not current_user.is_authenticated:
            flash('コメントを投稿するにはログインが必要です。', 'danger')
            current_app.logger.warning("WARNING: Unauthenticated user attempted to post comment.")
            return redirect(url_for('security.login', next=request.url))

        if comment_form.validate_on_submit():
            #current_app.logger.debug("DEBUG: Comment form validation successful.")
            try:
                comment = Comment(
                    body=comment_form.body.data,
                    author_name=current_user.username,  # Use logged-in user's name
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
                # ここでreturnを追加
                return render_template(
                    'home/post_detail.html',
                    post=post,
                    comments=comments,
                    comment_form=comment_form,
                    delete_form=delete_form,
                    current_year=current_year
                )
        else:
            current_app.logger.warning(f"WARNING: Comment form validation failed. Errors: {comment_form.errors}")
            for field, errors in comment_form.errors.items():
                for error in errors:
                    flash(f'フォームエラー - {field}: {error}', 'danger')

    comments = Comment.query.filter_by(post_id=post.id, is_approved=True).order_by(Comment.created_at.desc()).all()
    
    current_year = datetime.now(pytz.utc).year 
    
    return render_template('home/post_detail.html', 
                           post=post, 
                           comments=comments, 
                           comment_form=comment_form, 
                           delete_form=delete_form, 
                           current_year=current_year)


# コメント削除エンドポイント (CSRF保護あり)
@home_bp.route('/post/<uuid:post_id>/comment/<uuid:comment_id>/delete', methods=['POST'])
# ★★★ 修正: このデコレータ行を削除 ★★★
# @current_app.logger.info("Function delete_comment called.") # デバッグログ
def delete_comment(post_id, comment_id):
    # 関数が呼び出された時にログを記録する
    current_app.logger.info("Function delete_comment called.") 

    delete_form = DeleteForm()
    if delete_form.validate_on_submit():
        comment_to_delete = db.session.get(Comment, comment_id)
        if comment_to_delete and comment_to_delete.post_id == post_id:
            db.session.delete(comment_to_delete)
            db.session.commit()
            flash('コメントが削除されました。', 'success')
        else:
            flash('コメントが見つからないか、削除できませんでした。', 'danger')
        return redirect(url_for('home.post_detail', post_id=post_id))
    flash('無効なリクエストです。', 'danger')
    return redirect(url_for('home.post_detail', post_id=post_id))

# カテゴリ別記事一覧
@home_bp.route('/category/<uuid:category_id>')
def posts_by_category(category_id):
    category = db.session.get(Category, category_id) 
    if category is None:
        flash('カテゴリが見つかりません。', 'danger')
        abort(404) 

    page = request.args.get('page', 1, type=int)
    posts_pagination = Post.query.filter_by(category=category, is_published=True).order_by(Post.created_at.desc()).paginate(
        page=page, per_page=current_app.config.get('POSTS_PER_PAGE', 10), error_out=False
    )
    posts = posts_pagination.items

    next_url = url_for('home.posts_by_category', category_id=category.id, page=posts_pagination.next_num) if posts_pagination.has_next else None
    prev_url = url_for('home.posts_by_category', category_id=category.id, page=posts_pagination.prev_num) if posts_pagination.has_prev else None

    csrf_form = DeleteForm()

    current_year = datetime.now(pytz.utc).year 

    return render_template('home/posts_by_category.html', 
                           category=category, 
                           posts=posts,
                           posts_pagination=posts_pagination, 
                           next_url=next_url,
                           prev_url=prev_url,
                           csrf_form=csrf_form, 
                           current_year=current_year)

# タグ別記事一覧
@home_bp.route('/tag/<uuid:tag_id>')
def posts_by_tag(tag_id):
    tag = db.session.get(Tag, tag_id)
    if tag is None:
        flash('タグが見つかりません。', 'danger')
        abort(404) 

    page = request.args.get('page', 1, type=int)
    posts_pagination = tag.posts.filter(Post.is_published==True).order_by(Post.created_at.desc()).paginate(
        page=page, per_page=current_app.config.get('POSTS_PER_PAGE', 10), error_out=False
    )
    posts = posts_pagination.items
    
    next_url = url_for('home.posts_by_tag', tag_id=tag.id, page=posts_pagination.next_num) if posts_pagination.has_next else None
    prev_url = url_for('home.posts_by_tag', tag_id=tag.id, page=posts_pagination.prev_num) if posts_pagination.has_prev else None

    csrf_form = DeleteForm()

    current_year = datetime.now(pytz.utc).year
    
    return render_template('home/posts_by_tag.html', 
                           tag=tag, 
                           posts=posts,
                           posts_pagination=posts_pagination, 
                           next_url=next_url,
                           prev_url=prev_url,
                           csrf_form=csrf_form, 
                           current_year=current_year)

# 検索結果ページ
@home_bp.route('/search')
def search_results():
    query = request.args.get('query', '')
    page = request.args.get('page', 1, type=int)

    if query:
        posts_query = Post.query.filter(
            (Post.title.ilike(f'%{query}%')) | (Post.body.ilike(f'%{query}%')),
            Post.is_published==True 
        ).order_by(Post.created_at.desc())
        
        posts_pagination = posts_query.paginate(
            page=page, per_page=current_app.config.get('POSTS_PER_PAGE', 10), error_out=False
        )
        posts = posts_pagination.items
        
        next_url = url_for('home.search_results', query=query, page=posts_pagination.next_num) if posts_pagination.has_next else None
        prev_url = url_for('home.search_results', query=query, page=posts_pagination.prev_num) if posts_pagination.has_prev else None

        flash(f"「{query}」の検索結果", 'info')
    else:
        posts = []
        posts_pagination = None 
        next_url = None
        prev_url = None
        flash('検索キーワードが入力されていません。', 'warning')
    
    csrf_form = DeleteForm() 
    current_year = datetime.now(pytz.utc).year
    
    return render_template('home/search_results.html', 
                           posts=posts, 
                           posts_pagination=posts_pagination, 
                           query=query, 
                           next_url=next_url,
                           prev_url=prev_url,
                           csrf_form=csrf_form, 
                           current_year=current_year)

# その他の共通処理（例: エラーハンドリング）
@home_bp.app_errorhandler(403)
def forbidden(e):
    current_app.logger.warning(f"ACCESS_DENIED: User {current_user.id if current_user.is_authenticated else 'anonymous'} attempted to access {request.path} without sufficient role.")
    return render_template('errors/403.html', current_year=datetime.now(pytz.utc).year), 403

@home_bp.app_errorhandler(404)
def page_not_found(e):
    current_app.logger.warning(f"PAGE_NOT_FOUND: {request.path}")
    return render_template('errors/404.html', current_year=datetime.now(pytz.utc).year), 404

@home_bp.app_errorhandler(500)
def internal_server_error(e):
    current_app.logger.exception(f"INTERNAL_SERVER_ERROR: {e}")
    return render_template('errors/500.html', current_year=datetime.now(pytz.utc).year), 500
