import os
import hashlib
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json

app = Flask(__name__)
CORS(app)

# ============================================================
#   НАСТРОЙКИ TURSO
# ============================================================
DB_URL = "https://lumoba-cursedd.aws-eu-west-1.turso.io/v1/query"
DB_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3ODQ0MTAwMDksImlkIjoiMDE5Zjc3MWYtOTQwMS03ZjFkLWE3ZWUtYjEyYzVjYjI4NTA3Iiwia2lkIjoicWpYbEhLbElGQmJNX29uRDlaWEkyWFVfazVBT3h3X3JIMF9TcUZ6MmU0ZyIsInJpZCI6ImIxMDIxMzYxLWQ3ZGEtNGMzNC05MWQ4LWVjMTU4ZGUwNmU2ZCJ9.GBhD9cLc9UJvMUL1hK6lixqtZ1MwPLbII9fXgaYG2txsUUn9NRkI-5W3r3PXRJHgfFrEUbNT_52pOx4JV6bmDA"

def query_db(sql):
    """Отправка запроса в Turso"""
    print(f"🔍 SQL: {sql[:200]}")
    
    try:
        response = requests.post(
            DB_URL,
            headers={
                'Authorization': f'Bearer {DB_TOKEN}',
                'Content-Type': 'application/json'
            },
            json={
                'statements': [{'sql': sql}]
            },
            timeout=30
        )
        
        print(f"📊 Статус: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Ошибка: {response.text}")
            return {'error': f'HTTP {response.status_code}: {response.text[:200]}'}
        
        data = response.json()
        print(f"✅ Успешно: {json.dumps(data)[:200]}")
        return data
        
    except Exception as e:
        print(f"💥 Исключение: {str(e)}")
        return {'error': str(e)}

# ============================================================
#   ИНИЦИАЛИЗАЦИЯ
# ============================================================
def init_db():
    print("🔄 СОЗДАНИЕ ТАБЛИЦЫ...")
    
    sql = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        rank TEXT DEFAULT 'Бронза',
        level INTEGER DEFAULT 1,
        gold INTEGER DEFAULT 500
    )
    """
    
    result = query_db(sql)
    
    if 'error' in result:
        print(f"❌ ОШИБКА: {result['error']}")
        return False
    
    print("✅ ТАБЛИЦА ГОТОВА")
    return True

# ============================================================
#   API
# ============================================================

@app.route('/')
def home():
    return jsonify({
        'status': 'ok',
        'message': 'Lumoba API работает!'
    })

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        print(f"📝 РЕГИСТРАЦИЯ: {username}")
        
        if not username or not password:
            return jsonify({'error': 'Заполните все поля'}), 400
        
        # Проверяем существование
        check = query_db(f"SELECT id FROM users WHERE username = '{username}'")
        rows = check.get('results', [{}])[0].get('response', {}).get('result', {}).get('rows', [])
        
        if rows:
            return jsonify({'error': 'Пользователь уже существует'}), 400
        
        # Хешируем пароль
        hashed = hashlib.sha256(password.encode()).hexdigest()
        
        # Создаём пользователя
        sql = f"INSERT INTO users (username, password) VALUES ('{username}', '{hashed}')"
        result = query_db(sql)
        
        if 'error' in result:
            print(f"❌ Ошибка вставки: {result}")
            return jsonify({'error': 'Ошибка базы данных при создании'}), 500
        
        print(f"✅ ПОЛЬЗОВАТЕЛЬ СОЗДАН: {username}")
        return jsonify({'success': True, 'message': 'Аккаунт создан!'})
        
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        print(f"📝 ВХОД: {username}")
        
        if not username or not password:
            return jsonify({'error': 'Заполните все поля'}), 400
        
        hashed = hashlib.sha256(password.encode()).hexdigest()
        
        sql = f"SELECT id, username, rank, level, gold FROM users WHERE username = '{username}' AND password = '{hashed}'"
        result = query_db(sql)
        
        rows = result.get('results', [{}])[0].get('response', {}).get('result', {}).get('rows', [])
        
        if not rows:
            return jsonify({'error': 'Неверный логин или пароль'}), 401
        
        user = rows[0]
        return jsonify({
            'success': True,
            'user': {
                'id': user[0],
                'username': user[1],
                'rank': user[2],
                'level': user[3],
                'gold': user[4]
            }
        })
        
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/top', methods=['GET'])
def get_top():
    try:
        result = query_db("SELECT username, kills, rank, level FROM users ORDER BY kills DESC LIMIT 10")
        rows = result.get('results', [{}])[0].get('response', {}).get('result', {}).get('rows', [])
        
        return jsonify([{
            'username': row[0],
            'kills': row[1] if len(row) > 1 else 0,
            'rank': row[2] if len(row) > 2 else 'Бронза',
            'level': row[3] if len(row) > 3 else 1
        } for row in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================
#   ЗАПУСК
# ============================================================
if __name__ == '__main__':
    print("🚀 ЗАПУСК СЕРВЕРА...")
    init_db()
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 ПОРТ: {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
