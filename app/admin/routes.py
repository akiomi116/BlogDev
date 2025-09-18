# F:\dev\BrogDev\app\admin\routes.py

import os
import uuid
import pytz 
import re
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image as PilImage 
from werkzeug.security import generate_password_hash 

from flask import Blueprint, render_template, redirect, url_for,  request, current_app, jsonify, abort ,flash
from flask_login import login_required, current_user
from app.models import Post, Comment, Category, Tag, Image, User, Role 
from app.extensions import db
from app.forms import PostForm, ImageUploadForm, BulkImageUploadForm, DeleteForm, UserEditForm 
from wtforms.validators import Optional, DataRequired 
from flask_wtf.file import FileAllowed 


from flask_security import roles_required
from flask_principal import Permission, RoleNeed

from . import bp

# from . import blog_admin_bp
from app import db

from werkzeug.utils import secure_filename
from PIL import Image as PilImage # Python Imaging Library 用

import re

# ファイルの許可された拡張子をチェックするヘルパー関数
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']



@bp.route('/show-routes')
def show_routes():
    import urllib
    output = []
    for rule in current_app.url_map.iter_rules():
        options = {}
        for arg in rule.arguments:
            options[arg] = f"[{arg}]"

        methods = ','.join(rule.methods)
        url = urllib.parse.unquote(rule.rule)
        line = f"{rule.endpoint:50s} {methods:20s} {url}"
        output.append(line)
    
    output.sort()
    
    return "<pre>" + "\n".join(output) + "</pre>"



def slugify(text):
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text

# --- 管理ダッシュボードのルート ---
@bp.route('/')
@bp.route('/index')
@login_required
# @roles_required('admin', 'poster') 
def index():
    # --- デバッグコード ---
    print(f"--- Admin Dashboard Access ---")
    print(f"User: {current_user.username}")
    print(f"User ID: {current_user.id}")
    print(f"User Roles: {[role.name for role in current_user.roles]}")
    print(f"Has 'admin' role: {current_user.has_role('admin')}")
    print(f"Has 'poster' role: {current_user.has_role('poster')}")
    # --- デバッグコード終了 ---

    # ここにデバッグ用のprint文を追加
    print(f"DEBUG (admin.index): current_user.is_authenticated = {current_user.is_authenticated}")
    print(f"DEBUG (admin.index): current_user.email = {current_user.email if current_user.is_authenticated else 'Not authenticated'}")

    # 管理ダッシュボードの概要情報を取得
    total_posts = Post.query.count()
    published_posts = Post.query.filter_by(is_published=True).count()
    total_comments = Comment.query.count()
    total_users = User.query.count()
    
    return render_template('admin/index.html', 
                        title='管理ダッシュボード',
                        total_posts=total_posts,
                        published_posts=published_posts,
                        total_comments=total_comments,
                        total_users=total_users)

# ヘルパー関数: 許可されたファイル拡張子かどうかをチェック
def allowed_file(filename):
    # ファイル名に拡張子があるか確認し、許可された拡張子リストに含まれているかチェック
    # rsplit('.', 1)[1] で拡張子部分を正確に取得
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

# --- 投稿管理 ---

@bp.route('/posts')
@login_required
def list_posts():
    # 手動の権限チェック
    required_roles = ['admin', 'editor', 'poster']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    if current_user.has_role('admin'):
        posts = Post.query.order_by(Post.created_at.desc()).all()
    else:
        posts = Post.query.filter_by(posted_by=current_user).order_by(Post.created_at.desc()).all()
    
    csrf_form = DeleteForm()
    
    return render_template('posts/list_posts.html', posts=posts, title='投稿管理', csrf_form=csrf_form)


@bp.route('/posts/new', methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    gallery_images = Image.query.all()  # 必要に応じてフィルタを追加

    # カテゴリの選択肢を動的に設定
    form.category.choices = [(str(c.id), c.name) for c in Category.query.all()]

    if request.method == 'POST':
        # デバッグログの出力 (current_app.logger を使用)
        current_app.logger.debug("\n--- DEBUG: POST Request Received ---")
        current_app.logger.debug(f"DEBUG: request.files: {request.files}")

        # main_image_file がリクエストに含まれているかチェック
        if 'main_image_file' in request.files:
            file_storage = request.files['main_image_file']
            current_app.logger.debug(f"DEBUG: main_image_file from request.files:")
            current_app.logger.debug(f" Filename: {file_storage.filename}")
            current_app.logger.debug(f" MIME Type: {file_storage.mimetype}")
            current_app.logger.debug(f" Content Length (from header): {file_storage.content_length} bytes")

            # ★★★最も重要な修正点: FileStorageストリームのポインタを先頭に戻す★★★
            # これをしないと、WTFormsがform.main_image_file.dataをバインドする際に
            # ストリームが既に読み尽くされているため、Noneになってしまう可能性があります。
            try:
                # Werkzeug の FileStorage オブジェクトの stream を使ってポインタを戻す
                file_storage.stream.seek(0) 
                current_app.logger.debug("DEBUG: file_storage.stream.seek(0) called.")
                # デバッグのために実際のサイズを再確認する (メモリ消費に注意)
                actual_stream_length = len(file_storage.stream.read())
                file_storage.stream.seek(0) # 再度先頭に戻す for WTForms
                current_app.logger.debug(f"DEBUG: Actual file content length (stream read): {actual_stream_length} bytes")
                
                if actual_stream_length == 0 and file_storage.filename: # ファイルが選択されているのに内容が0の場合
                    current_app.logger.error("ERROR: File content is empty after stream read, but filename exists.")
                    flash('アップロードされたファイルが空です。再度お試しください。', 'danger')
                    return render_template('posts/new_post.html', form=form, title='新規投稿', is_edit=False)

            except Exception as e:
                current_app.logger.error(f"Error seeking/reading file stream for debug: {e}", exc_info=True)
                flash('ファイルの読み取り中にエラーが発生しました。', 'danger')
                return render_template('posts/new_post.html', form=form, title='新規投稿', is_edit=False)
        else:
            current_app.logger.debug("DEBUG: 'main_image_file' not in request.files (no file uploaded).")

        current_app.logger.debug(f"DEBUG: request.form: {request.form}")
        current_app.logger.debug(f"--- DEBUG End ---")
        
        # form.validate_on_submit() は、request.form と request.files を使ってフォームをバリデート
        # 上記で file_storage.stream.seek(0) を行っていれば、form.main_image_file.data は適切にバインドされるはず
        if form.validate_on_submit():
            current_app.logger.debug(f"DEBUG: Form validation successful.")
            current_app.logger.debug(f"DEBUG: form.main_image_file.data type: {type(form.main_image_file.data)}")
            if form.main_image_file.data:
                current_app.logger.debug(f"DEBUG: form.main_image_file.data.filename: {form.main_image_file.data.filename}")
            current_app.logger.debug(f"DEBUG: form.main_image.data: {form.main_image.data}") # QuerySelectFieldのデータ (ImageオブジェクトまたはNone)

            main_image_obj = None

            # 1. 新しい画像がアップロードされた場合を優先
            if form.main_image_file.data and form.main_image_file.data.filename:
                main_image_file = form.main_image_file.data
                
                if not allowed_file(main_image_file.filename):
                    flash('許可されていないファイル形式です。', 'danger')
                    return render_template('posts/new_post.html', form=form, title='新規投稿', is_edit=False)

                original_filename = secure_filename(main_image_file.filename)
                unique_filename = str(uuid.uuid4()) + os.path.splitext(original_filename)[1]
                thumbnail_filename = 'thumb_' + unique_filename
                
                filepath_abs = os.path.join(current_app.config['UPLOAD_IMAGES_DIR'], unique_filename)
                thumbnail_filepath_abs = os.path.join(current_app.config['UPLOAD_THUMBNAILS_DIR'], thumbnail_filename)
                
                filepath_rel = os.path.join(current_app.config['UPLOAD_FOLDER_RELATIVE_PATH'], unique_filename).replace('\\', '/')
                thumbnail_filepath_rel = os.path.join(current_app.config['THUMBNAIL_FOLDER_RELATIVE_PATH'], thumbnail_filename).replace('\\', '/')

                try:
                    # ここでファイルの保存が行われます。
                    # form.main_image_file.data (FileStorageオブジェクト) は、
                    # 既にストリームが先頭に戻されているため、正しく保存できるはずです。
                    main_image_file.save(filepath_abs) 
                    
                    # サムネイル生成
                    img = PilImage.open(filepath_abs)
                    img.thumbnail(current_app.config['THUMBNAIL_SIZE'])
                    img.save(thumbnail_filepath_abs)
                    
                    main_image_obj = Image(
                        original_filename=original_filename,
                        unique_filename=unique_filename,
                        thumbnail_filename=thumbnail_filename,
                        mimetype=main_image_file.mimetype,
                        filepath=filepath_rel,
                        thumbnail_filepath=thumbnail_filepath_rel,
                        user_id=current_user.id,
                        alt_text=form.main_image_alt_text.data
                    )
                    db.session.add(main_image_obj)
                    db.session.flush() # IDを取得するためにflush
                    current_app.logger.info(f"New image uploaded and saved: {unique_filename}")
                except Exception as e:
                    current_app.logger.error(f"Image processing error: {e}", exc_info=True)
                    flash('画像の処理中にエラーが発生しました。', 'danger')
                    return render_template('posts/new_post.html', form=form, title='新規投稿', is_edit=False)

            # 2. 既存の画像がギャラリーから選択された場合 (form.selected_image_id.data が 画像ID の場合)
            elif form.selected_image_id.data:
                try:
                    image_id = uuid.UUID(form.selected_image_id.data)
                    main_image_obj = db.session.get(Image, image_id)
                    if main_image_obj:
                        if form.main_image_alt_text.data and form.main_image_alt_text.data != main_image_obj.alt_text:
                            main_image_obj.alt_text = form.main_image_alt_text.data
                            db.session.add(main_image_obj) # 変更を追跡させる
                        current_app.logger.info(f"Existing image selected from gallery: {main_image_obj.unique_filename}")
                    else:
                        flash('選択された画像が見つかりません。', 'danger')
                        return render_template('posts/new_post.html', form=form, title='新規投稿', is_edit=False)
                except ValueError:
                    flash('無効な画像IDです。', 'danger')
                    return render_template('posts/new_post.html', form=form, title='新規投稿', is_edit=False)

            # この時点では、main_image_obj が None であれば、フォームバリデーションが失敗しているはず。
            # ただし、念のため最終チェックとして残しておいても良い。
            if main_image_obj is None:
                flash('メイン画像をアップロードするか、ギャラリーから選択してください。', 'danger')
                return render_template('posts/new_post.html', form=form, title='新規投稿', is_edit=False)

            # 投稿作成処理
            category = None
            if form.category.data:
                category = db.session.get(Category, form.category.data) # QuerySelectFieldではないため、IDで取得

            new_post = Post(
                title=form.title.data,
                body=form.body.data,
                posted_by=current_user,
                category=category,
                is_published=form.is_published.data,
                main_image=main_image_obj 
            )
            db.session.add(new_post)
            
            if form.tags.data:
                new_post.tags = form.tags.data
            
            if form.additional_images.data: # QuerySelectMultipleFieldなので、Imageオブジェクトのリストが返る
                new_post.additional_images = form.additional_images.data

            db.session.commit()
            flash('新しい投稿が作成されました。', 'success')
            return redirect(url_for('blog_admin_bp.list_posts'))
        
        # バリデーション失敗時 (POSTメソッドの場合)
        else: 
            current_app.logger.warning(f"Post form validation failed: {form.errors}")
            current_app.logger.debug(f"Form validation errors: {form.errors}")
            current_app.logger.debug(f"form.main_image_file.data (on validation failure): {form.main_image_file.data}")
            current_app.logger.debug(f"form.main_image.data (on validation failure): {form.main_image.data}")
    
    # GETリクエストの場合、またはPOSTリクエストでバリデーション失敗した場合
    # 例: ギャラリー画像取得
    return render_template('posts/new_post.html', form=form, gallery_images=gallery_images, title='新規投稿', is_edit=False)


@bp.route('/posts/edit/<uuid:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    # 手動の権限チェック
    required_roles = ['admin', 'editor', 'poster']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    post = db.session.get(Post, post_id)
    if post is None:
        flash('投稿が見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_posts'))

    if not (current_user.has_role('admin') or current_user.has_role('poster') or post.posted_by_id == current_user.id):
        flash('この投稿を編集する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_posts'))

    form = PostForm(obj=post) 

    form.category.choices = [(str(c.id), c.name) for c in Category.query.all()]
    form.tags.choices = [(str(t.id), t.name) for t in Tag.query.order_by(Tag.name).all()]

    if request.method == 'GET':
        if post.main_image:
            form.main_image.data = post.main_image.id 
            form.main_image_alt_text.data = post.main_image.alt_text
        if post.additional_images:
            form.additional_images.data = post.additional_images

    if form.validate_on_submit(): # ここで不完全なif文を修正
        post.title = form.title.data
        post.body = form.body.data
        post.is_published = form.is_published.data
        post.updated_at = datetime.now(pytz.utc)

        if form.category.data:
            # カテゴリIDからCategoryオブジェクトを取得
            category_obj = db.session.get(Category, form.category.data)
            post.category = category_obj
        else:
            post.category = None

        selected_tags = []
        if form.tags.data:
            # Tagオブジェクトのリストからidリストに変換
            tag_ids = [tag.id for tag in form.tags.data]
            selected_tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
        post.tags = selected_tags

        main_image_file = form.main_image_file.data
        selected_main_image_id = form.main_image.data 
        
        new_main_image_obj = None
        upload_successful = False

        if main_image_file and main_image_file.filename and allowed_file(main_image_file.filename):
            original_filename = secure_filename(main_image_file.filename)
            unique_filename = str(uuid.uuid4()) + os.path.splitext(original_filename)[1]
            
            thumbnail_filename = 'thumb_' + unique_filename
            filepath_abs = os.path.join(current_app.config['UPLOAD_IMAGES_DIR'], unique_filename)
            thumbnail_filepath_abs = os.path.join(current_app.config['UPLOAD_THUMBNAILS_DIR'], thumbnail_filename)

            filepath_rel = os.path.join(current_app.config['UPLOAD_FOLDER_RELATIVE_PATH'], unique_filename).replace('\\', '/')
            thumbnail_filepath_rel = os.path.join(current_app.config['THUMBNAIL_FOLDER_RELATIVE_PATH'], thumbnail_filename).replace('\\', '/')

            try:
                # ここでファイルの保存が行われます。
                # form.main_image_file.data (FileStorageオブジェクト) は、
                # 既にストリームが先頭に戻されているため、正しく保存できるはずです。
                main_image_file.save(filepath_abs) 
                
                # サムネイル生成
                img = PilImage.open(filepath_abs)
                img.thumbnail(current_app.config['THUMBNAIL_SIZE'])
                img.save(thumbnail_filepath_abs)
                upload_successful = True
            except Exception as e:
                current_app.logger.error(f"投稿編集での画像アップロードエラー: {e}", exc_info=True)
                flash('新しいメイン画像のアップロード中にエラーが発生しました。', 'danger')
                thumbnail_filename = None
                upload_successful = False

            if upload_successful:
                new_main_image_obj = Image(
                    original_filename=original_filename,
                    unique_filename=unique_filename,
                    thumbnail_filename=thumbnail_filename,
                    mimetype=main_image_file.mimetype,
                    filepath=filepath_rel,
                    thumbnail_filepath=thumbnail_filepath_rel,
                    user_id=current_user.id,
                    alt_text=form.main_image_alt_text.data
                )
                db.session.add(new_main_image_obj)
                db.session.flush() 
                post.main_image = new_main_image_obj 

        elif selected_main_image_id:
            # Imageオブジェクトが来た場合はidを取り出す
            if hasattr(selected_main_image_id, "id"):
                image_id_to_fetch = selected_main_image_id.id
            elif isinstance(selected_main_image_id, uuid.UUID):
                image_id_to_fetch = selected_main_image_id
            else:
                try:
                    image_id_to_fetch = str(selected_main_image_id)
                except ValueError:
                    current_app.logger.error(f"不正なUUID文字列が selected_main_image_id に渡されました: {selected_main_image_id}")
                    flash('選択されたメイン画像の形式が不正です。', 'warning')
                    return render_template('posts/edit_post.html', form=form, post=post, title='投稿編集', is_edit=True)

            new_main_image_obj = db.session.get(Image, image_id_to_fetch)
            
            if new_main_image_obj:
                post.main_image = new_main_image_obj
                if form.main_image_alt_text.data:
                    new_main_image_obj.alt_text = form.main_image_alt_text.data
            else:
                flash('選択されたメイン画像が見つかりません。', 'warning')
                return render_template('posts/edit_post.html', form=form, post=post, title='投稿編集', is_edit=True)
        else:
            post.main_image = None
            if post.main_image_id: 
                old_main_image = db.session.get(Image, post.main_image_id)
                if old_main_image:
                    old_main_image.alt_text = None

        selected_additional_images = []
        if form.additional_images.data:
            for item in form.additional_images.data:
                if isinstance(item, uuid.UUID): 
                    img_obj = db.session.get(Image, item)
                    if img_obj:
                        selected_additional_images.append(img_obj)
                else: 
                    try:
                        img_obj = db.session.get(Image, str(item)) 
                        if img_obj:
                            selected_additional_images.append(img_obj)
                    except ValueError:
                        current_app.logger.warning(f"不正なUUID文字列が追加画像の選択に渡されました: {item}")
            
        post.additional_images = selected_additional_images
        
        db.session.commit()
        flash('投稿が正常に更新されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_posts'))
        
    return render_template('posts/edit_post.html', form=form, post=post, title='投稿編集', is_edit=True)




@bp.route('/posts/delete/<uuid:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    # 手動の権限チェック
    required_roles = ['admin', 'poster']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    post_to_delete = db.session.get(Post, post_id)
    if not post_to_delete:
        flash('投稿が見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_posts'))

    if not (current_user.has_role('admin') or (current_user.has_role('poster') and post_to_delete.posted_by_id == current_user.id)):
        flash('この投稿を削除する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_posts'))
    
    try:
        db.session.delete(post_to_delete)
        db.session.commit()
        flash('投稿が正常に削除されました。', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'投稿の削除中にエラーが発生しました: {e}', 'danger')
        current_app.logger.error(f"投稿の削除中にエラーが発生しました (DBロールバック): {e}", exc_info=True)
    
    return redirect(url_for('blog_admin_bp.list_posts'))


# --- カテゴリ管理 ---
@bp.route('/categories')
@login_required
def list_categories():
    # 手動の権限チェック
    required_roles = ['admin']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    categories = Category.query.order_by(Category.name).all()
    csrf_form = DeleteForm()
    return render_template('categories/list_categories.html', categories=categories, title='カテゴリ管理', csrf_form=csrf_form)

@bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def add_category():
    from app.forms import CategoryForm 
    form = CategoryForm()
    if form.validate_on_submit():
        slug = slugify(form.name.data)
        new_category = Category(
            name=form.name.data,
            slug=slug,
            description=form.description.data,
            user_id=current_user.id  # ここを追加
        )
        db.session.add(new_category)
        db.session.commit()
        flash('新しいカテゴリが追加されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_categories'))

    return render_template('categories/add_edit_category.html', form=form, title='カテゴリ追加')

@bp.route('/categories/edit/<uuid:category_id>', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    # 手動の権限チェック
    required_roles = ['admin']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    from app.forms import CategoryForm 
    category = db.session.get(Category, category_id)
    if category is None:
        flash('カテゴリが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_categories'))

    form = CategoryForm(obj=category)
    if form.validate_on_submit():
        category.name = form.name.data
        db.session.commit()
        flash('カテゴリ名が更新されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_categories'))
    return render_template('categories/add_edit_category.html', form=form, category=category, title='カテゴリ編集')

@bp.route('/categories/delete/<uuid:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    # 手動の権限チェック
    required_roles = ['admin']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    category_to_delete = db.session.get(Category, category_id)
    if category_to_delete is None:
        flash('カテゴリが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_categories'))
    
    if category_to_delete.posts.count() > 0:
        flash('このカテゴリには関連する投稿があります。先に投稿のカテゴリを変更または削除してください。', 'warning')
        return redirect(url_for('blog_admin_bp.list_categories'))

    try:
        db.session.delete(category_to_delete)
        db.session.commit()
        flash('カテゴリが削除されました。', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'カテゴリの削除中にエラーが発生しました: {e}', 'danger')
    return redirect(url_for('blog_admin_bp.list_categories'))

# --- タグ管理 ---
@bp.route('/tags')
@login_required
def list_tags():
    # 手動の権限チェック
    required_roles = ['admin']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    tags = Tag.query.order_by(Tag.name).all()
    csrf_form = DeleteForm()
    return render_template('tags/list_tags.html', tags=tags, title='タグ管理', csrf_form=csrf_form)

@bp.route('/tags/add', methods=['GET', 'POST'])
@login_required
def add_tag():
    # 手動の権限チェック
    required_roles = ['admin']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    from app.forms import TagForm 
    form = TagForm()
    if form.validate_on_submit():
        slug = form.slug.data if form.slug.data else slugify(form.name.data)
        new_tag = Tag(name=form.name.data, slug=slug, user_id=current_user.id)
        db.session.add(new_tag)
        db.session.commit()
        flash('新しいタグが追加されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_tags'))
    return render_template('tags/new_tag.html', form=form, title='タグ追加')

@bp.route('/tags/edit/<uuid:tag_id>', methods=['GET', 'POST'])
@login_required
def edit_tag(tag_id):
    # 手動の権限チェック
    required_roles = ['admin']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    from app.forms import TagForm 
    tag = db.session.get(Tag, tag_id)
    if tag is None:
        flash('タグが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_tags'))

    form = TagForm(obj=tag)
    if form.validate_on_submit():
        tag.name = form.name.data
        tag.slug = form.slug.data if form.slug.data else slugify(form.name.data)
        db.session.commit()
        flash('タグ名が更新されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_tags'))
    return render_template('tags/edit_tag.html', form=form, tag=tag, title='タグ編集')

@bp.route('/tags/delete/<uuid:tag_id>', methods=['POST'])
@login_required
def delete_tag(tag_id):
    # 手動の権限チェック
    required_roles = ['admin']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    tag_to_delete = db.session.get(Tag, tag_id)
    if tag_to_delete is None:
        flash('タグが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_tags'))

    if tag_to_delete.posts.count() > 0:
        flash('このタグには関連する投稿があります。先に投稿からタグを解除してください。', 'warning')
        return redirect(url_for('blog_admin_bp.list_tags'))

    try:
        db.session.delete(tag_to_delete)
        db.session.commit()
        flash('タグが削除されました。', 'success')
    except Exception as e: # このexceptブロックを正しく閉じる
        db.session.rollback()
        flash(f'タグの削除中にエラーが発生しました: {e}', 'danger')
        current_app.logger.error(f"タグの削除中にエラーが発生しました (DBロールバック): {e}", exc_info=True) # 追加: エラーログ出力
    return redirect(url_for('blog_admin_bp.list_tags'))


# --- 画像管理 ---

# 画像ギャラリー用のJSONデータを提供するルート
@bp.route('/uploads/images/json') 
@login_required 
def get_images_json():
    images = Image.query.order_by(Image.uploaded_at.desc()).all()
    image_list = []
    for img in images:
        image_list.append({
            'id': str(img.id), 
            'original_filename': img.original_filename,
            'unique_filename': img.unique_filename,
            'thumbnail_filename': img.thumbnail_filename,
            'alt_text': img.alt_text,
            'url': img.url, 
            'thumbnail_url': img.thumbnail_url 
        })
    return jsonify({"images": image_list})

@bp.route('/images')
@login_required
def list_images():
    # 手動の権限チェック
    required_roles = ['admin', 'editor', 'poster']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    if current_user.has_role('admin'):
        images = Image.query.order_by(Image.uploaded_at.desc()).all()
    else:
        images = Image.query.filter_by(user_id=current_user.id).order_by(Image.uploaded_at.desc()).all()
    return render_template('images/list_images.html', images=images, title='画像管理') 

@bp.route('/images/upload', methods=['GET', 'POST'])
@login_required
def upload_image():
    # 手動の権限チェック
    required_roles = ['admin', 'editor', 'poster']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    form = ImageUploadForm()
    if form.validate_on_submit():
        image_file = form.image.data
        if image_file and allowed_file(image_file.filename):
            original_filename = secure_filename(image_file.filename)
            unique_filename = str(uuid.uuid4()) + os.path.splitext(original_filename)[1] # 拡張子を取得
            
            filepath_abs = os.path.join(current_app.config['UPLOAD_IMAGES_DIR'], unique_filename)
            
            try:
                image_file.save(filepath_abs)

                thumbnail_filename = 'thumb_' + unique_filename
                thumbnail_filepath_abs = os.path.join(current_app.config['UPLOAD_THUMBNAILS_DIR'], thumbnail_filename)
                img_pil = PilImage.open(filepath_abs)
                img_pil.thumbnail(current_app.config['THUMBNAIL_SIZE'])
                img_pil.save(thumbnail_filepath_abs)
                
                filepath_rel = os.path.join(current_app.config['UPLOAD_FOLDER_RELATIVE_PATH'], unique_filename).replace('', '/')
                thumbnail_filepath_rel = os.path.join(current_app.config['THUMBNAIL_FOLDER_RELATIVE_PATH'], thumbnail_filename).replace('', '/')
                
            except Exception as e:
                current_app.logger.error(f"サムネイル生成中にエラーが発生しました: {e}")
                thumbnail_filename = None
                filepath_rel = None 
                thumbnail_filepath_rel = None 
            
            new_image = Image(
                original_filename=original_filename,
                unique_filename=unique_filename,
                thumbnail_filename=thumbnail_filename,
                filepath=filepath_rel, 
                thumbnail_filepath=thumbnail_filepath_rel if thumbnail_filename else None, 
                user_id=current_user.id,
                alt_text=form.alt_text.data
            )
            db.session.add(new_image)
            db.session.commit()
            flash('画像が正常にアップロードされました。', 'success')
            return redirect(url_for('blog_admin_bp.list_images'))
        else:
            flash('無効なファイル形式です。', 'danger')
    return render_template('images/upload_image.html', form=form, title='画像アップロード') 

@bp.route('/images/bulk_upload', methods=['GET', 'POST'])
@login_required
def bulk_upload_images():
    # 手動の権限チェック
    required_roles = ['admin', 'editor', 'poster']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    form = BulkImageUploadForm()
    if form.validate_on_submit():
        uploaded_count = 0
        failed_count = 0
        for image_file in form.images.data:
            if image_file and allowed_file(image_file.filename):
                original_filename = secure_filename(image_file.filename)
                unique_filename = str(uuid.uuid4()) + os.path.splitext(original_filename)[1] # 拡張子を取得
                
                filepath_abs = os.path.join(current_app.config['UPLOAD_IMAGES_DIR'], unique_filename)
                
                try:
                    image_file.save(filepath_abs)

                    thumbnail_filename = 'thumb_' + unique_filename
                    thumbnail_filepath_abs = os.path.join(current_app.config['UPLOAD_THUMBNAILS_DIR'], thumbnail_filename)
                    try:
                        img_pil = PilImage.open(filepath_abs)
                        img_pil.thumbnail(current_app.config['THUMBNAIL_SIZE'])
                        img_pil.save(thumbnail_filepath_abs)
                    except Exception as e:
                        current_app.logger.error(f"バルクアップロード中にサムネイル生成エラー: {original_filename} - {e}")
                        thumbnail_filename = None
                        thumbnail_filepath_abs = None 

                    filepath_rel = os.path.join(current_app.config['UPLOAD_FOLDER_RELATIVE_PATH'], unique_filename).replace('\\', '/')
                    thumbnail_filepath_rel = os.path.join(current_app.config['THUMBNAIL_FOLDER_RELATIVE_PATH'], thumbnail_filename).replace('\\', '/') if thumbnail_filename else None

                    new_image = Image(
                        original_filename=original_filename,
                        unique_filename=unique_filename,
                        thumbnail_filename=thumbnail_filename,
                        filepath=filepath_rel, 
                        thumbnail_filepath=thumbnail_filepath_rel, 
                        user_id=current_user.id,
                        alt_text="" 
                    )
                    db.session.add(new_image)
                    uploaded_count += 1
                except Exception as e:
                    current_app.logger.error(f"バルクアップロード中にファイル保存エラー: {original_filename} - {e}")
                    failed_count += 1
            else:
                failed_count += 1
        
        if uploaded_count > 0:
            db.session.commit()
            flash(f'{uploaded_count}個の画像を正常にアップロードしました。', 'success')
        if failed_count > 0:
            flash(f'{failed_count}個の画像のアップロードに失敗しました（無効なファイル形式またはエラー）。', 'danger')
        
        return redirect(url_for('blog_admin_bp.list_images'))
    return render_template('images/bulk_upload_images.html', form=form, title='一括画像アップロード')


@bp.route('/images/edit/<uuid:image_id>', methods=['GET', 'POST'])
@login_required
def edit_image(image_id):
    # 手動の権限チェック
    required_roles = ['admin', 'editor', 'poster']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    image = db.session.get(Image, image_id)
    if image is None:
        flash('画像が見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_images'))
    
    if not (current_user.has_role('admin') or image.user_id == current_user.id):
        flash('この画像を編集する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_images'))

    form = ImageUploadForm(obj=image)
    form.image.validators = [Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], '画像ファイル (JPG, JPEG, PNG, GIF, WEBP) のみ許可されます')]


    if form.validate_on_submit():
        image.alt_text = form.alt_text.data
        db.session.commit()
        flash('画像情報が更新されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_images'))
    elif request.method == 'GET':
        form.alt_text.data = image.alt_text

    return render_template('images/edit_image.html', form=form, image=image, title='画像編集')


@bp.route('/images/delete/<uuid:image_id>', methods=['POST'])
@login_required
def delete_image(image_id):
    # 手動の権限チェック
    required_roles = ['admin', 'editor', 'poster']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    image_to_delete = db.session.get(Image, image_id)
    if image_to_delete is None:
        flash('画像が見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_images'))
    
    if not (current_user.has_role('admin') or image_to_delete.user_id == current_user.id):
        flash('この画像を削除する権限がありません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_images'))

    if image_to_delete.main_image_for_post:
        flash('この画像は投稿のメイン画像として使用されています。先に投稿から画像を解除してください。', 'warning')
        return redirect(url_for('blog_admin_bp.list_images'))

    if image_to_delete.posts_as_additional_image.count() > 0:
        flash('この画像は複数の投稿の追加画像として使用されています。先に投稿から画像を解除してください。', 'warning')
        return redirect(url_for('blog_admin_bp.list_images'))

    try:
        abs_filepath = os.path.join(current_app.static_folder, image_to_delete.filepath) 
        abs_thumbnail_filepath = os.path.join(current_app.static_folder, image_to_delete.thumbnail_filepath) if image_to_delete.thumbnail_filepath else None 

        if image_to_delete.filepath and os.path.exists(abs_filepath):
            os.remove(abs_filepath)
            current_app.logger.info(f"Deleted physical file: {abs_filepath}")
        else:
            current_app.logger.warning(f"File not found for deletion (main image): {abs_filepath}")

        if image_to_delete.thumbnail_filepath and os.path.exists(abs_thumbnail_filepath):
            os.remove(abs_thumbnail_filepath)
            current_app.logger.info(f"Deleted physical thumbnail file: {abs_thumbnail_filepath}")
        else:
            current_app.logger.warning(f"File not found for deletion (thumbnail): {abs_thumbnail_filepath}")

        db.session.delete(image_to_delete)
        db.session.commit()
        flash('画像が削除されました。', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'画像の削除中にエラーが発生しました: {e}', 'danger')
        current_app.logger.error(f"画像の削除中にエラーが発生しました (DBロールバック): {e}", exc_info=True)
    return redirect(url_for('blog_admin_bp.list_images'))

# --- ユーザー管理 ---
@bp.route('/users')
@login_required
def list_users():
    # 手動の権限チェック
    required_roles = ['admin']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    users = User.query.order_by(User.username).all()
    csrf_form = DeleteForm() # 削除用フォーム
    return render_template('users/list_users.html', users=users, title='ユーザー管理', csrf_form=csrf_form)

# ユーザー編集ルート
@bp.route('/users/edit/<uuid:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    # 手動の権限チェック
    required_roles = ['admin']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    user = db.session.get(User, user_id)
    if user is None:
        flash('ユーザーが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_users'))

    form = UserEditForm(obj=user) 
    
    # ロールの選択肢をフォームに設定
    form.roles.choices = [(str(r.id), r.name) for r in Role.query.order_by(Role.name).all()]

    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.active = form.is_active.data

        # パスワードが入力された場合のみ更新
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data)
        
        # ロールの更新
        # form.roles.data は QuerySelectMultipleField から返される Role オブジェクトのリスト
        user.roles = form.roles.data

        db.session.commit()
        flash('ユーザー情報が更新されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_users'))
    elif request.method == 'GET':
        # QuerySelectMultipleFieldはIDのリストを期待する
        form.roles.data = [role for role in user.roles] # user.rolesはRoleオブジェクトのリスト

    return render_template('users/edit_user.html', form=form, user=user, title='ユーザー編集')

# ユーザー削除ルート
@bp.route('/users/delete/<uuid:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    # 手動の権限チェック
    required_roles = ['admin']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    user_to_delete = db.session.get(User, user_id)
    if user_to_delete is None:
        flash('ユーザーが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_users'))

    if user_to_delete.id == current_user.id:
        flash('自分自身を削除することはできません。', 'warning')
        return redirect(url_for('blog_admin_bp.list_users'))

    admin_roles = Role.query.filter_by(name='admin').all()
    if admin_roles:
        admin_role_ids = [role.id for role in admin_roles]
        if user_to_delete.has_role('admin') and User.query.filter(User.roles.any(Role.id.in_(admin_role_ids))).count() <= 1:
            flash('最後の管理者ユーザーは削除できません。', 'warning')
            return redirect(url_for('blog_admin_bp.list_users'))

    try:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash('ユーザーが削除されました。', 'success')
    except Exception as e: # このexceptブロックを正しく閉じる
        db.session.rollback()
        flash(f'ユーザーの削除中にエラーが発生しました: {e}', 'danger')
        current_app.logger.error(f"ユーザーの削除中にエラーが発生しました: {e}", exc_info=True) # 追加: エラーログ出力
    
    return redirect(url_for('blog_admin_bp.list_users'))

@bp.route('/comments')
@login_required
def list_comments():
    # 手動の権限チェック
    required_roles = ['admin']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    # コメント一覧を取得してテンプレートに渡す
    comments = Comment.query.all()
    delete_form = DeleteForm()
    return render_template('admin/comments.html', comments=comments, delete_form=delete_form)

@bp.route('/comments/approve/<uuid:comment_id>', methods=['POST'])
@login_required
def approve_comment(comment_id):
    # 手動の権限チェック
    required_roles = ['admin', 'editor', 'poster']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403)

    comment = db.session.get(Comment, comment_id)
    if not comment:
        flash('コメントが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_comments'))

    comment.is_approved = True
    db.session.commit()
    flash('コメントを承認しました。', 'success')
    return redirect(url_for('blog_admin_bp.list_comments'))

@bp.route('/comments/edit/<uuid:comment_id>', methods=['GET', 'POST'])
@login_required
def edit_comment(comment_id):
    # 手動の権限チェック
    required_roles = ['admin']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403)

    comment = db.session.get(Comment, comment_id)
    if not comment:
        flash('コメントが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_comments'))

    from app.forms import CommentAdminEditForm
    form = CommentAdminEditForm(obj=comment)

    if form.validate_on_submit():
        comment.body = form.body.data
        comment.is_approved = form.is_approved.data
        db.session.commit()
        flash('コメントが更新されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_comments'))

    return render_template('admin/edit_comment.html', form=form, comment=comment, title='コメント編集')

@bp.route('/comments/delete/<uuid:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    # 手動の権限チェック
    required_roles = ['admin']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403)

    comment_to_delete = db.session.get(Comment, comment_id)
    if not comment_to_delete:
        flash('コメントが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_comments'))

    try:
        db.session.delete(comment_to_delete)
        db.session.commit()
        flash('コメントが削除されました。', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'コメントの削除中にエラーが発生しました: {e}', 'danger')
        current_app.logger.error(f"コメントの削除中にエラーが発生しました: {e}", exc_info=True)

    return redirect(url_for('blog_admin_bp.list_comments'))

@bp.route('/roles')
@login_required
@roles_required('admin')
def manage_roles():
    """ロールを管理する"""
    from app.forms import DeleteForm
    roles = Role.query.order_by(Role.name).all()
    csrf_form = DeleteForm()
    return render_template('roles/manage_roles.html', roles=roles, csrf_form=csrf_form, title='ロール管理')

# --- ロール管理 ---

@bp.route('/roles/add', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def add_role():
    """新しいロールを追加する"""
    from app.forms import RoleForm
    form = RoleForm()
    if form.validate_on_submit():
        new_role = Role(name=form.name.data, description=form.description.data)
        db.session.add(new_role)
        db.session.commit()
        flash('新しいロールが追加されました。', 'success')
        return redirect(url_for('blog_admin_bp.manage_roles'))
    return render_template('roles/add_edit_role.html', form=form, title='新規ロール追加')

@bp.route('/roles/edit/<int:role_id>', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def edit_role(role_id):
    """既存のロールを編集する"""
    from app.forms import RoleForm
    role = db.session.get(Role, role_id)
    if role is None:
        flash('ロールが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.manage_roles'))
    
    form = RoleForm(obj=role, original_name=role.name)
    if form.validate_on_submit():
        role.name = form.name.data
        role.description = form.description.data
        db.session.commit()
        flash('ロール情報が更新されました。', 'success')
        return redirect(url_for('blog_admin_bp.manage_roles'))
    
    return render_template('roles/add_edit_role.html', form=form, role=role, title='ロール編集')

@bp.route('/roles/delete/<int:role_id>', methods=['POST'])
@login_required
@roles_required('admin')
def delete_role(role_id):
    """ロールを削除する"""
    role_to_delete = db.session.get(Role, role_id)
    if role_to_delete is None:
        flash('ロールが見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.manage_roles'))

    # ロールに属するユーザーがいる場合は削除させない
    if role_to_delete.users.count() > 0:
        flash('このロールにはユーザーが割り当てられているため、削除できません。', 'warning')
        return redirect(url_for('blog_admin_bp.manage_roles'))

    # 基本的なロール(admin, userなど)は削除させない等の追加チェックも可能
    if role_to_delete.name in ['admin', 'user', 'poster']:
        flash(f'基本的なロール \'{role_to_delete.name}\' は削除できません。', 'warning')
        return redirect(url_for('blog_admin_bp.manage_roles'))

    try:
        db.session.delete(role_to_delete)
        db.session.commit()
        flash('ロールが削除されました。', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'ロールの削除中にエラーが発生しました: {e}', 'danger')
    
    return redirect(url_for('blog_admin_bp.manage_roles'))

@bp.route('/posts/toggle_publish/<uuid:post_id>', methods=['POST'])
@login_required
def toggle_publish(post_id):
    # 手動の権限チェック
    required_roles = ['admin', 'editor', 'poster']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    post = db.session.get(Post, post_id)
    if not post:
        flash('投稿が見つかりません。', 'danger')
        return redirect(url_for('blog_admin_bp.list_posts'))
    post.is_published = not post.is_published
    db.session.commit()
    flash('公開状態を切り替えました。', 'success')
    return redirect(url_for('blog_admin_bp.list_posts'))

# ユーザー追加ルート
@bp.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    # 手動の権限チェック
    required_roles = ['admin']
    if not any(Permission(RoleNeed(role_name)).can() for role_name in required_roles):
        flash('アクセス権限がありません。', 'danger')
        abort(403) # または redirect(url_for('home.index')) など

    form = UserEditForm()
    form.roles.choices = [(str(r.id), r.name) for r in Role.query.order_by(Role.name).all()]

    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            active=form.is_active.data
        )
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data)
        if form.roles.data:
            user.roles = form.roles.data
        db.session.add(user)
        db.session.commit()
        flash('ユーザーが追加されました。', 'success')
        return redirect(url_for('blog_admin_bp.list_users'))

    return render_template('users/edit_user.html', form=form, title='ユーザー追加')


