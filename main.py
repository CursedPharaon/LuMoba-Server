from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
import datetime
import json

app = Flask(__name__)
CORS(app)  # Разрешаем все запросы

# ============================================================
#   ПОДКЛЮЧЕНИЕ К TURSO
# ============================================================
import libsql_client

DB_URL = "libsql://lumoba-cursedd.aws-eu-west-1.turso.io"
DB_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3ODQ0MTAwMDksImlkIjoiMDE5Zjc3MWYtOTQwMS03ZjFkLWE3ZWUtYjEyYzVjYjI4NTA3Iiwia2lkIjoicWpYbEhLbElGQmJNX29uRDlaWEkyWFVfazVBT3h3X3JIMF9TcUZ6MmU0ZyIsInJpZCI6ImIxMDIxMzYxLWQ3ZGEtNGMzNC05MWQ4LWVjMTU4ZGUwNmU2ZCJ9.GBhD9cLc9UJvMUL1hK6lixqtZ1MwPLbII9fXgaYG2txsUUn9NRkI-5W3r3PXRJHgfFrEUbNT_52pOx4JV6bmDA"

def get_db():
    return libsql_client.create_client_sync(DB_URL, auth_token=DB_TOKEN)

# ============================================================
#   СОЗДАНИЕ ТАБЛИЦ
# ============================================================
def init_db():
    with get_db() as db:
        db.execute("""
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
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                kills INTEGER,
                deaths INTEGER,
                gold_earned INTEGER,
                result TEXT,
                played_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS clans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                leader_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (leader_id) REFERENCES users(id)
            )
        """)
    print("✅ База данных инициализирована")

init_db()

# ============================================================
#   ХЕШИРОВАНИЕ
# ============================================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ============================================================
#   API ЭНДПОИНТЫ
# ============================================================

# 1. РЕГИСТРАЦИЯ
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Заполните все поля'}), 400
    
    hashed = hash_password(password)
    
    with get_db() as db:
        # Проверяем существование
        existing = db.execute("SELECT id FROM users WHERE username = ?", [username])
        if existing.fetchone():
            return jsonify({'error': 'Пользователь уже существует'}), 400
        
        # Создаём
        db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            [username, hashed]
        )
    
    return jsonify({'success': True, 'message': 'Аккаунт создан!'})

# 2. ВХОД
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Заполните все поля'}), 400
    
    hashed = hash_password(password)
    
    with get_db() as db:
        result = db.execute(
            "SELECT id, username, rank, level, exp, gold, kills, deaths, class, clan FROM users WHERE username = ? AND password = ?",
            [username, hashed]
        )
        user = result.fetchone()
        
        if not user:
            return jsonify({'error': 'Неверный логин или пароль'}), 401
        
        # Обновляем последний вход
        db.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            [user[0]]
        )
    
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

# 3. ПОЛУЧИТЬ СТАТИСТИКУ ИГРОКА
@app.route('/api/stats/<int:user_id>', methods=['GET'])
def get_stats(user_id):
    with get_db() as db:
        result = db.execute(
            "SELECT username, rank, level, kills, deaths, gold FROM users WHERE id = ?",
            [user_id]
        )
        user = result.fetchone()
        if not user:
            return jsonify({'error': 'Игрок не найден'}), 404
    
    return jsonify({
        'username': user[0],
        'rank': user[1],
        'level': user[2],
        'kills': user[3],
        'deaths': user[4],
        'gold': user[5]
    })

# 4. ОБНОВИТЬ СТАТИСТИКУ ПОСЛЕ МАТЧА
@app.route('/api/update_stats', methods=['POST'])
def update_stats():
    data = request.json
    user_id = data.get('user_id')
    kills = data.get('kills', 0)
    deaths = data.get('deaths', 0)
    gold = data.get('gold', 0)
    exp = data.get('exp', 0)
    result = data.get('result', 'loss')
    
    with get_db() as db:
        db.execute(
            """UPDATE users SET 
                kills = kills + ?,
                deaths = deaths + ?,
                gold = gold + ?,
                exp = exp + ?
            WHERE id = ?""",
            [kills, deaths, gold, exp, user_id]
        )
        
        # Добавляем матч в историю
        db.execute(
            "INSERT INTO matches (user_id, kills, deaths, gold_earned, result) VALUES (?, ?, ?, ?, ?)",
            [user_id, kills, deaths, gold, result]
        )
    
    return jsonify({'success': True})

# 5. ТОП ИГРОКОВ
@app.route('/api/top', methods=['GET'])
def get_top():
    with get_db() as db:
        result = db.execute(
            "SELECT username, kills, rank, level FROM users ORDER BY kills DESC LIMIT 10"
        )
        top = result.fetchall()
    
    return jsonify([{
        'username': t[0],
        'kills': t[1],
        'rank': t[2],
        'level': t[3]
    } for t in top])

# ============================================================
#   ЗАПУСК СЕРВЕРА
# ============================================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    print("🚀 Сервер запущен на http://localhost:5000")
