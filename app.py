from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import base64

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "DELETE"]}})

LOGO_DIR = os.path.join(os.getcwd(), 'logos')
os.makedirs(LOGO_DIR, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect('autonomous_tracker.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/companies', methods=['GET'])
def get_companies():
    conn = get_db_connection()
    companies = conn.execute('SELECT * FROM companies').fetchall()
    conn.close()
    result = []
    for company in companies:
        logo_path = os.path.join(LOGO_DIR, f"{company['company_id']}.png")
        logo_url = f"/logos/{company['company_id']}.png" if os.path.exists(logo_path) else None
        result.append({'company_id': company['company_id'], 'company_name': company['company_name'], 'logo': logo_url})
    return jsonify(result)

@app.route('/companies', methods=['POST'])
def add_company():
    data = request.get_json()
    if data.get('admin_key') != 'secret123':
        return jsonify({'error': 'Unauthorized'}), 401
    name = data.get('name')
    conn = get_db_connection()
    cursor = conn.execute('INSERT INTO companies (company_name) VALUES (?)', (name,))
    conn.commit()
    company_id = cursor.lastrowid
    conn.close()
    return jsonify({'company_id': company_id, 'company_name': name, 'logo': None})

@app.route('/save/<int:company_id>', methods=['POST'])
def save_company(company_id):
    data = request.get_json()
    if data.get('admin_key') != 'secret123':
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Save logo if provided
    logo_data = data.get('logo')
    logo_url = None
    if logo_data:
        try:
            # Handle both data URL format and raw base64
            if ',' in logo_data:
                logo_bytes = base64.b64decode(logo_data.split(',')[1])
            else:
                logo_bytes = base64.b64decode(logo_data)
                
            logo_path = os.path.join(LOGO_DIR, f"{company_id}.png")
            with open(logo_path, 'wb') as f:
                f.write(logo_bytes)
            logo_url = f"/logos/{company_id}.png"
        except Exception as e:
            print(f"Logo save error: {str(e)}")  # Log the error
            return jsonify({'error': f"Logo save failed: {str(e)}"}), 500

    # Update progress
    completed = data.get('completed', [])
    conn = get_db_connection()
    conn.execute('DELETE FROM progress WHERE company_id = ?', (company_id,))
    for req_id in completed:
        conn.execute('INSERT INTO progress (company_id, requirement_id, date_met) VALUES (?, ?, ?)',
                    (company_id, req_id, '2025-02-25'))
    conn.commit()
    conn.close()

    # Calculate position
    position = len(completed) * 0.1
    return jsonify({'status': 'success', 'position': position, 'logo': logo_url})

@app.route('/logos/<filename>')
def serve_logo(filename):
    return send_from_directory(LOGO_DIR, filename)

@app.route('/requirements', methods=['GET'])
def get_requirements():
    conn = get_db_connection()
    requirements = conn.execute('SELECT * FROM requirements').fetchall()
    conn.close()
    return jsonify([dict(row) for row in requirements])

@app.route('/progress/<int:company_id>', methods=['GET'])
def get_progress(company_id):
    conn = get_db_connection()
    completed = conn.execute('SELECT requirement_id FROM progress WHERE company_id = ?', (company_id,)).fetchall()
    conn.close()
    return jsonify({'completed': [row['requirement_id'] for row in completed]})

@app.route('/position/<int:company_id>', methods=['GET'])
def get_position(company_id):
    conn = get_db_connection()
    completed = conn.execute('SELECT requirement_id FROM progress WHERE company_id = ?', (company_id,)).fetchall()
    conn.close()
    position = len(completed) * 0.1
    return jsonify({'position': position})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
