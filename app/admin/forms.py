# F:\dev\BrogDev\app\admin\forms.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, BooleanField, MultipleFileField, SelectMultipleField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, Optional, Regexp
from app.models import User, Category, Tag, Role, Image # モデルをインポート
from flask_login import current_user # フォーム内でcurrent_userを使うため
from flask import current_app # ロギングのため
from app import db # db インスタンスをインポート。Role.query などで必要


# --- ユーザー関連フォーム (管理者用) ---
class UserForm(FlaskForm):
    username = StringField('ユーザー名', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    password = PasswordField('パスワード', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('パスワードの確認', validators=[Optional(), EqualTo('password', message='パスワードが一致しません。')])
    role_id = SelectField('役割', coerce=str, validators=[DataRequired()])
    is_active = BooleanField('アクティブ')
    submit = SubmitField('保存')

    def __init__(self, *args, **kwargs):
        self.obj = kwargs.get('obj', None)
        super(UserForm, self).__init__(*args, **kwargs)
        # ロールの選択肢を設定
        self.role_id.choices = [(str(role.id), role.name) for role in Role.query.order_by(Role.name.asc()).all()]

    def validate_username(self, username):
        if self.obj and username.data == self.obj.username:
            return
def __init__(self, *args, **kwargs):
    self.obj = kwargs.get('obj', None)
    super(CategoryForm, self).__init__(*args, **kwargs)

def validate_name(self, name):
    if self.obj and name.data == self.obj.name:
        return

    # 管理者は全カテゴリの一意性を検証
    category = Category.query.filter_by(name=name.data).first()
    if category:
        raise ValidationError('そのカテゴリ名はすでに存在します。')

def validate_slug(self, slug):
    if not slug.data:
        return

    if self.obj and slug.data == self.obj.slug:
        return

    # 管理者は全スラッグの一意性を検証
    category = Category.query.filter_by(slug=slug.data).first()
    if category:
        raise ValidationError('そのスラッグはすでに存在します。')
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('そのユーザー名はすでに使われています。別のユーザー名を選んでください。')

    def validate_email(self, email):
        if self.obj and email.data == self.obj.email:
            return

        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('そのメールアドレスはすでに登録されています。')

# --- ロール関連フォーム (管理者用) ---
class RoleForm(FlaskForm):
    name = StringField('ロール名', validators=[DataRequired(), Length(min=2, max=50)])
    description = TextAreaField('説明', validators=[Length(max=200)])
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
    submit = SubmitField('削除')

# ユーザーのロールを変更するためのフォームです。
class UserRoleForm(FlaskForm):
    role = SelectField('ロール', coerce=str, validators=[DataRequired()])
    submit = SubmitField('ロールを更新')


# --- 投稿関連フォーム (管理者・編集者用) ---
class PostForm(FlaskForm):
    title = StringField('タイトル', validators=[DataRequired(), Length(min=1, max=255)])
    body = TextAreaField('本文', validators=[DataRequired()])

    # ギャラリーから選択された画像のIDを保持する HiddenField
    main_image_upload = FileField('メイン画像アップロード', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif'], '画像ファイルのみ')])
    selected_image_id = HiddenField('選択画像ID')
    
    main_image_file = FileField('新しいメイン画像をアップロード (任意)', validators=[
        FileAllowed(['jpg', 'png', 'jpeg', 'gif', 'webp'], '画像ファイル (JPG, PNG, JPEG, GIF, WEBP) のみアップロード可能です！'),
        Optional()
    ])
    main_image_alt_text = StringField('メイン画像の代替テキスト (alt)', validators=[Optional(), Length(max=255)])

    main_image = SelectField('既存のメイン画像を選択 (任意)', coerce=str, validators=[Optional()])
    additional_images = SelectMultipleField('追加画像 (複数選択可)', coerce=str, validators=[Optional()])

    is_published = BooleanField('公開する', default=False)

    category = SelectField('カテゴリ', coerce=str, validators=[Optional()])
    tags = SelectMultipleField('タグ (Ctrl/Cmdキーで複数選択)', coerce=str, validators=[Optional()])

    submit = SubmitField('保存')

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.obj = kwargs.get('obj')

        # カテゴリの選択肢を設定 (管理者は全てのカテゴリを、編集者は自身のカテゴリを対象にすることも可能だが、ここでは全てのカテゴリを対象)
        categories = Category.query.order_by(Category.name.asc()).all()
        self.category.choices = [('', 'カテゴリなし')] + [(str(c.id), c.name) for c in categories]

        # タグの選択肢を設定 (管理者は全てのタグを、編集者は自身のタグを対象にすることも可能だが、ここでは全てのタグを対象)
        tags = Tag.query.order_by(Tag.name.asc()).all()
        self.tags.choices = [(str(t.id), t.name) for t in tags]

        # 画像の選択肢を設定 (メイン画像および追加画像用)
        # 管理者は全ての画像を、編集者は自身の画像を閲覧できるように調整
        if current_user.is_authenticated:
            if current_user.has_role('admin'):
                images = Image.query.order_by(Image.unique_filename.asc()).all()
            else: # 編集者などの場合
                images = Image.query.filter_by(user_id=current_user.id).order_by(Image.unique_filename.asc()).all()
        else:
            images = [] # 認証されていない場合は画像なし

        self.main_image.choices = [('', 'なし')] + [(str(img.id), img.unique_filename) for img in images]
        self.additional_images.choices = [(str(img.id), img.unique_filename) for img in images]

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False
        if not self.main_image_upload.data and not self.selected_image_id.data:
            self.main_image_upload.errors.append('メイン画像は必須です。ファイルをアップロードするか、ギャラリーから選択してください。')
            return False
        return True


# --- カテゴリ関連フォーム (管理者・編集者用) ---
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

        # 管理者は全カテゴリの一意性を検証
        category = Category.query.filter_by(name=name.data).first()
        if category:
            raise ValidationError('そのカテゴリ名はすでに存在します。')

    def validate_slug(self, slug):
        if not slug.data:
            return

        if self.obj and slug.data == self.obj.slug:
            return

        # 管理者は全スラッグの一意性を検証
        category = Category.query.filter_by(slug=slug.data).first()
        if category:
            raise ValidationError('そのスラッグはすでに存在します。')


# --- タグ関連フォーム (管理者・編集者用) ---
class TagForm(FlaskForm):
    name = StringField('タグ名', validators=[DataRequired(), Length(min=2, max=50)])
    slug = StringField('スラッグ', validators=[
        Optional(),
        Length(max=128),
        Regexp(r'^[a-z0-9-]+$', message="スラッグは半角英数字とハイフンのみを使用してください。"),
    ])
    description = TextAreaField('説明', validators=[Length(max=200)]) 
    submit = SubmitField('保存')

    def __init__(self, *args, **kwargs):
        self.obj = kwargs.get('obj', None)
        super(TagForm, self).__init__(*args, **kwargs)

    def validate_name(self, name):
        if self.obj and name.data == self.obj.name:
            return

        # 管理者は全タグの一意性を検証
        tag = Tag.query.filter_by(name=name.data).first()
        if tag:
            raise ValidationError('そのタグ名はすでに存在します。')

    def validate_slug(self, slug):
        if not slug.data:
            return

        if self.obj and slug.data == self.obj.slug:
            return

        # 管理者は全スラッグの一意性を検証
        tag = Tag.query.filter_by(slug=slug.data).first()
        if tag:
            raise ValidationError('そのスラッグはすでに存在します。')

# --- 画像アップロードフォーム (単一ファイル) (管理者・編集者用) ---
class ImageUploadForm(FlaskForm):
    image_file = FileField('画像ファイル', validators=[
        DataRequired(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], '画像ファイル (JPG, JPEG, PNG, GIF, WEBP) のみ許可されます')
    ])
    alt_text = StringField('代替テキスト (alt)', validators=[Optional(), Length(max=255)])
    submit = SubmitField('アップロード')

# --- 一括画像アップロードフォーム (管理者・編集者用) ---
class BulkImageUploadForm(FlaskForm):
    image_files = MultipleFileField('画像ファイルを選択 (複数可)', validators=[
        DataRequired(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], '画像ファイル (JPG, JPEG, PNG, GIF, WEBP) のみ許可されます')
    ])
    submit = SubmitField('一括アップロード')


# --- 管理画面用コメント管理フォーム (承認/編集用) ---
class AdminCommentForm(FlaskForm): # 名前をAdminCommentFormに変更
    body = TextAreaField('コメント本文', validators=[DataRequired()])
    approved = BooleanField('承認済み')
    submit = SubmitField('更新')

# QRコード管理用のフォーム (管理画面専用と想定)
class QRForm(FlaskForm):
    name = StringField('QRコード名', validators=[DataRequired(), Length(min=1, max=100)])
    url = StringField('URL', validators=[DataRequired(), Length(min=1, max=500)])
    submit = SubmitField('QRコードを作成/更新')