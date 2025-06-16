# F:\dev\BrogDev\app\admin\forms.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, BooleanField, MultipleFileField, SelectMultipleField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, Optional, Regexp
from app.models import User, Category, Tag, Role, Image # Image モデルをインポート
from flask_login import current_user
from flask import current_app # current_app をインポート
import logging # ロギングを追加する場合に備えて

# logger = logging.getLogger(__name__) # この行は不要、代わりに current_app.logger を使用

# ログインフォーム
class LoginForm(FlaskForm):
    username = StringField('ユーザー名', validators=[DataRequired()])
    password = PasswordField('パスワード', validators=[DataRequired()])
    remember_me = BooleanField('ログイン情報を記憶する')
    submit = SubmitField('ログイン')

# 認証フォーム (新規登録など汎用的な認証操作用)
class AuthForm(FlaskForm):
    # これは例として定義していますが、実際の用途に応じて変更してください
    # 例えば、ユーザー登録フォームとして使う場合は以下のようなフィールドになります
    username = StringField('ユーザー名', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    password = PasswordField('パスワード', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        'パスワードの確認', validators=[DataRequired(), EqualTo('password', message='パスワードが一致しません。')]
    )
    submit = SubmitField('登録')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('そのユーザー名はすでに使われています。別のユーザー名を選んでください。')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('そのメールアドレスはすでに登録されています。')

# その他のフォームがあればここに追加
# 例: パスワードリセットリクエストフォーム
class RequestResetForm(FlaskForm):
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    submit = SubmitField('パスワードリセットをリクエスト')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('そのメールアドレスを持つアカウントはありません。登録してください。')

# 例: パスワードリセットフォーム
class ResetPasswordForm(FlaskForm):
    password = PasswordField('新しいパスワード', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        'パスワードの確認', validators=[DataRequired(), EqualTo('password', message='パスワードが一致しません。')]
    )
    submit = SubmitField('パスワードをリセット')




# --- ユーザー関連フォーム ---
class UserForm(FlaskForm):
    username = StringField('ユーザー名', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    password = PasswordField('パスワード', validators=[Optional(), Length(min=6)]) # 新規作成時のみ必須、編集時は任意
    confirm_password = PasswordField('パスワードの確認', validators=[Optional(), EqualTo('password', message='パスワードが一致しません。')])
    role_id = SelectField('ロール', coerce=str, validators=[DataRequired()]) # user.role_id に対応
    role = SelectField('役割', coerce=str, validators=[DataRequired()]) 

    submit = SubmitField('保存')

    def __init__(self, *args, **kwargs):
        self.obj = kwargs.get('obj', None)
        super(UserForm, self).__init__(*args, **kwargs)
        self.role_id.choices = [(str(role.id), role.name) for role in Role.query.order_by(Role.name.asc()).all()]

    def validate_username(self, username):
        if self.obj and username.data == self.obj.username:
            return

        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('そのユーザー名はすでに使われています。別のユーザー名を選んでください。')

    def validate_email(self, email):
        if self.obj and email.data == self.obj.email:
            return

        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('そのメールアドレスはすでに登録されています。')

# --- ロール関連フォーム ---
class RoleForm(FlaskForm):
    name = StringField('ロール名', validators=[DataRequired(), Length(min=2, max=50)])
    submit = SubmitField('保存')

    def __init__(self, *args, **kwargs):
        self.obj = kwargs.get('obj', None)
        super(RoleForm, self).__init__(*args, **kwargs)

    def validate_name(self, name):
        if self.obj and name.data == self.obj.name:
            return

        role = Role.query.filter_by(name=name.data).first()
        if role:
            raise ValidationError('そのロール名はすでに存在します。')

class DeleteRoleForm(FlaskForm):
    pass


# --- 投稿関連フォーム ---
class PostForm(FlaskForm):
    title = StringField('タイトル', validators=[DataRequired(), Length(min=1, max=255)])
    body = TextAreaField('本文', validators=[DataRequired()])

    main_image_file = FileField('新しいメイン画像をアップロード (任意)', validators=[
        FileAllowed(['jpg', 'png', 'jpeg', 'gif', 'webp'], '画像ファイル (JPG, PNG, JPEG, GIF, WEBP) のみアップロード可能です！'),
        Optional()
    ])

    main_image = SelectField('既存のメイン画像を選択 (任意)', coerce=str, validators=[Optional()])

    additional_images = SelectMultipleField('追加画像 (複数選択可)', coerce=str, validators=[Optional()])

    is_published = BooleanField('公開する', default=False)

    category = SelectField('カテゴリ', coerce=str, validators=[Optional()])
    tags = SelectMultipleField('タグ (Ctrl/Cmdキーで複数選択)', coerce=str, validators=[Optional()])

    submit = SubmitField('保存')

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)

        if current_user.is_authenticated and current_user.has_role('admin'):
            categories = Category.query.order_by(Category.name.asc()).all()
            current_app.logger.debug(f"DEBUG(PostForm): admin user {current_user.username} fetching all categories.")
        elif current_user.is_authenticated:
            categories = Category.query.order_by(Category.name.asc()).all()
            current_app.logger.debug(f"DEBUG(PostForm): User {current_user.username} fetching categories.")
        else:
            categories = []
            current_app.logger.debug("DEBUG(PostForm): Anonymous user, no categories loaded.")
        self.category.choices = [('', 'カテゴリなし')] + [(str(c.id), c.name) for c in categories]
        current_app.logger.debug(f"DEBUG(PostForm): Loaded {len(self.category.choices) - 1} categories for SelectField. Choices: {self.category.choices}")

        if current_user.is_authenticated:
            tags = Tag.query.order_by(Tag.name.asc()).all()
            current_app.logger.debug(f"DEBUG(PostForm): User {current_user.username} fetching all tags.")
        else:
            tags = []
            current_app.logger.debug("DEBUG(PostForm): Anonymous user, no tags loaded.")
        self.tags.choices = [(str(t.id), t.name) for t in tags]
        current_app.logger.debug(f"DEBUG(PostForm): Loaded {len(self.tags.choices)} tags for SelectMultipleField. Choices: {self.tags.choices}")

        if current_user.is_authenticated:
            if current_user.has_role('admin'):
                images = Image.query.order_by(Image.unique_filename.asc()).all()
                current_app.logger.debug(f"DEBUG(PostForm): admin user {current_user.username} fetching all images.")
            else:
                images = Image.query.filter_by(user_id=current_user.id).order_by(Image.unique_filename.asc()).all()
                current_app.logger.debug(f"DEBUG(PostForm): User {current_user.username} fetching their own images.")
        else:
            images = []
            current_app.logger.debug("DEBUG(PostForm): Anonymous user, no images loaded.")

        self.main_image.choices = [('', 'なし')] + [(str(img.id), img.unique_filename) for img in images]
        self.additional_images.choices = [(str(img.id), img.unique_filename) for img in images]
        current_app.logger.debug(f"DEBUG(PostForm): Loaded {len(self.main_image.choices) - 1} main images and {len(self.additional_images.choices)} additional images for SelectFields.")

# --- カテゴリ関連フォーム ---
class CategoryForm(FlaskForm):
    name = StringField('カテゴリ名', validators=[DataRequired(), Length(min=2, max=100)])
    slug = StringField('スラッグ', validators=[Optional(), Length(min=2, max=100)])
    description = TextAreaField('説明', validators=[Length(max=500)])
    submit = SubmitField('保存')

    def __init__(self, *args, **kwargs):
        self.obj = kwargs.get('obj', None)
        super(CategoryForm, self).__init__(*args, **kwargs)

    def validate_name(self, name):
        if self.obj and name.data == self.obj.name:
            return

        category = Category.query.filter_by(name=name.data, user_id=current_user.id).first()
        if category:
            raise ValidationError('そのカテゴリ名はすでに存在します。')

    def validate_slug(self, slug):
        if not slug.data:
            return

        if self.obj and slug.data == self.obj.slug:
            return

        category = Category.query.filter_by(slug=slug.data, user_id=current_user.id).first()
        if category:
            raise ValidationError('そのスラッグはすでに存在します。')


# --- タグ関連フォーム ---
class TagForm(FlaskForm):
    name = StringField('タグ名', validators=[DataRequired(), Length(min=2, max=50)])
    slug = StringField('スラッグ', validators=[
        Optional(), # 必須でなければOptional()
        Length(max=128),
        Regexp(r'^[a-z0-9-]+$', message="スラッグは半角英数字とハイフンのみを使用してください。"),
    ])
    submit = SubmitField('保存')

    def __init__(self, *args, **kwargs):
        self.obj = kwargs.get('obj', None)
        super(TagForm, self).__init__(*args, **kwargs)

    def validate_name(self, name):
        if self.obj and name.data == self.obj.name:
            return

        tag = Tag.query.filter_by(name=name.data, user_id=current_user.id).first()
        if tag:
            raise ValidationError('そのタグ名はすでに存在します。')

    def validate_slug(self, slug):
        if not slug.data:
            return

        if self.obj and slug.data == self.obj.slug:
            return

        tag = Tag.query.filter_by(slug=slug.data, user_id=current_user.id).first()
        if tag:
            raise ValidationError('そのスラッグはすでに存在します。')

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
    body = TextAreaField('コメント本文', validators=[DataRequired()])
    approved = BooleanField('承認済み')
    submit = SubmitField('更新')
