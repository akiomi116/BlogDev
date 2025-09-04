from app import create_app, db
from app.models import Post

app = create_app()
with app.app_context():
    print(Post.query.count())