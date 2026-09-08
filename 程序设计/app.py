import uuid

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
    'database': 'recruit_quizzes_test_four_database',
    'charset': 'utf8mb4'
}



def get_db_connection():
    return pymysql.connect(**DB_CONFIG)


# def init_db():
#     """启动时建库建表，幂等，可重复执行。"""
#     # 第一步：先连服务器（不带 database 参数），建库
#     cfg = dict(DB_CONFIG)
#     db_name = cfg.pop('database')
#     conn = pymysql.connect(**cfg)
#     try:
#         with conn.cursor() as cur:
#             cur.execute(
#                 f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4"
#             )
#         conn.commit()
#     finally:
#         conn.close()

#     # 第二步：连指定库，建表
#     conn = pymysql.connect(**DB_CONFIG)
#     try:
#         with conn.cursor() as cur:
#             cur.execute('''
#                 CREATE TABLE IF NOT EXISTS users (
#                     userID   INT AUTO_INCREMENT PRIMARY KEY,   -- 主键必须是 userID 单列，否则 AUTO_INCREMENT 会重复
#                     username VARCHAR(50)  NOT NULL UNIQUE,      -- UNIQUE 让"用户名重复"由数据库兜底（409）
#                     password VARCHAR(255) NOT NULL
#                 )
#             ''')
#         conn.commit()
#     finally:
#         conn.close()
#     print('[DB] users 表已就绪')


@app.route('/')
def home():
    return redirect('/login')


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
                    'SELECT userID, username, password FROM users WHERE username = %s',
                    (username,)
                )
                user = cur.fetchone()
                if not user or user['password'] != password:
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
            conn.close()                          # 用 try/finally 保证一定关，原代码关两次容易出错

    return render_template('login.html')


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
                    return jsonify({'code': 409,
                                    'message': 'username already exists'}), 409
                session_id = str(uuid.uuid4())
                cur.execute(
                    'INSERT INTO users (username, password, sessionID) VALUES (%s, %s, %s)',
                    (username, password, session_id)
                )
                user_id = cur.lastrowid
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
    """个人中心页面 —— 只负责返回 HTML，不含任何数据

    页面本身谁都能打开；真正的数据由页面里的 JS 请求 /users/me 获取。
    没登录时那个接口返回 401，页面显示「未登录」。
    （页面路由不能返回 JSON，否则浏览器点菜单看到的是一堆文本而不是页面）
    """
    return render_template('me.html')

@app.route('/users/me', methods=['GET', 'PATCH', 'DELETE'])
def api_me():
    """个人中心数据接口：GET 查看 / PATCH 改用户名或密码 / DELETE 注销

    三个操作都要登录态：从请求头 Session-ID 取凭据，去数据库比对，
    查不到一律 401。PATCH 的两个操作靠请求体里的字段名区分。
    """
    sid = (request.headers.get('Session-ID') or '').strip()
    if not sid:
        return jsonify({'code': 401, 'message': 'Unauthorized'}), 401

    conn = get_db_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            # 1. 凭 sessionID 查库——这就是"比对"本身
            cur.execute(
                'SELECT userID, username, password FROM users WHERE sessionID = %s',
                (sid,)
            )
            user = cur.fetchone()
            if not user:
                return jsonify({'code': 401, 'message': 'Unauthorized'}), 401

            # ---------- 3. 查看个人信息 ----------
            if request.method == 'GET':
                return jsonify({
                    'code': 200,
                    'data': {
                        'userID':   user['userID'],
                        'username': user['username']
                    }
                }), 200

            data = request.get_json(silent=True) or {}

            # ---------- 5. 修改用户名（有 new_username 就走这条） ----------
            if request.method == 'PATCH' and 'new_username' in data:
                new_username = (data.get('new_username') or '').strip()
                if not new_username or not data.get('password'):
                    return jsonify({'code': 400,
                                    'message': 'invalid parameters'}), 400
                # 改用户名要验密码，防止别人捡到已登录的页面乱改
                if data.get('password') != user['password']:
                    return jsonify({'code': 400,
                                    'message': 'wrong password'}), 400
                # 排除自己再查重，否则改成同名也会被判重复
                cur.execute(
                    'SELECT 1 FROM users WHERE username = %s AND userID != %s',
                    (new_username, user['userID'])
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

            # ---------- 6. 修改密码（没有 new_username 的 PATCH 走这条） ----------
            if request.method == 'PATCH':
                old_password = data.get('old_password')
                new_password = data.get('new_password')
                if not old_password or not new_password:
                    return jsonify({'code': 400,
                                    'message': 'invalid parameters'}), 400
                if old_password != user['password']:
                    return jsonify({'code': 400,
                                    'message': 'wrong password'}), 400

                cur.execute('UPDATE users SET password = %s WHERE userID = %s',
                            (new_password, user['userID']))
                conn.commit()
                return jsonify({'code': 200,
                                'message': 'password updated successfully'}), 200

            # ---------- 7. 注销账号 ----------
            if request.method == 'DELETE':
                if not data.get('password') or data.get('password') != user['password']:
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
    """查看用户列表（需要登录态）

    从请求头 Session-ID 读取凭据，去数据库比对：
      - 请求头没带 → 401
      - 数据库查不到这个 sessionID → 401
      - 查得到 → 返回用户列表，只含用户名（不返回密码和 sessionID）
    """
    sid = (request.headers.get('Session-ID') or '').strip() 
    if not sid:
        return jsonify({'code': 401, 'message': 'Unauthorized'}), 401

    conn = get_db_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            # 1. 凭 sessionID 查库，查不到就是没登录或已失效
            cur.execute(
                'SELECT userID, username FROM users WHERE sessionID = %s',
                (sid,)
            )
            if not cur.fetchone():
                return jsonify({'code': 401, 'message': 'Unauthorized'}), 401

            # 2. 分页参数：转不成数字就回退默认值，避免拼进 SQL 出错
            try:
                page = max(1, int(request.args.get('page', 1)))
                limit = max(1, min(100, int(request.args.get('limit', 20))))
            except ValueError:
                page, limit = 1, 20

            # 3. 只查 username —— 密码和 sessionID 绝不能出现在响应里
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