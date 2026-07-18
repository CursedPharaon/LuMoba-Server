import os
import json
import hashlib
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

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
            print(f"❌ Ошибка HTTP: {response.status_code}")
            return {'error': response.text}
        
        return response.json()
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return {'error': str(e)}

# ============================================================
#   ИНИЦИАЛИЗАЦИЯ БД
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
        );
        
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            kills INTEGER,
            deaths INTEGER,
            gold_earned INTEGER,
            result TEXT,
            played_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        
        CREATE TABLE IF NOT EXISTS clans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            leader_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (leader_id) REFERENCES users(id)
        );
    """
    result = query_db(sql)
    if 'error' in result:
        print(f"❌ Ошибка инициализации: {result['error']}")
        return False
    print("✅ База данных инициализирована")
    return True

# Инициализируем при старте
init_db()

# ============================================================
#   ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def extract_rows(result):
    """Извлекает строки из ответа Turso"""
    try:
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
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({'error': 'Заполните все поля'}), 400
    
    # Проверяем существование
    check = query_db(f"SELECT id FROM users WHERE username = '{username}'")
    if extract_rows(check):
        return jsonify({'error': 'Пользователь уже существует'}), 400
    
    hashed = hash_password(password)
    
    # Создаём пользователя
    result = query_db(
        f"INSERT INTO users (username, password) VALUES ('{username}', '{hashed}')"
    )
    
    if 'error' in result:
        return jsonify({'error': 'Ошибка базы данных'}), 500
    
    return jsonify({'success': True, 'message': 'Аккаунт создан!'})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({'error': 'Заполните все поля'}), 400
    
    hashed = hash_password(password)
    
    result = query_db(
        f"SELECT id, username, rank, level, exp, gold, kills, deaths, class, clan FROM users WHERE username = '{username}' AND password = '{hashed}'"
    )
    
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
            'clan': user[9]
        }
    })

@app.route('/api/top', methods=['GET'])
def get_top():
    result = query_db(
        "SELECT username, kills, rank, level FROM users ORDER BY kills DESC LIMIT 10"
    )
    rows = extract_rows(result)
    
    return jsonify([{
        'username': row[0],
        'kills': row[1],
        'rank': row[2],
        'level': row[3]
    } for row in rows])

@app.route('/api/update_stats', methods=['POST'])
def update_stats():
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
    
    # Добавляем матч
    query_db(f"""
        INSERT INTO matches (user_id, kills, deaths, gold_earned, result) 
        VALUES ({user_id}, {kills}, {deaths}, {gold}, '{result}')
    """)
    
    return jsonify({'success': True})

# ============================================================
#   ЗАПУСК
# ============================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
    print(f"🚀 Сервер запущен на порту {port}")
