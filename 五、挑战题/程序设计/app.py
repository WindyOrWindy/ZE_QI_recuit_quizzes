import uuid
import jwt
import datetime
import hashlib
import base64
import os
from flask import *
from flask_cors import CORS
import pymysql

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    'host': 'localhost',          # MySQL 服务器地址
    'port': 3306,                 # MySQL 端口
    'user': 'root',               # MySQL 用户名
    'password': 'Koko622724@',    # MySQL 密码（生产环境务必改为读 os.environ，避免明文入仓）
    'database': 'recruit_quizzes_test_five_database',
    'charset': 'utf8mb4'
}



def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

@app.route('/')
def home():
    return redirect('/login')

#验证密码->比较加密码一不一样
def verify_password(password: str, salt_b64: str, hashed_b64: str) -> bool:
    # 1. 还原盐值
    salt = base64.b64decode(salt_b64)
    
    # 2. 用同样的盐重新哈希
    pwd_bytes = password.encode('utf-8')
    new_hash = hashlib.sha256(pwd_bytes + salt).digest()
    
    # 3. 比较
    stored_hash = base64.b64decode(hashed_b64)
    return new_hash == stored_hash

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return jsonify({'code': 400, 'message': 'invalid parameters'}), 400

        conn = get_db_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(
                    'SELECT userID, username, password,salt FROM users WHERE username = %s',
                    (username,)
                )
                user = cur.fetchone()
                if not user or not verify_password(password, user['salt'], user['password']):
                    return jsonify({'code': 401,
                                    'message': 'username or password is wrong'}), 401

                # 登录成功：生成 sessionId 写回 users.sessionID
                session_id = str(uuid.uuid4())
                cur.execute(
                    'UPDATE users SET sessionID = %s WHERE userID = %s',
                    (session_id, user['userID'])
                )
            conn.commit()                         

            return jsonify({
                'code': 200,
                'message': '登录成功',
                'sessionId': session_id,         
                'username': user['username']
            }), 200
        finally:
            conn.close()                    

    return render_template('login.html')

def hash_password(password: str) -> tuple:
    # 1. 生成随机盐值（16字节）
    salt = os.urandom(16)
    
    # 2. 密码 + 盐 → SHA256
    #    注意：密码要encode成bytes
    pwd_bytes = password.encode('utf-8')
    
    # 3. 拼接后哈希
    hashed = hashlib.sha256(pwd_bytes + salt).digest()
    
    # 4. 转成可存储的字符串（Base64）
    salt_b64 = base64.b64encode(salt).decode('utf-8')
    hashed_b64 = base64.b64encode(hashed).decode('utf-8')
    
    return salt_b64, hashed_b64


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return jsonify({'code': 400, 'message': 'invalid parameters'}), 400

        conn = get_db_connection()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute('SELECT 1 FROM users WHERE username = %s', (username,))
                if cur.fetchone():
                    #重复注册返回 409（或 400）
                    return jsonify({'code': 409,
                                    'message': 'username already exists'}), 409
                session_id = str(uuid.uuid4())
                salt_b64, hashed_pwd = hash_password(password)

                cur.execute(
                    'INSERT INTO users (username, password, sessionID, salt) VALUES (%s, %s, %s, %s)',
                    (username, hashed_pwd, session_id, salt_b64)
                )
                user_id = cur.lastrowid #获取user_id（刚插入的那个）


            conn.commit()           

            return jsonify({
                'code': 201,
                'message': '注册成功',
                'userId': user_id,
                'username': username,
                'sessionId': session_id
            }), 201
        except Exception as e:
            print('[注册] 异常：', e)
            return jsonify({'code': 500, 'message': 'server error'}), 500
        finally:
            conn.close()

    return render_template('register.html')


@app.route('/me', methods=['GET', 'POST', 'PATCH', 'DELETE'])
def me():
    return render_template('me.html')

@app.route('/users/me', methods=['GET', 'PATCH', 'DELETE'])
def api_me():
    sid = (request.headers.get('Session-ID') or '').strip()
    if not sid:
        return jsonify({'code': 401, 'message': 'Unauthorized'}), 401

    conn = get_db_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            # 凭 sessionID 查库
            cur.execute(
                'SELECT userID, username, password,salt FROM users WHERE sessionID = %s',
                (sid,)
            )
            user = cur.fetchone()
            if not user:
                return jsonify({'code': 401, 'message': 'Unauthorized'}), 401

            #  查看个人信息 
            if request.method == 'GET':
                return jsonify({
                    'code': 200,
                    'data': {
                        'userID':   user['userID'],
                        'username': user['username']
                    }
                }), 200

            data = request.get_json(silent=True) or {}

            #  修改用户名（有 new_username ）
            if request.method == 'PATCH' and 'new_username' in data:
                new_username = (data.get('new_username') or '').strip()
                if not new_username or not data.get('password'):
                    return jsonify({'code': 400,
                                    'message': 'invalid parameters'}), 400
                if not verify_password(data.get('password'), user['salt'], user['password']):
                    return jsonify({'code': 400,
                                    'message': 'wrong password'}), 400
                # 重复 → 409
                cur.execute(
                    'SELECT 1 FROM users WHERE username = %s',
                    (new_username,)
                )
                if cur.fetchone():
                    return jsonify({'code': 409,
                                    'message': 'username already exists'}), 409

                cur.execute('UPDATE users SET username = %s WHERE userID = %s',
                            (new_username, user['userID']))
                conn.commit()
                return jsonify({'code': 200,
                                'username': new_username,
                                'message': 'username updated successfully'}), 200

            # ---------- 修改密码（没有 new_username 的 PATCH ） ----------
            if request.method == 'PATCH':
                old_password = data.get('old_password')
                new_password = data.get('new_password')
                if not old_password or not new_password:
                    return jsonify({'code': 400,
                                    'message': 'invalid parameters'}), 400

                # 用存的 salt 校验旧密码
                if not verify_password(old_password, user['salt'], user['password']):
                    return jsonify({'code': 400,
                                    'message': 'wrong password'}), 400

                # 重新生成盐值并同时更新 salt 列，否则改密后旧 salt 与新高 hash 不匹配
                new_salt, new_hash = hash_password(new_password)
                cur.execute('UPDATE users SET password = %s, salt = %s WHERE userID = %s',
                            (new_hash, new_salt, user['userID']))
                conn.commit()
                return jsonify({'code': 200,
                                'message': 'password updated successfully'}), 200

            # ----------  注销账号 ----------
            if request.method == 'DELETE':
                pwd = data.get('password')
                if not pwd or not verify_password(pwd, user['salt'], user['password']):
                    return jsonify({'code': 400, 'message': 'wrong password'}), 400
                cur.execute('DELETE FROM users WHERE userID = %s', (user['userID'],))
                conn.commit()
                return '', 204            # 204 不能有响应体，所以返回空字符串
    finally:
        conn.close()


@app.route('/user_list', methods=['GET'])
def user_list():
    return render_template('user_list.html')


@app.route('/users/user_list', methods=['GET'])
def api_user_list():
    sid = (request.headers.get('Session-ID') or '').strip() 
    if not sid:
        return jsonify({'code': 401, 'message': 'Unauthorized'}), 401

    conn = get_db_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(
                'SELECT userID, username FROM users WHERE sessionID = %s',
                (sid,)
            )
            if not cur.fetchone():
                return jsonify({'code': 401, 'message': 'Unauthorized'}), 401

            # 分页参数：转不成数字就回退默认值，避免拼进 SQL 出错
            try:
                page = max(1, int(request.args.get('page', 1)))
                limit = max(1, min(100, int(request.args.get('limit', 20))))
            except ValueError:
                page, limit = 1, 20

            # 3. 只查 username 
            cur.execute(
                'SELECT username FROM users ORDER BY userID LIMIT %s OFFSET %s',
                (limit, (page - 1) * limit)
            )
            rows = cur.fetchall()

            cur.execute('SELECT COUNT(*) AS total FROM users')
            total = cur.fetchone()['total']

        return jsonify({
            'code': 200,
            'data': [{'username': r['username']} for r in rows],
            'total': total,
            'page': page,
            'limit': limit
        }), 200
    finally:
        conn.close()


# 启动入口：python app.py 才走这里；被其他模块 import 时不触发
if __name__ == '__main__':
    app.run('0.0.0.0', 80)