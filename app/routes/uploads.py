# F:\dev\BrogDev\app\routes\uploads.py

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, abort, jsonify
from flask_login import login_required, current_user
from app.models import Image
from app.extensions import db
from app.forms import ImageUploadForm, BulkImageUploadForm

from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename
from PIL import Image as PILImage
import os
import uuid
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

uploads_bp = Blueprint(
    'uploads',
    __name__,
    url_prefix='/admin/uploads',
    template_folder=os.path.join(os.path.abspath(os.path.dirname(__file__)), '../../admin/templates') 
)

# --- ファイル操作に関するユーティリティ関数 ---
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image_and_thumbnail(file, upload_folder, thumbnail_folder, user_id, thumbnail_size=(128, 128)):
    if file.filename == '':
        logger.warning("No file selected for upload.")
        return None
    try:
        original_filename = secure_filename(file.filename)
        extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{extension}"
        
        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(thumbnail_folder, exist_ok=True)

        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)

        thumbnail_filename = None
        thumbnail_filepath = None
        try:
            img = PILImage.open(file_path)
            img.thumbnail(thumbnail_size)
            thumbnail_filename = f"thumb_{uuid.uuid4().hex}.{extension}"
            thumbnail_filepath = os.path.join(thumbnail_folder, thumbnail_filename)
            img.save(thumbnail_filepath)
            logger.info(f"Thumbnail created for {unique_filename}")
        except Exception as e:
            logger.error(f"Failed to create thumbnail for {unique_filename}: {e}", exc_info=True)

        return {
            'original_filename': original_filename,
            'unique_filename': unique_filename,
            'thumbnail_filename': thumbnail_filename,
            'filepath': file_path,
            'thumbnail_filepath': thumbnail_filepath,
            'user_id': user_id
        }
    except Exception as e:
        logger.error(f"Error saving image or creating thumbnail for {file.filename}: {e}", exc_info=True)
        return None

def delete_file(filename, folder):
    file_path = os.path.join(folder, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Deleted file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}", exc_info=True)
            return False
    else:
        logger.warning(f"Attempted to delete non-existent file: {file_path}")
        return False

# --- ルート定義 ---

@uploads_bp.route('/images', methods=['GET'])
@login_required
def manage_images():
    if not current_user.is_authenticated or \
       not hasattr(current_user, 'role') or \
       not current_user.role or \
       current_user.role.name not in ['admin', 'poster']:
        flash('この操作を行う権限がありません。', 'danger')
        current_app.logger.warning(f"ACCESS_DENIED: User {current_user.id if current_user.is_authenticated else 'Anonymous'} attempted to access manage_images without sufficient role.")
        abort(403)

    if current_user.role.name == 'admin':
        images = Image.query.order_by(Image.uploaded_at.desc()).all()
    else:
        images = Image.query.filter_by(user_id=current_user.id).order_by(Image.uploaded_at.desc()).all()

    form = FlaskForm()
    # ★修正: 'admin/manage_images.html' から 'manage_images.html' に変更
    return render_template('manage_images.html', form=form, images=images)

@uploads_bp.route('/images/upload_single', methods=['GET'])
@login_required
def show_upload_single_form():
    if not current_user.is_authenticated or \
       not hasattr(current_user, 'role') or \
       not current_user.role or \
       current_user.role.name not in ['admin', 'poster']:
        flash('この操作を行う権限がありません。', 'danger')
        current_app.logger.warning(f"ACCESS_DENIED: User {current_user.id} attempted to show_upload_single_form without sufficient role.")
        abort(403)

    form = ImageUploadForm()
    # ★修正: 'admin/upload_single_image.html' から 'upload_single_image.html' に変更
    return render_template('upload_single_image.html', form=form) 

@uploads_bp.route('/images/upload_single', methods=['POST'])
@login_required
def upload_single_image():
    if not current_user.is_authenticated or \
       not hasattr(current_user, 'role') or \
       not current_user.role or \
       current_user.role.name not in ['admin', 'poster']:
        flash('この操作を行う権限がありません。', 'danger')
        current_app.logger.warning(f"ACCESS_DENIED: User {current_user.id} attempted to upload_single_image without sufficient role.")
        abort(403)

    form = ImageUploadForm()

    if form.validate_on_submit():
        image_file = form.image_file.data
        if image_file and allowed_file(image_file.filename):
            try:
                image_info = save_image_and_thumbnail(
                    image_file, 
                    current_app.config['UPLOAD_FOLDER'], 
                    current_app.config['THUMBNAIL_FOLDER'],
                    current_user.id
                )
                
                if image_info:
                    new_image = Image(
                        original_filename=image_info['original_filename'],
                        unique_filename=image_info['unique_filename'],
                        filepath=image_info['filepath'], 
                        thumbnail_filepath=image_info['thumbnail_filepath'], 
                        thumbnail_filename=image_info['thumbnail_filename'],
                        user_id=image_info['user_id']
                    )
                    
                    db.session.add(new_image)
                    db.session.commit()
                    flash('画像が正常にアップロードされました。', 'success')
                    current_app.logger.info(f"Image '{image_file.filename}' uploaded successfully by user {current_user.id}. Unique filename: {image_info['unique_filename']}")
                    return redirect(url_for('uploads.manage_images'))
                else:
                    flash('画像の保存中に予期せぬエラーが発生しました。', 'danger')
                    current_app.logger.error(f"save_image_and_thumbnail returned None for {image_file.filename}")
            except Exception as e:
                db.session.rollback()
                flash(f'画像のアップロード中にエラーが発生しました: {e}', 'danger')
                current_app.logger.error(f"Error uploading image: {e}", exc_info=True)
        else:
            flash('無効なファイル形式、またはファイルが選択されていません。', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{form[field].label.text}: {error}", 'danger')
        current_app.logger.warning(f"Single image upload form validation failed for user {current_user.id}. Errors: {form.errors}")

    # ★修正: 'admin/upload_single_image.html' から 'upload_single_image.html' に変更
    return render_template('upload_single_image.html', form=form)


@uploads_bp.route('/images/bulk_upload_form', methods=['GET'])
@login_required
def show_bulk_upload_form():
    if not current_user.is_authenticated or \
       not hasattr(current_user, 'role') or \
       not current_user.role or \
       current_user.role.name not in ['admin', 'poster']:
        flash('この操作を行う権限がありません。', 'danger')
        current_app.logger.warning(f"ACCESS_DENIED: User {current_user.id} attempted to show_bulk_upload_form without sufficient role.")
        abort(403)

    form = BulkImageUploadForm()
    # ★修正: 'admin/upload_images.html' から 'upload_images.html' に変更
    return render_template('upload_images.html', form=form)

@uploads_bp.route('/images/bulk_upload', methods=['POST'])
@login_required
def bulk_upload():
    if not current_user.is_authenticated or \
       not hasattr(current_user, 'role') or \
       not current_user.role or \
       current_user.role.name not in ['admin', 'poster']:
        flash('この操作を行う権限がありません。', 'danger')
        current_app.logger.warning(f"ACCESS_DENIED: User {current_user.id} attempted to bulk_upload without sufficient role.")
        abort(403)

    form = BulkImageUploadForm()
    
    if form.validate_on_submit():
        uploaded_count = 0
        error_count = 0
        files_to_commit = []

        for file in form.images.data:
            if file and file.filename and allowed_file(file.filename):
                try:
                    image_info = save_image_and_thumbnail(
                        file, 
                        current_app.config['UPLOAD_FOLDER'], 
                        current_app.config['THUMBNAIL_FOLDER'],
                        current_user.id
                    )
                    
                    if image_info:
                        new_image = Image(
                            original_filename=image_info['original_filename'],
                            unique_filename=image_info['unique_filename'],
                            filepath=image_info['filepath'], 
                            thumbnail_filepath=image_info['thumbnail_filepath'], 
                            thumbnail_filename=image_info['thumbnail_filename'],
                            user_id=image_info['user_id']
                        )
                        files_to_commit.append(new_image)
                        uploaded_count += 1
                    else:
                        flash(f"'{file.filename}' の保存中に予期せぬエラーが発生しました。", 'danger')
                        error_count += 1
                except Exception as e:
                    logger.error(f"Error processing file '{file.filename}': {e}", exc_info=True)
                    flash(f"'{file.filename}' のアップロード中にエラーが発生しました: {e}", 'danger')
                    error_count += 1
            else:
                flash(f"'{file.filename if file else 'ファイル'}' は無効な形式か、選択されていません。", 'warning')
                error_count += 1
        
        if files_to_commit:
            try:
                db.session.add_all(files_to_commit)
                db.session.commit()
                flash(f'{uploaded_count}個の画像が正常にアップロードされました。', 'success')
                current_app.logger.info(f"{uploaded_count} images bulk uploaded by user {current_user.id}.")
            except Exception as e:
                db.session.rollback()
                flash(f'データベース保存中にエラーが発生しました: {e}', 'danger')
                current_app.logger.error(f"Database commit error during bulk upload: {e}", exc_info=True)
                error_count += len(files_to_commit)
        elif uploaded_count == 0 and error_count == 0:
            flash('アップロードするファイルが選択されていませんでした。', 'warning')

        if error_count > 0:
            flash(f'{error_count}個の画像はアップロードに失敗しました。', 'danger')

        return redirect(url_for('uploads.manage_images'))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{form[field].label.text}: {error}", 'danger')
        current_app.logger.warning(f"Bulk image upload form validation failed for user {current_user.id}. Errors: {form.errors}")
        # ★修正: 'admin/upload_images.html' から 'upload_images.html' に変更
        return render_template('upload_images.html', form=form)


@uploads_bp.route('/images/delete/<uuid:image_id>', methods=['POST'])
@login_required
def delete_image(image_id):
    if not current_user.is_authenticated or \
       not hasattr(current_user, 'role') or \
       not current_user.role or \
       (current_user.role.name != 'admin' and current_user.id != image.user_id):
        flash('この操作を行う権限がありません。', 'danger')
        current_app.logger.warning(f"ACCESS_DENIED: User {current_user.id} attempted to delete image {image_id} (owner: {image.user_id}) without sufficient role.")
        abort(403)

    image = db.session.get(Image, image_id)
    if image is None:
        abort(404)

    try:
        delete_file(image.unique_filename, current_app.config['UPLOAD_FOLDER'])
        if image.thumbnail_filename:
            delete_file(image.thumbnail_filename, current_app.config['THUMBNAIL_FOLDER'])
        
        db.session.delete(image)
        db.session.commit()
        flash('画像が正常に削除されました。', 'success')
        current_app.logger.info(f"Image {image_id} (file: {image.unique_filename}) deleted by user {current_user.id}.")
    except Exception as e:
        db.session.rollback()
        flash(f'画像の削除中にエラーが発生しました: {e}', 'danger')
        current_app.logger.error(f"Error deleting image {image_id}: {e}", exc_info=True)
    
    return redirect(url_for('uploads.manage_images'))


@uploads_bp.route('/images/json', methods=['GET'])
@login_required
def list_images_json():
    if not current_user.is_authenticated or \
       not hasattr(current_user, 'role') or \
       not current_user.role or \
       current_user.role.name not in ['admin', 'poster']:
        return jsonify({"error": "Unauthorized"}), 403

    if current_user.role.name == 'admin':
        images = Image.query.order_by(Image.uploaded_at.desc()).all()
    else:
        images = Image.query.filter_by(user_id=current_user.id).order_by(Image.uploaded_at.desc()).all()

    images_data = []
    for img in images:
        images_data.append({
            'id': str(img.id),
            'original_filename': img.original_filename,
            'unique_filename': img.unique_filename,
            'url': img.url,
            'thumbnail_url': img.thumbnail_url
        })
    
    return jsonify({"images": images_data}), 200
