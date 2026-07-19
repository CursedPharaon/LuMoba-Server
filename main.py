import os
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Настройки Turso
DB_URL = "https://lumoba-cursedd.aws-eu-west-1.turso.io/v1/query"
DB_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3ODQ0MTAwMDksImlkIjoiMDE5Zjc3MWYtOTQwMS03ZjFkLWE3ZWUtYjEyYzVjYjI4NTA3Iiwia2lkIjoicWpYbEhLbElGQmJNX29uRDlaWEkyWFVfazVBT3h3X3JIMF9TcUZ6MmU0ZyIsInJpZCI6ImIxMDIxMzYxLWQ3ZGEtNGMzNC05MWQ4LWVjMTU4ZGUwNmU2ZCJ9.GBhD9cLc9UJvMUL1hK6lixqtZ1MwPLbII9fXgaYG2txsUUn9NRkI-5W3r3PXRJHgfFrEUbNT_52pOx4JV6bmDA"

# ============================================================
#   ЭНДПОИНТЫ
# ============================================================

@app.route('/')
def home():
    return jsonify({
        'status': 'ok',
        'message': 'Lumoba Proxy работает!'
    })

@app.route('/api', methods=['GET'])
def api_info():
    return jsonify({
        'status': 'ok',
        'message': 'API работает! Используйте POST /api/query для SQL запросов'
    })

@app.route('/api/query', methods=['POST'])
def query():
    """Прокси-запрос к Turso"""
    try:
        data = request.json
        sql = data.get('sql', '')
        
        print(f"🔍 Получен SQL: {sql[:100]}...")
        
        if not sql:
            return jsonify({'error': 'SQL не передан'}), 400
        
        # Отправляем запрос к Turso
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
        
        print(f"📊 Статус Turso: {response.status_code}")
        
        if response.status_code != 200:
            return jsonify({'error': f'Turso HTTP {response.status_code}: {response.text[:200]}'}), response.status_code
        
        return jsonify(response.json())
        
    except Exception as e:
        print(f"💥 Ошибка: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================================
#   ЗАПУСК
# ============================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Сервер запущен на порту {port}")
    print(f"🌐 / - проверка")
    print(f"🌐 /api - информация об API")
    print(f"🌐 /api/query - основной эндпоинт")
    app.run(host='0.0.0.0', port=port, debug=False)
