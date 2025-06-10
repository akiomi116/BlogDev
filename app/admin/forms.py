# F:\dev\BrogDev\app\admin\forms.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, BooleanField, MultipleFileField, SelectMultipleField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, Optional
from app.models import User, Category, Tag, Role, Image # Image モデルをインポート
from flask_login import current_user
from flask import current_app # current_app をインポート

# logger = logging.getLogger(__name__) # この行は不要、代わりに current_app.logger を使用

# --- ユーザー関連フォーム ---
class UserForm(FlaskForm):
    username = StringField('ユーザー名', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    password = PasswordField('パスワード', validators=[Optional(), Length(min=6)]) # 新規作成時のみ必須、編集時は任意
    confirm_password = PasswordField('パスワードの確認', validators=[Optional(), EqualTo('password', message='パスワードが一致しません。')])
    roles = SelectMultipleField('ロール', coerce=str, validators=[DataRequired()]) # 複数のロールを選択可能にする

    submit = SubmitField('保存')

    # 新規作成時のバリデーション（edit_userではobj=userが渡されるため、user_idで既存ユーザーを区別）
    def __init__(self, *args, **kwargs):
        self.original_username = kwargs.pop('original_username', None)
        self.original_email = kwargs.pop('original_email', None)
        super(UserForm, self).__init__(*args, **kwargs)

    def validate_username(self, username):
        if username.data != self.original_username: # 編集時でユーザー名が変更された場合のみチェック
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('そのユーザー名はすでに使われています。別のユーザー名を選んでください。')

    def validate_email(self, email):
        if email.data != self.original_email: # 編集時でメールアドレスが変更された場合のみチェック
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('そのメールアドレスはすでに登録されています。')

# --- ロール関連フォーム ---
class RoleForm(FlaskForm):
    name = StringField('ロール名', validators=[DataRequired(), Length(min=2, max=50)])
    submit = SubmitField('保存')

    def __init__(self, *args, **kwargs):
        self.original_name = kwargs.pop('original_name', None)
        super(RoleForm, self).__init__(*args, **kwargs)

    def validate_name(self, name):
        if name.data != self.original_name:
            role = Role.query.filter_by(name=name.data).first()
            if role:
                raise ValidationError('そのロール名はすでに存在します。')

# --- 投稿関連フォーム ---
class PostForm(FlaskForm):
    title = StringField('タイトル', validators=[DataRequired(), Length(min=1, max=255)])
    body = TextAreaField('本文', validators=[DataRequired()])
    
    # 新しいメイン画像をアップロードするためのフィールド (FileField)
    main_image_file = FileField('新しいメイン画像をアップロード (任意)', validators=[
        FileAllowed(['jpg', 'png', 'jpeg', 'gif'], '画像ファイル (JPG, PNG, JPEG, GIF) のみアップロード可能です！'),
        Optional() # アップロードは任意
    ])
    
    # 既存のメイン画像を選択するためのフィールド (SelectField)
    main_image = SelectField('既存のメイン画像を選択 (任意)', coerce=str, validators=[Optional()])
    
    # 追加画像も既存から選択
    additional_images = SelectMultipleField('追加画像 (複数選択可)', coerce=str, validators=[Optional()]) 
    
    is_published = BooleanField('公開する', default=False)
    
    category = SelectField('カテゴリ', coerce=str, validators=[Optional()])
    tags = SelectMultipleField('タグ (Ctrl/Cmdキーで複数選択)', coerce=str, validators=[Optional()])
    
    submit = SubmitField('保存')

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        
        # カテゴリの選択肢をデータベースから取得
        if current_user.is_authenticated:
            if hasattr(current_user, 'role') and current_user.role and current_user.role.name == 'Admin':
                categories = Category.query.order_by(Category.name.asc()).all()
                current_app.logger.debug(f"DEBUG(PostForm): Admin user {current_user.username} fetching all categories.")
            else:
                categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name.asc()).all()
                current_app.logger.debug(f"DEBUG(PostForm): User {current_user.username} fetching their own categories.")
        else:
            categories = []
            current_app.logger.debug("DEBUG(PostForm): Anonymous user, no categories loaded.")
        self.category.choices = [('', 'カテゴリなし')] + [(str(c.id), c.name) for c in categories]
        current_app.logger.debug(f"DEBUG(PostForm): Loaded {len(self.category.choices) - 1} categories for SelectField. Choices: {self.category.choices}")

        # タグの選択肢をデータベースから取得
        if current_user.is_authenticated:
            # タグはユーザーに紐づかない共通のものが想定されるため、role.nameによる分岐は不要かもしれません
            # ただし、もしユーザーごとのタグがある場合は、User.idでフィルタリングを適用
            tags = Tag.query.order_by(Tag.name.asc()).all()
            current_app.logger.debug(f"DEBUG(PostForm): User {current_user.username} fetching all tags.")
        else:
            tags = []
            current_app.logger.debug("DEBUG(PostForm): Anonymous user, no tags loaded.")
        self.tags.choices = [(str(t.id), t.name) for t in tags]
        current_app.logger.debug(f"DEBUG(PostForm): Loaded {len(self.tags.choices)} tags for SelectMultipleField. Choices: {self.tags.choices}")

        # 画像の選択肢をデータベースから取得 (unique_filename を使用)
        if current_user.is_authenticated:
            # 管理者の場合、全ての画像を読み込む
            if hasattr(current_user, 'role') and current_user.role and current_user.role.name == 'Admin':
                images = Image.query.order_by(Image.unique_filename.asc()).all() # ★ここを修正しました★
                current_app.logger.debug(f"DEBUG(PostForm): Admin user {current_user.username} fetching all images.")
            else:
                # 一般ユーザーの場合、自分がアップロードした画像のみを読み込む
                images = Image.query.filter_by(user_id=current_user.id).order_by(Image.unique_filename.asc()).all() # ★ここを修正しました★
                current_app.logger.debug(f"DEBUG(PostForm): User {current_user.username} fetching their own images.")
        else:
            images = []
            current_app.logger.debug("DEBUG(PostForm): Anonymous user, no images loaded.")
            
        self.main_image.choices = [('', 'なし')] + [(str(img.id), img.unique_filename) for img in images] # ★ここを修正しました★
        self.additional_images.choices = [(str(img.id), img.unique_filename) for img in images] # ★ここを修正しました★
        current_app.logger.debug(f"DEBUG(PostForm): Loaded {len(self.main_image.choices) - 1} main images and {len(self.additional_images.choices)} additional images for SelectFields.")

# --- カテゴリ関連フォーム ---
class CategoryForm(FlaskForm):
    name = StringField('カテゴリ名', validators=[DataRequired(), Length(min=2, max=50)])
    submit = SubmitField('保存')

    def __init__(self, *args, **kwargs):
        self.original_name = kwargs.pop('original_name', None)
        super(CategoryForm, self).__init__(*args, **kwargs)

    def validate_name(self, name):
        if name.data != self.original_name:
            category = Category.query.filter_by(name=name.data).first()
            if category:
                raise ValidationError('そのカテゴリ名はすでに存在します。')

# --- タグ関連フォーム ---
class TagForm(FlaskForm):
    name = StringField('タグ名', validators=[DataRequired(), Length(min=2, max=50)])
    submit = SubmitField('保存')

    def __init__(self, *args, **kwargs):
        self.original_name = kwargs.pop('original_name', None)
        super(TagForm, self).__init__(*args, **kwargs)

    def validate_name(self, name):
        if name.data != self.original_name:
            tag = Tag.query.filter_by(name=name.data).first()
            if tag:
                raise ValidationError('そのタグ名はすでに存在します。')

# --- 画像アップロードフォーム (単一ファイル) ---
class ImageUploadForm(FlaskForm):
    image_file = FileField('画像ファイル', validators=[
        DataRequired(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], '画像ファイル (JPG, JPEG, PNG, GIF, WEBP) のみ許可されます')
    ])
    alt_text = StringField('代替テキスト (alt)', validators=[Optional(), Length(max=255)])
    submit = SubmitField('アップロード')

# --- 一括画像アップロードフォーム ---
class BulkImageUploadForm(FlaskForm):
    image_files = MultipleFileField('画像ファイルを選択 (複数可)', validators=[
        DataRequired(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], '画像ファイル (JPG, JPEG, PNG, GIF, WEBP) のみ許可されます')
    ])
    submit = SubmitField('一括アップロード')

# --- コメント管理フォーム (承認/削除用) ---
class CommentForm(FlaskForm):
    # 管理者がコメントを編集する場合のフィールド。
    # 承認/却下、削除はPOSTリクエストで直接行うことが多いので、
    # このフォームはコメント内容を編集したい場合のために定義します。
    body = TextAreaField('コメント本文', validators=[DataRequired()])
    approved = BooleanField('承認済み')
    submit = SubmitField('更新')