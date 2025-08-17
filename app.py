from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
import os
from flask_socketio import SocketIO, emit
import re
import time
import threading
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins='*')

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

messages = []
message_counter = 0
message_lock = threading.Lock()

DATABASE = 'users.db'


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                nickname TEXT,
                profile_pic TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        db.execute('''
            CREATE TABLE IF NOT EXISTS user_sequence (
                last_id INTEGER DEFAULT 0
            )
        ''')

        db.execute('INSERT OR IGNORE INTO user_sequence (last_id) VALUES (0)')
        db.commit()


def update_db_schema():
    with app.app_context():
        db = get_db()
        cursor = db.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'profile_pic' not in columns:
            db.execute('ALTER TABLE users ADD COLUMN profile_pic TEXT DEFAULT "/static/default_profile.png"')
            db.commit()
            print("Added profile_pic column to users table")

        if 'user_id' not in columns:
            db.execute('ALTER TABLE users ADD COLUMN user_id INTEGER DEFAULT 0')
            db.commit()
            print("Added user_id column to users table")

            users = db.execute('SELECT id FROM users').fetchall()
            for i, user in enumerate(users, start=1):
                db.execute('UPDATE users SET user_id = ? WHERE id = ?', (i, user['id']))
            db.execute('UPDATE user_sequence SET last_id = ?', (len(users),))
            db.commit()

            db.execute('''
                CREATE TABLE IF NOT EXISTS users_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    nickname TEXT,
                    profile_pic TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            db.execute('''
                INSERT INTO users_new 
                SELECT id, user_id, username, password, nickname, profile_pic, created_at 
                FROM users
            ''')

            db.execute('DROP TABLE users')
            db.execute('ALTER TABLE users_new RENAME TO users')
            db.commit()

            db.execute('UPDATE user_sequence SET last_id = ?', (len(users),))
            db.commit()


init_db()
update_db_schema()


@app.route('/')
def root_redirect():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('index'))


@app.route('/@me')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('index.html',
                           username=session['username'],
                           user_id=session['user_id'],
                           profile_pic=session.get('profile_pic', '/static/default_profile.png'))


@app.errorhandler(404)
def page_not_found(e):
    if 'user_id' in session and not request.path.startswith('/@me'):
        return redirect('/@me' + request.path)
    return "Page not found", 404


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['nickname'] = user['nickname'] or user['username']

            profile_pic = user['profile_pic'] if 'profile_pic' in user.keys() else '/static/default_profile.png'
            session['profile_pic'] = profile_pic if profile_pic else '/static/default_profile.png'

            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        nickname = request.form.get('nickname', '').strip()

        if not username or not password:
            return render_template('signup.html', error='Username and password are required')

        if len(username) < 4 or len(username) > 20:
            return render_template('signup.html', error='Username must be between 4-20 characters')

        if len(password) < 6:
            return render_template('signup.html', error='Password must be at least 6 characters')

        db = get_db()
        try:
            result = db.execute('SELECT last_id FROM user_sequence').fetchone()
            next_id = result['last_id'] + 1

            db.execute(
                'INSERT INTO users (user_id, username, password, nickname, profile_pic) VALUES (?, ?, ?, ?, ?)',
                (next_id, username, generate_password_hash(password), nickname or None, '/static/default_profile.png')
            )

            db.execute('UPDATE user_sequence SET last_id = ?', (next_id,))

            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('signup.html', error='Username already exists')

    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/admin')
def admin_tools():
    return """
    <h1>Admin Tools</h1>
    <h2>Check User</h2>
    <form action="/check_user" method="post">
        <input type="text" name="username" value="fahriredwood">
        Admin Password: <input type="password" name="admin_pass"><br>
        <button type="submit">Check User</button>
    </form>

    <h2>Reset Password</h2>
    <form action="/reset_password" method="post">
        <input type="text" name="username" value="fahriredwood">
        New Password: <input type="password" name="new_password"><br>
        Admin Password: <input type="password" name="admin_pass"><br>
        <button type="submit">Reset Password</button>
    </form>
    """


@app.route('/check_user', methods=['POST'])
def check_user():
    if request.form['admin_pass'] != "admin123":
        return "Wrong admin password"

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?',
                      (request.form['username'],)).fetchone()

    if user:
        return f"User {user['username']} exists in database"
    else:
        return "User not found"


@app.route('/reset_password', methods=['POST'])
def reset_password():
    if request.form['admin_pass'] != "admin123":  # Change this password!
        return "Wrong admin password"

    if len(request.form['new_password']) < 6:
        return "Password must be at least 6 characters"

    db = get_db()
    db.execute('UPDATE users SET password = ? WHERE username = ?',
               (generate_password_hash(request.form['new_password']),
                request.form['username']))
    db.commit()

    return f"Password for {request.form['username']} has been reset"

MAX_MESSAGE_LENGTH = 1000

@socketio.on('send_message')
def receive_text(data):
    global message_counter

    user_text = data.get("text", "").strip()
    media_url = data.get("media_url")
    reply_to = data.get("reply_to")

    if len(user_text) > MAX_MESSAGE_LENGTH:
        return

    if not user_text and not media_url:
        return

    if 'user_id' not in session:
        return

    username = session['username']
    profile_pic = session.get('profile_pic', '/static/default_profile.png')

    msg_to_send = None
    with message_lock:
        msg_id = message_counter
        message_counter += 1

        msg_to_send = {
            'id': msg_id,
            'user_id': session['user_id'],
            'nickname': username,
            'text': user_text,
            'media_url': media_url,
            'timestamp': time.time(),
            'edited': False,
            'profile_pic': profile_pic,
            'reply_to': reply_to
        }
        messages.append(msg_to_send)

    emit('new_message', msg_to_send, broadcast=True)


@socketio.on('get_messages')
def get_messages():
    emit('load_messages', messages)


@app.route('/message/<int:msg_id>')
def message_link(msg_id):
    with message_lock:
        for msg in messages:
            if msg['id'] == msg_id:
                return redirect(url_for('index') + f'#msg-{msg_id}')

    return redirect(url_for('index'))


@socketio.on('delete_message')
def delete_message(msg_id):
    global messages
    with message_lock:
        messages = [m for m in messages if m['id'] != msg_id]
    emit('remove_message', msg_id, broadcast=True)


@socketio.on('edit_message')
def edit_message(data):
    msg_id = data.get('id')
    new_text = data.get('text')

    with message_lock:
        for msg in messages:
            if msg['id'] == msg_id:
                if msg['text'] != new_text:
                    msg['text'] = new_text
                    msg['edited'] = True
                else:
                    msg['text'] = new_text
                    msg['edited'] = False
                emit('update_message', msg, broadcast=True)
                break


@socketio.on('typing')
def handle_typing(data):
    username = data.get('nickname') or data.get('username')
    if not username:
        return
    emit('user_typing', {'nickname': username}, broadcast=True, include_self=False)


@socketio.on('stop_typing')
def handle_stop_typing(data):
    username = data.get('nickname') or data.get('username')
    if not username:
        return
    emit('user_stopped_typing', {'nickname': username}, broadcast=True, include_self=False)


def safe_filename(original_name):
    safe_name = re.sub(r'[^a-zA-Z0-9.\-_]', '_', original_name)
    base, ext = os.path.splitext(safe_name)
    timestamp = str(int(time.time() * 1000))
    if base == '' or base == '.':
        return f"{timestamp}-file{ext}"
    else:
        return f"{timestamp}-{safe_name}"


@app.route('/upload_video', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify(success=False, error="No file provided"), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify(success=False, error="No file selected"), 400

    # Add file size limit (10MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset file pointer

    if file_size > 150 * 1024 * 1024:  # 150MB limit
        return jsonify(success=False, error="File too large (max 150MB)"), 400

    # Basic file type validation
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mp3', '.webm', '.ogg', '.mov', '.rar'}
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        return jsonify(success=False, error="File type not allowed"), 400

    os.makedirs('./uploads', exist_ok=True)

    filename = safe_filename(file.filename)
    filepath = os.path.join('./uploads', filename)

    try:
        file.save(filepath)
        file_url = f"/uploads/{filename}"
        return jsonify(success=True, url=file_url)
    except Exception as e:
        return jsonify(success=False, error=f"Upload failed: {str(e)}"), 500


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    uploads_dir = os.path.join(os.getcwd(), 'uploads')
    file_path = os.path.join(uploads_dir, filename)
    return send_file(file_path, conditional=True)


online_users = {}
user_last_activity = {}
AFK_TIMEOUT = 300


def update_online_users_list():
    db = get_db()
    all_users = db.execute('SELECT username, profile_pic, user_id FROM users').fetchall()
    current_time = time.time()

    users_with_status = []
    for user in all_users:
        user_id = user['user_id']
        profile_pic = user['profile_pic'] or "/static/default_profile.png"

        if user_id in online_users:
            last_active = user_last_activity.get(user_id, 0)
            if (current_time - last_active) > AFK_TIMEOUT:
                status = "away"
            else:
                status = "online"
        else:
            status = "offline"

        users_with_status.append({
            'user_id': user_id,
            "username": user['username'],
            "status": status,
            "profile_pic": profile_pic
        })

    emit('update_online_users', users_with_status, broadcast=True)


@socketio.on('register_user')
def handle_register(username):
    user_id = session.get('user_id')
    if not user_id:
        return

    if user_id not in online_users:
        online_users[user_id] = []
    if request.sid not in online_users[user_id]:
        online_users[user_id].append(request.sid)

    user_last_activity[user_id] = time.time()
    update_online_users_list()


@socketio.on('user_activity')
def handle_activity(data=True):
    user_id = session.get('user_id')
    if not user_id:
        return

    is_active = True
    if isinstance(data, dict) and 'active' in data:
        is_active = bool(data['active'])

    if is_active:
        user_last_activity[user_id] = time.time()

    update_online_users_list()


@socketio.on('disconnect')
def handle_disconnect():
    user_id = session.get('user_id')
    if not user_id:
        return

    if user_id in online_users:
        if request.sid in online_users[user_id]:
            online_users[user_id].remove(request.sid)

        if not online_users[user_id]:
            del online_users[user_id]
            user_last_activity.pop(user_id, None)

    update_online_users_list()


@app.route('/upload_profile_pic', methods=['POST'])
def upload_profile_pic():
    if 'user_id' not in session:
        return jsonify(success=False, error="Not logged in"), 401

    if 'file' not in request.files:
        return jsonify(success=False, error="No file provided"), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify(success=False, error="No file selected"), 400

    # File size limit (2MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > 2 * 1024 * 1024:
        return jsonify(success=False, error="File too large (max 2MB)"), 400

    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        return jsonify(success=False, error="File type not allowed"), 400

    filename = f"profile_{session['user_id']}{file_ext}"
    filepath = os.path.join('./uploads', filename)

    try:
        file.save(filepath)
        file_url = f"/uploads/{filename}"

        db = get_db()
        db.execute('UPDATE users SET profile_pic = ? WHERE user_id = ?',(file_url, session['user_id']))
        db.commit()

        session['profile_pic'] = file_url

        return jsonify(success=True, url=file_url)
    except Exception as e:
        return jsonify(success=False, error="Upload failed"), 500


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)