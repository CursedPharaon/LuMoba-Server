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

@app.route('/', methods=['GET', 'POST', 'OPTIONS'])
def home():
    if request.method == 'OPTIONS':
        return '', 200
    
    if request.method == 'GET':
        return jsonify({'status': 'ok', 'message': 'Lumoba Proxy работает! Используйте POST с SQL'})
    
    # POST - обрабатываем SQL
    try:
        data = request.json
        sql = data.get('sql', '')
        
        if not sql:
            return jsonify({'error': 'SQL не передан'}), 400
        
        print(f"📝 SQL: {sql[:100]}...")
        
        response = requests.post(
            DB_URL,
            headers={
                'Authorization': f'Bearer {DB_TOKEN}',
                'Content-Type': 'application/json'
            },
            json={'statements': [{'sql': sql}]},
            timeout=30
        )
        
        if response.status_code != 200:
            return jsonify({'error': f'Turso: {response.text[:100]}'}), response.status_code
        
        return jsonify(response.json())
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Сервер запущен на порту {port}")
    print(f"🌐 Отправляйте POST запросы с SQL на /")
    app.run(host='0.0.0.0', port=port)
