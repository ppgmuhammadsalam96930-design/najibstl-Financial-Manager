import os
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
from dotenv import load_dotenv
import jwt 
from functools import wraps # Diperlukan untuk dekorator @wraps

# --- 1. Konfigurasi Dasar & Environment ---
load_dotenv()
app = Flask(__name__)
CORS(app) 

# --- 2. Konfigurasi Keamanan (Ambil dari .env) ---
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
if not app.config["SECRET_KEY"]:
    raise ValueError("SECRET_KEY tidak ditemukan di .env. Harap cek konfigurasi.")

bcrypt = Bcrypt(app)

# --- 3. Koneksi MongoDB (Ambil dari .env) ---
uri = os.getenv("MONGO_URI")
if not uri:
    # Gagal jika MONGO_URI tidak diset (TIDAK ADA HARDCODE)
    raise ValueError("MONGO_URI tidak ditemukan di .env. Harap set koneksi string Anda.")

# Inisialisasi Klien MongoDB
try:
    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client['stl_financial_manager'] # Database untuk aplikasi STL Anda
    users_collection = db['users']
    data_collection = db['financial_backups'] # Menggunakan nama dari file Anda
    
    client.admin.command('ping')
    print("🚀 Backend Siap! Berhasil terhubung ke MongoDB.")
except Exception as e:
    print(f"❌ Gagal terhubung ke MongoDB: {e}")
    client = None

# --- 4. Fungsi Decorator Autentikasi (JWT) ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('x-access-token')

        if not token:
            return jsonify({'message': 'Token autentikasi tidak ada!'}), 401

        try:
            # Decode token, memastikan token masih berlaku (exp)
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = users_collection.find_one({'_id': ObjectId(data['user_id'])})
            
            if not current_user:
                 return jsonify({'message': 'User tidak ditemukan atau token tidak valid!'}), 401
            
            # Ubah ObjectId menjadi string untuk digunakan di rute
            current_user['_id'] = str(current_user['_id'])
            
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token sudah kedaluwarsa. Silakan login ulang.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token tidak valid!'}), 401
        except Exception as e:
            return jsonify({'message': f'Error validasi token: {str(e)}'}), 500

        # Meneruskan objek user yang terautentikasi ke fungsi rute
        return f(current_user, *args, **kwargs)
    return decorated

# --- 5. Rute Autentikasi (Publik) ---

@app.route('/auth/register', methods=['POST'])
def register():
    """Mendaftarkan pengguna baru."""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'message': 'Email dan password diperlukan'}), 400

        if users_collection.find_one({'email': email}):
            return jsonify({'message': 'Email sudah terdaftar'}), 409

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        user_id = users_collection.insert_one({
            'email': email,
            'password': hashed_password,
            'created_at': datetime.datetime.now(datetime.timezone.utc)
        }).inserted_id

        return jsonify({'message': 'Registrasi berhasil', 'user_id': str(user_id)}), 201

    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/auth/login', methods=['POST'])
def login():
    """Login pengguna dan mengembalikan token JWT."""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        user = users_collection.find_one({'email': email})

        if not user or not bcrypt.check_password_hash(user['password'], password):
            return jsonify({'message': 'Login gagal! Email atau Password salah.'}), 401
        
        # Buat token JWT berlaku 24 jam
        token = jwt.encode({
            'user_id': str(user['_id']),
            'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24) 
        }, app.config['SECRET_KEY'], algorithm="HS256")

        return jsonify({'message': 'Login berhasil', 'token': token, 'email': user['email']})

    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

# --- 6. Rute Data Sync (Aman / Perlu Token) ---

@app.route('/api/sync/upload', methods=['POST'])
@token_required
def upload_data(current_user):
    """Menyimpan/Memperbarui BLOB data aplikasi financial (backup)."""
    try:
        user_id = current_user['_id']
        app_data_blob = request.get_json() 

        if not app_data_blob:
            return jsonify({'message': 'Tidak ada data untuk diunggah'}), 400

        # Gunakan update_one dengan upsert=True
        # Membuat dokumen baru jika belum ada, atau memperbarui jika sudah ada
        data_collection.update_one(
            {'user_id': ObjectId(user_id)}, # Kunci unik adalah user_id
            {
                '$set': {
                    'app_data': app_data_blob,
                    'last_updated': datetime.datetime.now(datetime.timezone.utc),
                    'user_email': current_user['email']
                }
            },
            upsert=True
        )

        return jsonify({'message': 'Data berhasil diunggah dan disinkronisasi'}), 200

    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500


@app.route('/api/sync/download', methods=['GET'])
@token_required
def download_data(current_user):
    """Mengambil data backup terakhir pengguna dari cloud."""
    try:
        user_id = current_user['_id']
        data_doc = data_collection.find_one({'user_id': ObjectId(user_id)})

        if not data_doc:
            return jsonify({'message': 'Belum ada data di cloud', 'data': {}}), 200

        # Hapus _id, user_id, dan detail internal lainnya dari respons
        data_doc.pop('_id', None)
        data_doc.pop('user_id', None)
        data_doc.pop('user_email', None)
        
        # Mengembalikan hanya BLOB data aplikasi
        return jsonify({'message': 'Data berhasil diunduh', 'data': data_doc.get('app_data', {})})

    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

# --- 7. Menjalankan Server ---
if __name__ == '__main__':
    # Ambil port dari environment variable (untuk deployment) atau default ke 5000
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
