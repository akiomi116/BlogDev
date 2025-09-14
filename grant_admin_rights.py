from app import create_app
from app.extensions import db
from app.models import User, Role

# Flaskアプリケーションのインスタンスを作成し、アプリケーションコンテキストをプッシュ
app = create_app()
with app.app_context():
    try:
        # 1. 'admin' ロールを取得または作成
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            print("Admin role not found, creating it...")
            admin_role = Role(name='admin', description='Administrator')
            db.session.add(admin_role)
        
        # 2. 'user' ロールもついでに作成
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            print("User role not found, creating it...")
            user_role = Role(name='user', description='Standard user')
            db.session.add(user_role)

        # 3. 'poster' ロールもついでに作成
        poster_role = Role.query.filter_by(name='poster').first()
        if not poster_role:
            print("Poster role not found, creating it...")
            poster_role = Role(name='poster', description='User who can post')
            db.session.add(poster_role)

        # 先にロールをコミット
        db.session.commit()
        print("Roles created or found.")

        # 4. 対象のユーザーを取得
        target_email = 'akiomi.nishimura@gmail.com'
        user = User.query.filter_by(email=target_email).first()

        if user:
            # 5. ユーザーに 'admin' ロールを割り当て
            admin_role = Role.query.filter_by(name='admin').first() # 再取得
            if admin_role not in user.roles:
                user.roles.append(admin_role)
                print(f"Assigning admin role to {user.email}...")
                db.session.commit()
                print("Successfully assigned admin role.")
            else:
                print(f"{user.email} already has the admin role.")
        else:
            print(f"User with email '{target_email}' not found.")

    except Exception as e:
        print(f"An error occurred: {e}")
        db.session.rollback()
    finally:
        print("Script finished.")
