import os
import hashlib
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ============================================================
#   НАСТРОЙКИ TURSO
# ============================================================
DB_URL = "https://lumoba-cursedd.aws-eu-west-1.turso.io/v1/query"
DB_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3ODQ0MTAwMDksImlkIjoiMDE5Zjc3MWYtOTQwMS03ZjFkLWE3ZWUtYjEyYzVjYjI4NTA3Iiwia2lkIjoicWpYbEhLbElGQmJNX29uRDlaWEkyWFVfazVBT3h3X3JIMF9TcUZ6MmU0ZyIsInJpZCI6ImIxMDIxMzYxLWQ3ZGEtNGMzNC05MWQ4LWVjMTU4ZGUwNmU2ZCJ9.GBhD9cLc9UJvMUL1hK6lixqtZ1MwPLbII9fXgaYG2txsUUn9NRkI-5W3r3PXRJHgfFrEUbNT_52pOx4JV6bmDA"

def query_turso(sql):
    """Отправка запроса в Turso - ПРЯМАЯ ПОДСТАНОВКА как в HTML коде"""
    try:
        print(f"🔍 SQL: {sql[:200]}")
        
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
            print(f"❌ Ошибка: {response.text[:300]}")
            return {'error': f'HTTP {response.status_code}'}
        
        data = response.json()
        print(f"✅ Ответ получен")
        return data
        
    except Exception as e:
        print(f"💥 Ошибка: {str(e)}")
        return {'error': str(e)}

def safe_string(val):
    """Безопасное преобразование в строку"""
    if val is None:
        return ''
    return str(val)

def safe_int(val):
    """Безопасное преобразование в int"""
    try:
        return int(val) if val is not None else 0
    except:
        return 0

def extract_rows(result):
    """Извлекает rows из ответа Turso (как в HTML коде)"""
    try:
        if 'error' in result:
            return []
        if result and 'rows' in result:
            return result['rows']
        if result and 'results' in result and len(result['results']) > 0:
            response = result['results'][0].get('response', {})
            result_data = response.get('result', {})
            return result_data.get('rows', [])
        return []
    except Exception as e:
        print(f"⚠️ Ошибка извлечения: {e}")
        return []

# ============================================================
#   ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
# ============================================================
def init_db():
    print("🔄 СОЗДАНИЕ ТАБЛИЦ...")
    
    # Создаём таблицу users (как в HTML коде)
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
        class TEXT DEFAULT 'fighter',
        clan TEXT DEFAULT 'Без клана',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    result = query_turso(sql)
    
    if 'error' in result:
        print(f"❌ ОШИБКА СОЗДАНИЯ ТАБЛИЦЫ: {result['error']}")
        return False
    
    print("✅ ТАБЛИЦА ГОТОВА")
    return True

# ============================================================
#   API ЭНДПОИНТЫ (КАК В HTML КОДЕ)
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
        
        # Экранируем кавычки (как в HTML коде)
        safe_username = username.replace("'", "''")
        safe_password = password.replace("'", "''")
        
        # Проверяем существование (ПРЯМАЯ ПОДСТАНОВКА)
        check_sql = f"SELECT id FROM users WHERE username = '{safe_username}'"
        check_result = query_turso(check_sql)
        rows = extract_rows(check_result)
        
        if rows and len(rows) > 0:
            return jsonify({'error': 'Пользователь уже существует'}), 400
        
        # Хешируем пароль
        hashed = hashlib.sha256(password.encode()).hexdigest()
        
        # Создаём пользователя (ПРЯМАЯ ПОДСТАНОВКА)
        insert_sql = f"INSERT INTO users (username, password) VALUES ('{safe_username}', '{hashed}')"
        insert_result = query_turso(insert_sql)
        
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
        
        # Экранируем кавычки
        safe_username = username.replace("'", "''")
        
        # Хешируем пароль
        hashed = hashlib.sha256(password.encode()).hexdigest()
        
        # Ищем пользователя (ПРЯМАЯ ПОДСТАНОВКА)
        sql = f"SELECT id, username, rank, level, gold, kills, deaths, exp, class, clan FROM users WHERE username = '{safe_username}' AND password = '{hashed}'"
        result = query_turso(sql)
        
        rows = extract_rows(result)
        
        if not rows or len(rows) == 0:
            return jsonify({'error': 'Неверный логин или пароль'}), 401
        
        user = rows[0]
        return jsonify({
            'success': True,
            'user': {
                'id': user[0],
                'username': safe_string(user[1]),
                'rank': safe_string(user[2]),
                'level': safe_int(user[3]),
                'gold': safe_int(user[4]),
                'kills': safe_int(user[5]),
                'deaths': safe_int(user[6]),
                'exp': safe_int(user[7]),
                'class': safe_string(user[8]) if len(user) > 8 else 'fighter',
                'clan': safe_string(user[9]) if len(user) > 9 else 'Без клана'
            }
        })
        
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/top', methods=['GET'])
def get_top():
    try:
        sql = "SELECT username, kills, rank, level FROM users ORDER BY kills DESC LIMIT 10"
        result = query_turso(sql)
        rows = extract_rows(result)
        
        return jsonify([{
            'username': safe_string(row[0]),
            'kills': safe_int(row[1]) if len(row) > 1 else 0,
            'rank': safe_string(row[2]) if len(row) > 2 else 'Бронза',
            'level': safe_int(row[3]) if len(row) > 3 else 1
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
        
        # Прямая подстановка
        sql = f"""
            UPDATE users SET 
                kills = kills + {kills},
                deaths = deaths + {deaths},
                gold = gold + {gold},
                exp = exp + {exp}
            WHERE id = {user_id}
        """
        result = query_turso(sql)
        
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
