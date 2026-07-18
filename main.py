import os
import json
import hashlib
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import urllib.parse

app = Flask(__name__)
CORS(app)

# ============================================================
#   ПОДКЛЮЧЕНИЕ К TURSO ЧЕРЕЗ HTTP
# ============================================================
DB_URL = "https://lumoba-cursedd.aws-eu-west-1.turso.io/v1/query"
DB_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3ODQ0MTAwMDksImlkIjoiMDE5Zjc3MWYtOTQwMS03ZjFkLWE3ZWUtYjEyYzVjYjI4NTA3Iiwia2lkIjoicWpYbEhLbElGQmJNX29uRDlaWEkyWFVfazVBT3h3X3JIMF9TcUZ6MmU0ZyIsInJpZCI6ImIxMDIxMzYxLWQ3ZGEtNGMzNC05MWQ4LWVjMTU4ZGUwNmU2ZCJ9.GBhD9cLc9UJvMUL1hK6lixqtZ1MwPLbII9fXgaYG2txsUUn9NRkI-5W3r3PXRJHgfFrEUbNT_52pOx4JV6bmDA"

def query_db(sql):
    """Отправка SQL через HTTP API"""
    try:
        print(f"📝 Выполняем SQL: {sql[:100]}...")
        
        response = requests.post(
            DB_URL,
            headers={
                'Authorization': f'Bearer {DB_TOKEN}',
                'Content-Type': 'application/json'
            },
            json={
                'statements': [{'sql': sql}]
            },
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"❌ HTTP ошибка: {response.status_code}")
            print(f"Ответ: {response.text[:200]}")
            return {'error': f'HTTP {response.status_code}: {response.text[:100]}'}
        
        data = response.json()
        print(f"✅ Ответ получен")
        return data
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return {'error': str(e)}

# ============================================================
#   ИНИЦИАЛИЗАЦИЯ БД (создаём ТОЛЬКО таблицу users)
# ============================================================
def init_db():
    sql = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rank TEXT DEFAULT 'Бронза',
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            gold INTEGER DEFAULT 500,
            kills INTEGER DEFAULT 0,
            deaths INTEGER DEFAULT 0,
            class TEXT DEFAULT 'fighter',
            clan TEXT DEFAULT 'Без клана',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    result = query_db(sql)
    if 'error' in result:
        print(f"❌ Ошибка инициализации: {result['error']}")
        return False
    print("✅ База данных инициализирована")
    return True

# Инициализируем при старте
print("🔄 Инициализация базы данных...")
init_db()

# ============================================================
#   ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def extract_rows(result):
    """Извлекает строки из ответа Turso"""
    try:
        if 'error' in result:
            return []
        return result.get('results', [{}])[0].get('response', {}).get('result', {}).get('rows', [])
    except:
        return []

# ============================================================
#   API ЭНДПОИНТЫ
# ============================================================

@app.route('/')
def home():
    return jsonify({'status': 'ok', 'message': 'Lumoba API работает!'})

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        print(f"📝 Регистрация: {username}")
        
        if not username or not password:
            return jsonify({'error': 'Заполните все поля'}), 400
        
        # Проверяем существование
        check = query_db(f"SELECT id FROM users WHERE username = '{username}'")
        rows = extract_rows(check)
        
        if rows:
            return jsonify({'error': 'Пользователь уже существует'}), 400
        
        hashed = hash_password(password)
        
        # Создаём пользователя
        sql = f"INSERT INTO users (username, password) VALUES ('{username}', '{hashed}')"
        result = query_db(sql)
        
        if 'error' in result:
            print(f"❌ Ошибка вставки: {result}")
            return jsonify({'error': 'Ошибка базы данных'}), 500
        
        return jsonify({'success': True, 'message': 'Аккаунт создан!'})
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        print(f"📝 Вход: {username}")
        
        if not username or not password:
            return jsonify({'error': 'Заполните все поля'}), 400
        
        hashed = hash_password(password)
        
        sql = f"SELECT id, username, rank, level, exp, gold, kills, deaths, class, clan FROM users WHERE username = '{username}' AND password = '{hashed}'"
        result = query_db(sql)
        
        rows = extract_rows(result)
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
                'exp': user[4],
                'gold': user[5],
                'kills': user[6],
                'deaths': user[7],
                'class': user[8],
                'clan': user[9] if len(user) > 9 else 'Без клана'
            }
        })
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/top', methods=['GET'])
def get_top():
    try:
        result = query_db("SELECT username, kills, rank, level FROM users ORDER BY kills DESC LIMIT 10")
        rows = extract_rows(result)
        
        return jsonify([{
            'username': row[0],
            'kills': row[1],
            'rank': row[2],
            'level': row[3]
        } for row in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_stats', methods=['POST'])
def update_stats():
    try:
        data = request.json
        user_id = data.get('user_id')
        kills = data.get('kills', 0)
        deaths = data.get('deaths', 0)
        gold = data.get('gold', 0)
        exp = data.get('exp', 0)
        result = data.get('result', 'loss')
        
        # Обновляем пользователя
        query_db(f"""
            UPDATE users SET 
                kills = kills + {kills},
                deaths = deaths + {deaths},
                gold = gold + {gold},
                exp = exp + {exp}
            WHERE id = {user_id}
        """)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================
#   ЗАПУСК
# ============================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Запуск сервера на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
