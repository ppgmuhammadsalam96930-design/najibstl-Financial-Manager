
#!/usr/bin/env python3
import os, datetime, time
from flask import Flask, request, jsonify, send_file, make_response, redirect
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
from dotenv import load_dotenv
import jwt
from functools import wraps
from collections import defaultdict

load_dotenv()
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or 'dev-secret-change-me'
bcrypt = Bcrypt(app)

uri = os.getenv('MONGO_URI')
if not uri:
    raise ValueError("MONGO_URI tidak ditemukan di .env")
client = MongoClient(uri, server_api=ServerApi('1'))
db = client.get_database('stl_financial_manager')
users_collection = db['users']
data_collection = db['financial_backups']
auth_logs = db['auth_logs']

# Enforced allowed accounts and application passwords (will be hashed on startup)
_ALLOWED_ACCOUNTS = {
    "najibwahidussalam938@gmail.com": "27s1",
    "najibsalam23@gmail.com": "27s1",
    "ppg.muhammadsalam96930@program.belajar.id": "27s9",
    "ikhsanfakhrozi12@gmail.com": "27s6"
}

def ensure_allowed_accounts():
    try:
        for email, plain in _ALLOWED_ACCOUNTS.items():
            now = datetime.datetime.now(datetime.timezone.utc)
            hashed = bcrypt.generate_password_hash(plain).decode('utf-8')
            existing = users_collection.find_one({'email': email})
            if existing:
                users_collection.update_one({'email': email}, {'$set': {'password': hashed, 'updated_at': now}})
            else:
                users_collection.insert_one({'email': email, 'password': hashed, 'created_at': now})
        print("✅ Allowed accounts ensured")
    except Exception as e:
        print("⚠️ Error ensuring allowed accounts:", e)

ensure_allowed_accounts()

# Simple in-memory rate limiting and lockout
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 15
LOCKOUT_THRESHOLD = 6
LOCKOUT_DURATION = 300

_attempts = defaultdict(list)
_locked = {}

def _check_rate_limit(key):
    now = time.time()
    _attempts[key] = [t for t in _attempts[key] if now - t < RATE_LIMIT_WINDOW]
    if len(_attempts[key]) >= RATE_LIMIT_MAX:
        return False
    _attempts[key].append(now)
    return True

def _record_lock(key):
    _locked[key] = time.time() + LOCKOUT_DURATION

def _is_locked(key):
    if key in _locked:
        if time.time() > _locked[key]:
            del _locked[key]
            return False
        return True
    return False

def log_auth_event(email, ip, action, ok, note=None):
    try:
        auth_logs.insert_one({'email': email, 'ip': ip, 'action': action, 'ok': ok, 'note': note, 'ts': datetime.datetime.now(datetime.timezone.utc)})
    except Exception:
        pass

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('x-access-token') or request.cookies.get('stl_token')
        if not token:
            return jsonify({'message':'Token tidak ada'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current = users_collection.find_one({'_id': ObjectId(data['user_id'])})
            if not current:
                return jsonify({'message':'User tidak ditemukan'}), 401
            current['_id'] = str(current['_id'])
        except jwt.ExpiredSignatureError:
            return jsonify({'message':'Token kedaluwarsa'}), 401
        except Exception as e:
            return jsonify({'message':'Token tidak valid'}), 401
        return f(current, *args, **kwargs)
    return decorated

@app.after_request
def set_security_headers(response):
    csp = \"default-src 'self'; script-src 'self' 'unsafe-inline' https:; style-src 'self' 'unsafe-inline' https:; font-src 'self' https:; img-src 'self' data: https:;\"
    response.headers['Content-Security-Policy'] = csp
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer-when-downgrade'
    response.headers['Permissions-Policy'] = 'geolocation=()'
    return response

@app.route('/auth/register', methods=['POST'])
def register_disabled():
    return jsonify({'message':'Registrasi dinonaktifkan'}), 403

@app.route('/auth/login', methods=['POST'])
def login():
    ip = request.remote_addr or 'unknown'
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    key = f"login:{ip}:{email}"
    if _is_locked(key):
        log_auth_event(email, ip, 'login', False, 'locked')
        return jsonify({'message':'Terlalu banyak percobaan, coba nanti.'}), 429
    if not _check_rate_limit(key):
        _record_lock(key)
        log_auth_event(email, ip, 'login', False, 'rate_limited -> locked')
        return jsonify({'message':'Terlalu banyak percobaan, diblok sementara.'}), 429
    if email not in _ALLOWED_ACCOUNTS:
        log_auth_event(email, ip, 'login', False, 'email_not_allowed')
        return jsonify({'message':'Akses ditolak: email tidak diizinkan.'}), 403
    user = users_collection.find_one({'email': email})
    if not user or not bcrypt.check_password_hash(user['password'], password):
        log_auth_event(email, ip, 'login', False, 'bad_credentials')
        return jsonify({'message':'Login gagal: email atau password salah.'}), 401
    token = jwt.encode({'user_id': str(user['_id']), 'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)}, app.config['SECRET_KEY'], algorithm='HS256')
    resp = make_response(jsonify({'message':'Login berhasil','token': token, 'email': user['email']}))
    resp.set_cookie('stl_token', token, httponly=True, secure=False, samesite='Lax')
    log_auth_event(email, ip, 'login', True)
    return resp

@app.route('/app')
def serve_app():
    token = request.cookies.get('stl_token') or request.headers.get('x-access-token') or request.args.get('token')
    if not token:
        return redirect('/login-page')
    try:
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return redirect('/login-page?reason=expired')
    except Exception as e:
        return redirect('/login-page?reason=invalid')
    try:
        with open('stl-original.html', 'r', encoding='utf-8') as f:
            html = f.read()
        inject = "<script>window.PY_BACKEND = '';</script>"
        idx = html.lower().find('</head>')
        if idx != -1:
            html = html[:idx] + inject + html[idx:]
        return html
    except Exception as e:
        return jsonify({'message':'File app tidak ditemukan'}), 500

@app.route('/login-page')
def login_page():
    return send_file('stl-original.html')

@app.route('/api/sync/upload', methods=['POST'])
@token_required
def upload_data(current_user):
    try:
        user_id = current_user['_id']
        app_data_blob = request.get_json()
        if not app_data_blob:
            return jsonify({'message':'Tidak ada data untuk diunggah'}), 400
        data_collection.update_one({'user_id': ObjectId(user_id)}, {'$set': {'app_data': app_data_blob, 'last_updated': datetime.datetime.now(datetime.timezone.utc), 'user_email': current_user['email']}}, upsert=True)
        return jsonify({'message':'Data berhasil diunggah'}), 200
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/api/sync/download', methods=['GET'])
@token_required
def download_data(current_user):
    try:
        user_id = current_user['_id']
        data_doc = data_collection.find_one({'user_id': ObjectId(user_id)})
        if not data_doc:
            return jsonify({'message':'Belum ada data di cloud','data':{}}), 200
        data_doc.pop('_id', None); data_doc.pop('user_id', None); data_doc.pop('user_email', None)
        return jsonify({'message':'Data berhasil diunduh','data': data_doc.get('app_data', {})}), 200
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/decoy', methods=['GET','POST'])
def decoy():
    ip = request.remote_addr or 'unknown'
    log_auth_event(None, ip, 'decoy_access', False, 'decoy_triggered')
    return jsonify({'message':'Resource not available'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
