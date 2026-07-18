import os
import hashlib
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ============================================================
#   НАСТРОЙКИ TURSO
# ============================================================
DB_URL = "https://lumoba-cursedd.aws-eu-west-1.turso.io/v1/query"
DB_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3ODQ0MTAwMDksImlkIjoiMDE5Zjc3MWYtOTQwMS03ZjFkLWE3ZWUtYjEyYzVjYjI4NTA3Iiwia2lkIjoicWpYbEhLbElGQmJNX29uRDlaWEkyWFVfazVBT3h3X3JIMF9TcUZ6MmU0ZyIsInJpZCI6ImIxMDIxMzYxLWQ3ZGEtNGMzNC05MWQ4LWVjMTU4ZGUwNmU2ZCJ9.GBhD9cLc9UJvMUL1hK6lixqtZ1MwPLbII9fXgaYG2txsUUn9NRkI-5W3r3PXRJHgfFrEUbNT_52pOx4JV6bmDA"

def query_db(sql, args=None):
    """Отправка запроса в Turso с поддержкой параметров"""
    try:
        payload = {
            'statements': [{
                'sql': sql,
                'args': args if args else []
            }]
        }
        
        print(f"🔍 SQL: {sql[:150]}")
        if args:
            print(f"📦 Args: {args}")
        
        response = requests.post(
            DB_URL,
            headers={
                'Authorization': f'Bearer {DB_TOKEN}',
                'Content-Type': 'application/json'
            },
            json=payload,
            timeout=30
        )
        
        print(f"📊 Статус: {response.status_code}")
        
        if response.status_code != 200:
            error_text = response.text[:300]
            print(f"❌ Ошибка: {error_text}")
            return {'error': f'HTTP {response.status_code}: {error_text}'}
        
        data = response.json()
        print(f"✅ Ответ получен")
        return data
        
    except Exception as e:
        print(f"💥 Исключение: {str(e)}")
        return {'error': str(e)}

def extract_rows(result):
    """Извлекает строки из ответа Turso"""
    try:
        if 'error' in result:
            return []
        results = result.get('results', [])
        if not results:
            return []
        response = results[0].get('response', {})
        result_data = response.get('result', {})
        rows = result_data.get('rows', [])
        return rows
    except Exception as e:
        print(f"⚠️ Ошибка извлечения rows: {e}")
        return []

def init_db():
    """Создание таблицы"""
    print("🔄 СОЗДАНИЕ ТАБЛИЦЫ...")
    
    sql = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        rank TEXT DEFAULT 'Бронза',
        level INTEGER DEFAULT 1,
        gold INTEGER DEFAULT 500,
        kills INTEGER DEFAULT 0,
        deaths INTEGER DEFAULT 0,
        exp INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    result = query_db(sql)
    
    if 'error' in result:
        print(f"❌ ОШИБКА СОЗДАНИЯ ТАБЛИЦЫ: {result['error']}")
        return False
    
    print("✅ ТАБЛИЦА ГОТОВА")
    return True

# ============================================================
#   API ЭНДПОИНТЫ
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
        
        # Проверяем существование пользователя
        check_sql = "SELECT id FROM users WHERE username = ?"
        check_result = query_db(check_sql, [username])
        rows = extract_rows(check_result)
        
        if rows:
            return jsonify({'error': 'Пользователь уже существует'}), 400
        
        # Хешируем пароль
        hashed = hashlib.sha256(password.encode()).hexdigest()
        
        # Создаём пользователя
        insert_sql = "INSERT INTO users (username, password) VALUES (?, ?)"
        insert_result = query_db(insert_sql, [username, hashed])
        
        if 'error' in insert_result:
            print(f"❌ Ошибка вставки: {insert_result}")
            return jsonify({'error': 'Ошибка базы данных при создании'}), 500
        
        print(f"✅ ПОЛЬЗОВАТЕЛЬ СОЗДАН: {username}")
        return jsonify({
            'success': True,
            'message': 'Аккаунт создан!'
        })
        
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
        
        sql = "SELECT id, username, rank, level, gold FROM users WHERE username = ? AND password = ?"
        result = query_db(sql, [username, hashed])
        
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
                'gold': user[4]
            }
        })
        
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/top', methods=['GET'])
def get_top():
    try:
        sql = "SELECT username, kills, rank, level FROM users ORDER BY kills DESC LIMIT 10"
        result = query_db(sql)
        rows = extract_rows(result)
        
        return jsonify([{
            'username': row[0],
            'kills': row[1] if len(row) > 1 else 0,
            'rank': row[2] if len(row) > 2 else 'Бронза',
            'level': row[3] if len(row) > 3 else 1
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
        
        sql = """
            UPDATE users SET 
                kills = kills + ?,
                deaths = deaths + ?,
                gold = gold + ?,
                exp = exp + ?
            WHERE id = ?
        """
        result = query_db(sql, [kills, deaths, gold, exp, user_id])
        
        if 'error' in result:
            return jsonify({'error': 'Ошибка обновления'}), 500
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================
#   ЗАПУСК
# ============================================================
if __name__ == '__main__':
    print("🚀 ЗАПУСК СЕРВЕРА...")
    
    # Инициализируем базу
    if not init_db():
        print("⚠️ ПРЕДУПРЕЖДЕНИЕ: База данных не инициализирована")
    
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 ПОРТ: {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
