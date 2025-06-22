# F:\dev\BrogDev\app\utils.py

import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename
from PIL import Image as PILImage # PIL.ImageをPILImageとしてインポート

import logging

logger = logging.getLogger(__name__)

# ヘルパー関数群で使用する定数
UPLOAD_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
THUMBNAIL_SIZE = (200, 200)

def allowed_file(filename):
    """許可されたファイル拡張子であるかを確認します。"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in UPLOAD_EXTENSIONS

def create_thumbnail(original_filepath):
    """
    指定された画像ファイルからサムネイルを生成し、サムネイルのファイル名を返します。
    失敗した場合は None を返します。
    """
    #current_app.logger.debug(f"DEBUG(utils): create_thumbnail called for original_filepath: {original_filepath}")

    thumbnail_dir = current_app.config['THUMBNAIL_FOLDER']
    #current_app.logger.debug(f"DEBUG(utils): Thumbnail storage directory: {thumbnail_dir}")

    if not os.path.exists(thumbnail_dir):
        os.makedirs(thumbnail_dir)
        #current_app.logger.debug(f"DEBUG(utils): Thumbnail directory created: {thumbnail_dir}")
    else:
        current_app.logger.debug(f"DEBUG(utils): Thumbnail directory ensured: {thumbnail_dir}")

    try:
        img = PILImage.open(original_filepath)
        
        # original_filepath は unique_filename を含むパスなので、
        # ファイル名から拡張子を除いた部分がUUIDとなる
        filename_without_ext = os.path.splitext(os.path.basename(original_filepath))[0]
        uuid_part = filename_without_ext 

        thumb_filename = f"thumb_{uuid_part}.png" # サムネイルは常にPNGとして保存
        
        full_thumbnail_path = os.path.join(thumbnail_dir, thumb_filename)
        #current_app.logger.debug(f"DEBUG(utils): Full thumbnail path: {full_thumbnail_path}")

        img.thumbnail(THUMBNAIL_SIZE, PILImage.Resampling.LANCZOS)
        
        if img.mode == 'RGBA':
            img = img.convert('RGB') # RGBAモードの画像をPNGで保存する際に変換は不要ですが、念のためRGBに変換

        img.save(full_thumbnail_path, format='PNG')
        #current_app.logger.debug(f"DEBUG(utils): Thumbnail saved successfully to: {full_thumbnail_path}")

        return thumb_filename

    except Exception as e:
        current_app.logger.error(f"ERROR(utils): Error creating thumbnail for {original_filepath}: {e}", exc_info=True)
        return None

def delete_file(filename, folder_path):
    """指定されたフォルダからファイルを削除します。"""
    file_path = os.path.join(folder_path, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            current_app.logger.info(f"INFO(utils): File deleted: {file_path}")
            return True
        except Exception as e:
            current_app.logger.error(f"ERROR(utils): Error deleting file {file_path}: {e}", exc_info=True)
            return False
    else:
        current_app.logger.warning(f"WARNING(utils): File not found for deletion: {file_path}")
        return False

def save_image_and_thumbnail(image_file, upload_folder, thumbnail_folder, user_id):
    """
    画像を保存し、サムネイルを生成して、関連情報を辞書で返します。
    失敗した場合は None を返します。
    """
    if not image_file or not image_file.filename or not allowed_file(image_file.filename):
        logger.warning(f"WARNING(utils): Invalid file provided to save_image_and_thumbnail: {image_file.filename if image_file else 'No file'}")
        return None

    original_filename = secure_filename(image_file.filename)
    unique_filename_uuid = str(uuid.uuid4())
    # 拡張子を取得
    file_extension = os.path.splitext(original_filename)[1]
    
    # DBに保存するユニークなファイル名
    unique_filename = f"{unique_filename_uuid}{file_extension}" 

    # ファイルのフルパス
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
    
    thumbnail_filename = None
    thumbnail_filepath = None

    try:
        # まず元画像を保存
        image_file.save(filepath)
        logger.debug(f"画像を保存しました: {filepath}")

        # サムネイルを生成するためにcreate_thumbnail関数を呼び出す
        generated_thumbnail_filename = create_thumbnail(filepath)
        
        if generated_thumbnail_filename:
            thumbnail_filename = generated_thumbnail_filename
            thumbnail_filepath = os.path.join(current_app.config['THUMBNAIL_FOLDER'], thumbnail_filename)
        else:
            logger.warning(f"WARNING(utils): Thumbnail could not be generated for {original_filename}. Original file will be deleted.")
            # サムネイル生成に失敗したらオリジナルも削除
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Cleanup: Deleted original file {filepath} due to thumbnail generation error.")
            return None # サムネイルが作れない場合は全体を失敗とみなす

        return {
            'original_filename': original_filename,
            'unique_filename': unique_filename,
            'filepath': filepath,
            'thumbnail_filename': thumbnail_filename,
            'thumbnail_filepath': thumbnail_filepath, # ここも追加
            'user_id': user_id
        }

    except Exception as e:
        logger.error(f"ERROR(utils): Error in save_image_and_thumbnail for {original_filename}: {e}", exc_info=True)
        # エラーが発生した場合は、保存済みのファイルを削除
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Cleanup: Deleted original file {filepath} due to error.")
        if thumbnail_filepath and os.path.exists(thumbnail_filepath):
            os.remove(thumbnail_filepath)
            logger.info(f"Cleanup: Deleted thumbnail {thumbnail_filepath} due to error.")
        return None