# F:\dev\BrogDev\app\admin\routes.py

import os
import uuid
from flask import render_template, url_for, flash, redirect, request, current_app, Blueprint
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func
from PIL import Image as PilImage # PillowのImageクラスを別名でインポート

from app import db
from app import models 
from app.models import User, Role, Post, Category, Tag, Image, Comment
from app.admin.forms import (
    UserForm, RoleForm, PostForm, CategoryForm, TagForm,
    ImageUploadForm, BulkImageUploadForm, CommentForm
)

#from flask_admin.contrib.sqla import ModelView
#from flask_admin import Admin
from . import bp

# Category のカスタムビューを定義 (このファイル内で直接)
# ★ここに記述して問題ありません★
#class CategoryAdminView(ModelView):
#    can_create = True
#    can_edit = True
#    can_delete = True

# Adminインスタンスの初期化
#admin = Admin(name='ブログ管理', template_mode='bootstrap4')
#admin.init_app(bp) # bp は admin_bp のこと

# 管理画面のビューを登録
# ... (他のビューの登録) ...
#admin.add_view(CategoryAdminView(models.Category, db.session, name='カテゴリ管理', category='ブログ管理', endpoint='category_admin')) # エンドポイントを明示的に指定
#admin.add_view(CategoryAdminView(Category, db.session, name='カテゴリ管理', category='ブログ管理'))
# ... (残りのビューの登録) ...

# admin_bp ブループリントの登録は、このファイルの一番下、
# または別のファイル（app/__init__.py）で行われるはずなので、
# CategoryAdminView の定義がその登録よりも前であればOKです。
# （実際、このファイル自体が admin_bp のルート定義を行っているため、
#   このファイル内のどこに書いても admin_bp の実体（Blueprintオブジェクト）よりも
#   先に評価されることはありませんので心配いりません。）



# ブループリントの登録（通常は__init__.pyで行うが、ここでは省略）
admin_bp = Blueprint('blog_admin_bp', __name__, url_prefix='/admin',
                     template_folder='templates',
                     static_folder='static')

# 定数
THUMBNAIL_SIZE = (200, 200) # サムネイルのサイズを定義

# 許可されるファイル拡張子
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- ダッシュボード ---
@admin_bp.route('/')
@admin_bp.route('/index')
@login_required
def index():
    if not current_user.is_admin:
        flash('管理者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    
    total_users = User.query.count()
    total_posts = Post.query.count()
    total_categories = Category.query.count()
    total_tags = Tag.query.count()
    total_images = Image.query.count()
    
    # 承認待ちコメントの数を取得
    pending_comments_count = Comment.query.filter_by(is_approved=False).count()

    # 最近の活動（例: 最新の投稿、コメントなど）
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    recent_comments = Comment.query.order_by(Comment.created_at.desc()).limit(5).all()
    
    return render_template('admin/index.html',
                           total_users=total_users,
                           total_posts=total_posts,
                           total_categories=total_categories,
                           total_tags=total_tags,
                           total_images=total_images,
                           pending_comments_count=pending_comments_count,
                           recent_posts=recent_posts,
                           recent_comments=recent_comments)

# --- ユーザー管理 ---
@admin_bp.route('/users')
@login_required
def manage_users():
    if not current_user.is_admin:
        flash('管理者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    users = User.query.all()
    return render_template('users/manage_users.html', users=users)

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        flash('管理者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    
    form = UserForm() 
    # form.roles.choices は forms.py の UserForm.__init__ で設定済みなので不要
    # form.roles.choices = [(role.id, role.name) for role in Role.query.all()] # この行は削除またはコメントアウト

    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        
        # ロールの設定 (単一ロールの場合)
        # form.role_id.data には選択されたロールのID（文字列）が入っている
        # user.role_id に直接設定
        user.role_id = form.role_id.data 
        # selected_roles = Role.query.filter(Role.id.in_(form.roles.data)).all() # この行は削除
        # user.roles.extend(selected_roles) # この行は削除

        db.session.add(user)
        db.session.commit()
        flash('ユーザーが追加されました。', 'success')
        return redirect(url_for('admin.manage_users'))
    return render_template('users/add_user.html', form=form)


@admin_bp.route('/users/<uuid:user_id>/change_role', methods=['GET', 'POST'])
@login_required
def change_user_role(user_id):
    if not current_user.is_admin:
        flash('管理者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    
    user = User.query.get_or_404(user_id)
    form = RoleForm(obj=user) # ユーザーに割り当てられているロールをフォームに事前入力
    
    # ロールの選択肢を設定
    form.role.choices = [(role.id, role.name) for role in Role.query.all()]
    
    if form.validate_on_submit():
        # 現在のロールを全てクリア
        user.roles.clear()
        
        # 新しいロールを追加
        selected_role_id = form.role.data
        if selected_role_id:
            role = Role.query.get(selected_role_id)
            if role:
                user.roles.append(role)
        
        db.session.commit()
        flash(f'ユーザー「{user.username}」のロールが変更されました。', 'success')
        return redirect(url_for('admin.manage_users'))
    
    # フォームの初期値を設定 (GETリクエスト時)
    # user.roles はリストなので、最初のロールのIDを初期値とする
    if user.roles:
        form.role.data = user.roles[0].id
    
    return render_template('users/change_user_role.html', form=form, user=user)


@admin_bp.route('/users/edit/<uuid:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin:
        flash('管理者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    user = User.query.get_or_404(user_id)
    
    # UserForm の初期化時に original_username や original_email は UserForm の __init__ や validate_... メソッドで
    # self.obj を使って既存オブジェクトを参照するようにしているので、この引数は不要です。
    # よって、forms.py のUserFormの__init__とvalidate_username/emailメソッドはobjを直接使う形に修正します。
    # routes.py側はシンプルに obj=user を渡すのみでOKです。
    form = UserForm(obj=user) # original_username, original_email は削除

    # パスワードのバリデータはforms.pyのUserFormで既にOptional()を設定済み
    # form.password.validators = [Optional(), Length(min=6)] # この行は不要（フォーム定義で設定済み）
    # form.confirm_password.validators = [Optional(), EqualTo('password', message='パスワードが一致しません。')] # この行も不要

    # ロールの選択肢は forms.py の UserForm.__init__ で設定済みなので不要
    # form.roles.choices = [(role.id, role.name) for role in Role.query.all()] # この行は削除またはコメントアウト
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        if form.password.data: # パスワードが入力された場合のみ更新
            user.set_password(form.password.data)
        
        # ロールの更新 (単一ロールの場合)
        # form.role_id.data には選択されたロールのID（文字列）が入っている
        user.role_id = form.role_id.data # user.role_id を直接更新
        # user.roles.clear() # この行は削除
        # selected_roles = Role.query.filter(Role.id.in_(form.roles.data)).all() # この行は削除
        # user.roles.extend(selected_roles) # この行は削除

        db.session.commit()
        flash('ユーザー情報が更新されました。', 'success')
        return redirect(url_for('admin.manage_users'))
    elif request.method == 'GET':
        # GETリクエストの場合、既存のロールIDをフォームの選択肢にセット
        if user.role: # user.role が存在する場合のみ
            form.role_id.data = str(user.role.id) # UUIDを文字列に変換してセット
    return render_template('users/edit_user.html', form=form, user=user)

@admin_bp.route('/users/delete/<uuid:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash('管理者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    user = User.query.get_or_404(user_id)
    # ユーザーが所有する投稿、コメント、画像の削除なども必要に応じて追加
    
    # 例: ユーザーが投稿した記事を削除
    for post in user.posts:
        # 投稿に関連するコメントも削除
        for comment in post.comments:
            db.session.delete(comment)
        # 投稿に関連する画像とのリレーションも削除 (post_idがNULLになるようにするか、画像を削除)
        # 画像を削除する場合は、ファイルシステムからも削除するロジックが必要
        for image in post.images:
             # Imageレコードを削除するが、ファイルシステム上のファイルは残す（共有されている可能性を考慮）
             # または、ファイルシステムからも削除する場合は以下の行を有効にする
             # if os.path.exists(image.filepath):
             #     os.remove(image.filepath)
             # if image.thumbnail_filepath and os.path.exists(image.thumbnail_filepath):
             #     os.remove(image.thumbnail_filepath)
            db.session.delete(image) # Imageレコード自体は削除
        db.session.delete(post)

    # ユーザーがアップロードした画像を削除 (post_idがnullの画像など)
    for image in user.uploaded_images: # 'uploaded_images' はUserモデルのbackref名
        # 画像ファイルを実際に削除するロジック (必要であれば)
        if os.path.exists(image.filepath):
            os.remove(image.filepath)
        if image.thumbnail_filepath and os.path.exists(image.thumbnail_filepath):
            os.remove(image.thumbnail_filepath)
        db.session.delete(image)

    # ユーザーが作成したコメントを削除
    for comment in user.comments:
        db.session.delete(comment)
    
    db.session.delete(user)
    db.session.commit()
    flash('ユーザーが削除されました。', 'success')
    return redirect(url_for('admin.manage_users'))

# --- ロール管理 ---
@admin_bp.route('/roles')
@login_required
def manage_roles():
    if not current_user.is_admin:
        flash('管理者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    roles = Role.query.all()
    return render_template('roles/manage_roles.html', roles=roles)

@admin_bp.route('/roles/new', methods=['GET', 'POST'])
@login_required
def new_role():
    if not current_user.is_admin:
        flash('管理者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    form = RoleForm() # 新規作成なので original_name は不要
    if form.validate_on_submit():
        role = Role(name=form.name.data)
        db.session.add(role)
        db.session.commit()
        flash('新しいロールが追加されました。', 'success')
        return redirect(url_for('admin.manage_roles'))
    return render_template('roles/new_role.html', form=form)

@admin_bp.route('/roles/edit/<uuid:role_id>', methods=['GET', 'POST'])
@login_required
def edit_role(role_id):
    if not current_user.is_admin:
        flash('管理者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    role = Role.query.get_or_404(role_id)
    form = RoleForm(obj=role, original_name=role.name) # フォームの初期化時に現在のロール名を渡す
    if form.validate_on_submit():
        role.name = form.name.data
        db.session.commit()
        flash('ロール名が更新されました。', 'success')
        return redirect(url_for('admin.manage_roles'))
    return render_template('roles/edit_role.html', form=form, role=role)

@admin_bp.route('/roles/delete/<uuid:role_id>', methods=['POST'])
@login_required
def delete_role(role_id):
    if not current_user.is_admin:
        flash('管理者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    role = Role.query.get_or_404(role_id)
    
    # このロールに属するユーザーからロールを解除する（または別のデフォルトロールに割り当てる）
    # 例: ロールを解除する
    for user in role.users: # Userモデルのbackref名が'users'の場合
        user.roles.remove(role)
    db.session.delete(role)
    db.session.commit()
    flash('ロールが削除されました。', 'success')
    return redirect(url_for('admin.manage_roles'))

# --- 投稿管理 ---
@admin_bp.route('/posts')
@login_required
def list_posts():
    if not current_user.is_admin and not current_user.is_editor:
        flash('管理者または編集者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    posts = Post.query.all()
    return render_template('posts/list_posts.html', posts=posts)

@admin_bp.route('/posts/new', methods=['GET', 'POST'])
@login_required
def new_post():
    # 権限チェック (is_adminがAdminロール名と一致していることを前提)
    if not current_user.is_admin and not current_user.has_role('Poster'): # Posterロールも許可する場合
        flash('管理者または投稿者権限が必要です。', 'warning')
        return redirect(url_for('home.index'))

    form = PostForm()

    if form.validate_on_submit():
        main_image_obj = None # メインとなるImageオブジェクトを格納する変数

        # ① 新しい画像がアップロードされた場合
        if form.main_image_file.data:
            uploaded_file = form.main_image_file.data
            # ファイル名を安全にし、保存パスを決定
            # 例: アップロードフォルダは app/static/uploads/posts/ のように設定
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'posts')
            os.makedirs(upload_folder, exist_ok=True) # フォルダが存在しない場合は作成
            
            # ファイル名生成（UUIDなどを使ってユニークにするのがベスト）
            import uuid
            unique_filename = str(uuid.uuid4()) + os.path.splitext(uploaded_file.filename)[1]
            filepath = os.path.join(upload_folder, unique_filename)
            
            uploaded_file.save(filepath) # ファイルを保存

            # Imageモデルのインスタンスを作成し、DBに保存
            main_image_obj = Image(
                filename=unique_filename,
                path=f'/static/uploads/posts/{unique_filename}', # DBに保存するパスはURLとしてアクセス可能なパス
                user_id=current_user.id # 誰がアップロードしたか
            )
            db.session.add(main_image_obj)
            db.session.flush() # IDを生成するためにflush（commit前）

        # ② 新しい画像がなく、既存の画像が選択された場合
        elif form.main_image.data:
            main_image_id = form.main_image.data
            main_image_obj = Image.query.get(main_image_id)
            if not main_image_obj:
                flash('選択されたメイン画像が見つかりませんでした。', 'danger')
                return render_template('posts/new_post.html', form=form, title='新規投稿')

        # 新しい投稿を作成
        post = Post(
            title=form.title.data,
            body=form.body.data,
            is_published=form.is_published.data
        )

        post.author = current_user
        post.user_id = current_user.id

        db.session.add(post) 

        # メイン画像を設定
        if main_image_obj:
            post.main_image = main_image_obj # Postモデルにmain_imageリレーションがある場合

        # カテゴリを設定
        if form.category.data:
            category = Category.query.get(form.category.data)
            if category:
                post.category = category

        # タグを設定 (多対多のリレーションシップ)
        post.tags.clear() # 既存のタグをクリア
        if form.tags.data:
            for tag_id in form.tags.data:
                tag = Tag.query.get(tag_id)
                if tag:
                    post.tags.append(tag)
        
        # 追加画像を設定 (多対多のリレーションシップ)
        # Postモデルに additional_images というリレーションシップがあることを前提
        post.additional_images.clear()
        if form.additional_images.data:
            for img_id in form.additional_images.data:
                img = Image.query.get(img_id)
                if img:
                    post.additional_images.append(img)


        
        db.session.commit()
        flash('新しい投稿が作成されました！', 'success')
        return redirect(url_for('admin.posts'))

    # GETリクエストまたはバリデーションエラーの場合
    return render_template('posts/new_post.html', form=form, title='新規投稿')


@admin_bp.route('/posts/edit/<uuid:post_id>', methods=['GET', 'POST']) # UUID型のIDを受け取る
@login_required
def edit_post(post_id):
    # 権限チェック (is_adminがAdminロール名と一致していることを前提)
    if not current_user.is_admin and not current_user.has_role('Poster'): # Posterロールも許可する場合
        flash('管理者または投稿者権限が必要です。', 'warning')
        return redirect(url_for('home.index'))

    # 既存の投稿を取得
    post = Post.query.get_or_404(post_id)

    # 投稿の所有者チェック（管理者以外の場合）
    if not current_user.is_admin and post.user_id != current_user.id:
        flash('この投稿を編集する権限がありません。', 'danger')
        return redirect(url_for('admin.posts'))

    form = PostForm()

    if form.validate_on_submit():
        # フォームからデータを受け取り、投稿オブジェクトを更新

        # ① 新しい画像がアップロードされた場合
        if form.main_image_file.data:
            uploaded_file = form.main_image_file.data
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'posts')
            os.makedirs(upload_folder, exist_ok=True)
            
            unique_filename = str(uuid.uuid4()) + os.path.splitext(uploaded_file.filename)[1]
            filepath = os.path.join(upload_folder, unique_filename)
            uploaded_file.save(filepath)

            # 新しいImageモデルのインスタンスを作成し、DBに保存
            main_image_obj = Image(
                filename=unique_filename,
                path=f'/static/uploads/posts/{unique_filename}',
                user_id=current_user.id
            )
            db.session.add(main_image_obj)
            db.session.flush() # IDを生成

            # 既存のメイン画像がある場合、その関連付けを解除（オプション）
            # もし既存の画像を完全に置き換えたいなら、既存のImageオブジェクトをDBから削除することも検討
            # db.session.delete(post.main_image) # 必要に応じて
            
            post.main_image = main_image_obj # Postモデルのmain_imageを新しい画像に設定

        # ② 新しい画像がなく、既存の画像が選択された場合 (または「なし」が選択された場合)
        elif form.main_image.data: # 何か選択されている場合
            main_image_id = form.main_image.data
            if main_image_id == '': # 「なし」が選択された場合
                post.main_image = None # メイン画像を解除
            else:
                main_image_obj = Image.query.get(main_image_id)
                if main_image_obj:
                    post.main_image = main_image_obj # Postモデルのmain_imageを既存の画像に設定
                else:
                    flash('選択された既存のメイン画像が見つかりませんでした。', 'danger')
                    return render_template('posts/edit_post.html', form=form, post=post, title='投稿編集')
        # ③ どちらも選択されていない場合（変更なし）は post.main_image はそのまま

        # その他のフィールドを更新
        post.title = form.title.data
        post.body = form.body.data
        post.is_published = form.is_published.data

        # カテゴリの更新
        if form.category.data:
            category = Category.query.get(form.category.data)
            if category:
                post.category = category
            else: # 選択されたカテゴリが見つからない場合
                post.category = None # またはエラーメッセージ
        else: # カテゴリが選択されていない場合
            post.category = None

        # タグの更新 (多対多のリレーションシップ)
        post.tags.clear() # 既存のタグをクリア
        if form.tags.data:
            for tag_id in form.tags.data:
                tag = Tag.query.get(tag_id)
                if tag:
                    post.tags.append(tag)
        
        # 追加画像の更新 (多対多のリレーションシップ)
        post.additional_images.clear() # 既存の追加画像をクリア
        if form.additional_images.data:
            for img_id in form.additional_images.data:
                img = Image.query.get(img_id)
                if img:
                    post.additional_images.append(img)

        db.session.commit()
        flash('投稿が更新されました！', 'success')
        return redirect(url_for('admin.posts'))

    elif request.method == 'GET':
        # GETリクエストの場合、既存の投稿データをフォームにプリフィル
        form.title.data = post.title
        form.body.data = post.body
        form.is_published.data = post.is_published
        
        # カテゴリのプリフィル
        if post.category:
            form.category.data = str(post.category.id)
        else:
            form.category.data = '' # 'なし' を選択状態にするため

        # メイン画像のプリフィル (SelectField)
        if post.main_image:
            form.main_image.data = str(post.main_image.id)
        else:
            form.main_image.data = '' # 'なし' を選択状態にするため

        # タグのプリフィル (SelectMultipleField)
        form.tags.data = [str(tag.id) for tag in post.tags]
        
        # 追加画像のプリフィル (SelectMultipleField)
        form.additional_images.data = [str(img.id) for img in post.additional_images]

    return render_template('posts/edit_post.html', form=form, post=post, title='投稿編集')

@admin_bp.route('/delete_post/<uuid:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    if not current_user.is_admin and not current_user.is_editor:
        flash('管理者または編集者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    post = Post.query.get_or_404(post_id)
    # 投稿に関連するコメントを削除
    for comment in post.comments:
        db.session.delete(comment)
    
    # 投稿に関連する画像とのリレーションを解除（または画像を削除）
    # ここではリレーションを解除するのみ
    # 画像レコード自体は残し、post_idをNULLにする
    for image in post.images:
        image.post_id = None
        db.session.add(image)

    # メイン画像のリレーションも解除
    if post.main_image:
        post.main_image.is_main_image = False
        db.session.add(post.main_image)

    db.session.delete(post)
    db.session.commit()
    flash('投稿が削除されました。', 'success')
    return redirect(url_for('admin.list_posts'))

@admin_bp.route('/toggle_publish/<uuid:post_id>', methods=['POST'])
@login_required
def toggle_publish(post_id):
    if not current_user.is_admin and not current_user.is_editor:
        flash('管理者または編集者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    post = Post.query.get_or_404(post_id)
    post.is_published = not post.is_published
    db.session.commit()
    flash(f'投稿「{post.title}」の公開状態が{"公開" if post.is_published else "非公開"}に変更されました。', 'success')
    return redirect(url_for('admin.list_posts'))

# --- カテゴリ管理 ---
#@admin_bp.route('/categories')
#@login_required
#def manage_categories():
#    if not current_user.is_admin and not current_user.is_editor:
#        flash('管理者または編集者権限が必要です。', 'danger')
#        return redirect(url_for('home.index'))
#    categories = Category.query.all()
#    return render_template('categories/manage_categories.html', categories=categories)

@admin_bp.route('/categories/new', methods=['GET', 'POST'])
@login_required
def new_category():
    if not current_user.is_admin and not current_user.is_editor:
        flash('管理者または編集者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    form = CategoryForm() # 新規作成なので original_name は不要
    if form.validate_on_submit():
        category = Category(name=form.name.data)
        db.session.add(category)
        db.session.commit()
        flash('新しいカテゴリが追加されました。', 'success')
        return redirect(url_for('admin.manage_categories'))
    return render_template('categories/new_category.html', form=form)

@admin_bp.route('/categories/edit/<uuid:category_id>', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    if not current_user.is_admin and not current_user.is_editor:
        flash('管理者または編集者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    category = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=category, original_name=category.name) # フォームの初期化時に現在のカテゴリ名を渡す
    if form.validate_on_submit():
        category.name = form.name.data
        db.session.commit()
        flash('カテゴリ名が更新されました。', 'success')
        return redirect(url_for('admin.manage_categories'))
    return render_template('categories/edit_category.html', form=form, category=category)

@admin_bp.route('/categories/delete/<uuid:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    if not current_user.is_admin and not current_user.is_editor:
        flash('管理者または編集者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    category = Category.query.get_or_404(category_id)
    # このカテゴリに属する投稿をどうするか？
    # 例: 投稿のカテゴリをNULLにするか、デフォルトカテゴリに割り当てるか、投稿も削除するか
    # ここでは、投稿のカテゴリをNULLにする
    for post in category.posts:
        post.category_id = None # またはデフォルトカテゴリID
        db.session.add(post)

    db.session.delete(category)
    db.session.commit()
    flash('カテゴリが削除されました。', 'success')
    return redirect(url_for('admin.manage_categories'))

# --- タグ管理 ---
@admin_bp.route('/tags')
@login_required
def manage_tags():
    if not current_user.is_admin and not current_user.is_editor:
        flash('管理者または編集者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    tags = Tag.query.all()
    return render_template('tags/manage_tags.html', tags=tags)

@admin_bp.route('/tags/new', methods=['GET', 'POST'])
@login_required
def new_tag():
    if not current_user.is_admin and not current_user.is_editor:
        flash('管理者または編集者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    form = TagForm() # 新規作成なので original_name は不要
    if form.validate_on_submit():
        tag = Tag(name=form.name.data)
        db.session.add(tag)
        db.session.commit()
        flash('新しいタグが追加されました。', 'success')
        return redirect(url_for('admin.manage_tags'))
    return render_template('tags/new_tag.html', form=form)

@admin_bp.route('/tags/edit/<uuid:tag_id>', methods=['GET', 'POST'])
@login_required
def edit_tag(tag_id):
    if not current_user.is_admin and not current_user.is_editor:
        flash('管理者または編集者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    tag = Tag.query.get_or_404(tag_id)
    form = TagForm(obj=tag, original_name=tag.name) # フォームの初期化時に現在のタグ名を渡す
    if form.validate_on_submit():
        tag.name = form.name.data
        db.session.commit()
        flash('タグ名が更新されました。', 'success')
        return redirect(url_for('admin.manage_tags'))
    return render_template('tags/edit_tag.html', form=form, tag=tag)

@admin_bp.route('/tags/delete/<uuid:tag_id>', methods=['POST'])
@login_required
def delete_tag(tag_id):
    if not current_user.is_admin and not current_user.is_editor:
        flash('管理者または編集者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    tag = Tag.query.get_or_404(tag_id)
    
    # このタグに属する投稿からタグを解除する
    # 投稿のtagsリストから該当タグを削除
    for post in tag.posts:
        post.tags.remove(tag)
    
    db.session.delete(tag)
    db.session.commit()
    flash('タグが削除されました。', 'success')
    return redirect(url_for('admin.manage_tags'))


# --- 画像管理 ---
@admin_bp.route('/images')
@login_required
def list_images():
    if not current_user.is_admin and not current_user.is_editor:
        flash('管理者または編集者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    images = Image.query.order_by(Image.uploaded_at.desc()).all()
    # デバッグ用にパスを確認
    # for img in images:
    #     print(f"Image: {img.original_filename}, Thumbnail URL: {img.thumbnail_url}")
    return render_template('images/list_images.html', images=images)


@admin_bp.route('/images/upload', methods=['GET', 'POST'])
@login_required
def upload_image():
    if not current_user.is_admin and not current_user.is_editor:
        flash('管理者または編集者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    form = ImageUploadForm()
    if form.validate_on_submit():
        if 'image_file' in request.files and request.files['image_file'].filename != '':
            file = request.files['image_file']
            if file and allowed_file(file.filename):
                try:
                    filename = secure_filename(file.filename)
                    unique_filename = str(uuid.uuid4()) + os.path.splitext(filename)[1]

                    image_full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                    thumbnail_full_path = os.path.join(current_app.config['THUMBNAIL_FOLDER'], 'thumb_' + unique_filename)

                    file.save(image_full_path)

                    thumb_filename_for_db = None
                    thumb_filepath_for_db = None
                    try:
                        img = PilImage.open(image_full_path)
                        img.thumbnail(THUMBNAIL_SIZE)
                        img.save(thumbnail_full_path)
                        thumb_filename_for_db = 'thumb_' + unique_filename
                        thumb_filepath_for_db = thumbnail_full_path
                    except Exception as thumb_e:
                        current_app.logger.warning(f"Failed to generate thumbnail for {filename}: {thumb_e}")

                    new_image = Image(
                        original_filename=filename,
                        unique_filename=unique_filename,
                        filepath=image_full_path,
                        thumbnail_filename=thumb_filename_for_db,
                        thumbnail_filepath=thumb_filepath_for_db,
                        user_id=current_user.id,
                        alt_text=form.alt_text.data # フォームにalt_textフィールドがある場合
                    )
                    db.session.add(new_image)
                    db.session.commit()
                    flash('画像が正常にアップロードされました。', 'success')
                    return redirect(url_for('admin.list_images'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'画像のアップロード中にエラーが発生しました: {e}', 'warning')
                    current_app.logger.error(f"Error uploading single image: {e}", exc_info=True)
            else:
                flash('許可されていないファイル形式です。', 'warning')
        else:
            flash('ファイルが選択されていません。', 'warning')
    return render_template('images/upload_single_image.html', form=form)


@admin_bp.route('/images/bulk_upload_form')
@login_required
def show_bulk_upload_form():
    if not current_user.is_admin and not current_user.is_editor:
        flash('管理者または編集者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    form = BulkImageUploadForm()
    return render_template('images/bulk_upload_form.html', form=form)

@admin_bp.route('/images/bulk_upload', methods=['POST'])
@login_required
def bulk_upload_images():
    if not current_user.is_admin and not current_user.is_editor:
        flash('管理者または編集者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))

    form = BulkImageUploadForm()
    if form.validate_on_submit():
        uploaded_files = request.files.getlist('image_files')
        
        if not uploaded_files or uploaded_files[0].filename == '':
            flash('ファイルを一つ以上選択してください。', 'warning')
            return redirect(url_for('admin.show_bulk_upload_form'))

        upload_success_count = 0
        upload_fail_count = 0
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                try:
                    filename = secure_filename(file.filename)
                    unique_filename = str(uuid.uuid4()) + os.path.splitext(filename)[1]
                    
                    image_full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                    thumbnail_full_path = os.path.join(current_app.config['THUMBNAIL_FOLDER'], 'thumb_' + unique_filename)

                    # 元のファイルを保存
                    file.save(image_full_path)
                    
                    thumb_filename_for_db = None
                    thumb_filepath_for_db = None

                    # Pillow を使ってサムネイルを生成
                    try:
                        img = PilImage.open(image_full_path)
                        # サムネイルサイズにリサイズ（アスペクト比を維持してフィット）
                        img.thumbnail(THUMBNAIL_SIZE) 
                        img.save(thumbnail_full_path)
                        thumb_filename_for_db = 'thumb_' + unique_filename
                        thumb_filepath_for_db = thumbnail_full_path
                    except Exception as thumb_e:
                        current_app.logger.warning(f"Failed to generate thumbnail for {filename}: {thumb_e}")
                        # サムネイル生成に失敗した場合はNoneを設定

                    # Imageモデルに保存
                    new_image = Image(
                        original_filename=filename,
                        unique_filename=unique_filename,
                        filepath=image_full_path,
                        thumbnail_filename=thumb_filename_for_db,
                        thumbnail_filepath=thumb_filepath_for_db,
                        user_id=current_user.id,
                        is_main_image=False, # デフォルトでFalse
                        alt_text=None # デフォルトでNone (またはフォームから取得)
                    )
                    db.session.add(new_image)
                    db.session.commit()
                    upload_success_count += 1
                except Exception as e:
                    db.session.rollback()
                    flash(f'ファイル {file.filename} のアップロード中にエラーが発生しました: {e}', 'warning')
                    current_app.logger.error(f"Error uploading file {file.filename}: {e}", exc_info=True)
                    upload_fail_count += 1
            else:
                flash(f'ファイル {file.filename} は許可されていない形式です。', 'warning')
                upload_fail_count += 1
        
        if upload_success_count > 0:
            flash(f'{upload_success_count} 個の画像を正常にアップロードしました。', 'success')
        if upload_fail_count > 0:
            flash(f'{upload_fail_count} 個の画像のアップロードに失敗しました。詳細はログを確認してください。', 'warning')

        return redirect(url_for('admin.list_images'))
    else:
        # フォームのバリデーションに失敗した場合（CSRFトークンなど）
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
        return redirect(url_for('admin.show_bulk_upload_form'))


@admin_bp.route('/images/delete/<uuid:image_id>', methods=['POST'])
@login_required
def delete_image(image_id):
    if not current_user.is_admin and not current_user.is_editor:
        flash('管理者または編集者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    image = Image.query.get_or_404(image_id)
    
    try:
        # ファイルシステムから画像を削除
        if os.path.exists(image.filepath):
            os.remove(image.filepath)
        if image.thumbnail_filepath and os.path.exists(image.thumbnail_filepath):
            os.remove(image.thumbnail_filepath)
        
        # データベースからレコードを削除
        db.session.delete(image)
        db.session.commit()
        flash('画像が正常に削除されました。', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'画像の削除中にエラーが発生しました: {e}', 'danger')
        current_app.logger.error(f"Error deleting image {image_id}: {e}", exc_info=True)
    
    return redirect(url_for('admin.list_images'))

# --- コメント管理 ---
@admin_bp.route('/comments')
@login_required
def list_comments():
    if not current_user.is_admin and not current_user.is_editor:
        flash('管理者または編集者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    comments = Comment.query.order_by(Comment.created_at.desc()).all()
    return render_template('comments/list_comments.html', comments=comments)

@admin_bp.route('/comments/toggle_approval/<uuid:comment_id>', methods=['POST'])
@login_required
def toggle_approval(comment_id):
    if not current_user.is_admin and not current_user.is_editor:
        flash('管理者または編集者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    comment = Comment.query.get_or_404(comment_id)
    comment.approved = not comment.approved
    db.session.commit()
    flash(f'コメントが{"承認" if comment.approved else "却下"}されました。', 'success')
    return redirect(url_for('admin.list_comments'))

@admin_bp.route('/comments/delete/<uuid:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    if not current_user.is_admin and not current_user.is_editor:
        flash('管理者または編集者権限が必要です。', 'danger')
        return redirect(url_for('home.index'))
    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    flash('コメントが削除されました。', 'success')
    return redirect(url_for('admin.list_comments'))

# --- Homeブループリントからadminダッシュボードへのリダイレクト (home.dashboardは削除されている可能性) ---
# このルートはhomeブループリントに属するが、adminダッシュボードへのリダイレクトを担当
# @home_bp.route('/dashboard')
# @login_required
# def dashboard():
#     if current_user.is_admin or current_user.is_editor:
#         return redirect(url_for('admin.index'))
#     return render_template('home/dashboard.html') # 一般ユーザー向けダッシュボード