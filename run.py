# F:\dev\BrogDev\run.py

from app import create_app
from config import Config # Configをインポート

# Flaskアプリケーションのインスタンスを作成
app = create_app(Config) 

if __name__ == '__main__':
    # デバッグモードを有効にする（開発中のみ）
    app.debug = True 
    
    # ★修正点: host='0.0.0.0' を追加して、外部からのアクセスを許可する★
    # '0.0.0.0' は、サーバーが利用可能な全てのネットワークインターフェースからの接続を受け入れることを意味します。
    # port は適宜変更可能です。
    app.run(host='0.0.0.0', port=5001)