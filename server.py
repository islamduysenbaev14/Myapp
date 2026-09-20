from flask import Flask, request, jsonify
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash


# =========================================================
# MYCHAT SERVER
# =========================================================

app = Flask(__name__)

DB_NAME = "chat.db"


# =========================================================
# DATABASE
# =========================================================

def get_db():

    conn = sqlite3.connect(DB_NAME)

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    conn.close()


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["POST"])
def register():

    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:

        return jsonify({
            "success": False,
            "message": "Login va parolni kiriting."
        })

    if len(username) < 3:

        return jsonify({
            "success": False,
            "message": "Login kamida 3 ta belgidan iborat bo‘lsin."
        })

    if len(password) < 4:

        return jsonify({
            "success": False,
            "message": "Parol kamida 4 ta belgidan iborat bo‘lsin."
        })

    conn = get_db()

    try:

        conn.execute(
            """
            INSERT INTO users
            (username, password)
            VALUES (?, ?)
            """,
            (
                username,
                generate_password_hash(password)
            )
        )

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Ro‘yxatdan o‘tish muvaffaqiyatli."
        })

    except sqlite3.IntegrityError:

        return jsonify({
            "success": False,
            "message": "Bu login allaqachon mavjud."
        })

    finally:

        conn.close()


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["POST"])
def login():

    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:

        return jsonify({
            "success": False,
            "message": "Login va parolni kiriting."
        })

    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE username = ?
        """,
        (username,)
    ).fetchone()

    conn.close()

    if user:

        if check_password_hash(
            user["password"],
            password
        ):

            return jsonify({
                "success": True,
                "user_id": user["id"],
                "username": user["username"]
            })

    return jsonify({
        "success": False,
        "message": "Login yoki parol noto‘g‘ri."
    })


# =========================================================
# USERS
# =========================================================

@app.route("/users", methods=["GET"])
def users():

    current_id = request.args.get("user_id")

    if not current_id:

        return jsonify({
            "success": False,
            "message": "user_id kerak."
        }), 400

    conn = get_db()

    result = conn.execute(
        """
        SELECT id, username
        FROM users
        WHERE id != ?
        ORDER BY username
        """,
        (current_id,)
    ).fetchall()

    conn.close()

    users_list = []

    for user in result:

        users_list.append({
            "id": user["id"],
            "username": user["username"]
        })

    return jsonify(users_list)


# =========================================================
# SEND MESSAGE
# =========================================================

@app.route("/send", methods=["POST"])
def send():

    data = request.get_json(silent=True) or {}

    sender_id = data.get("sender_id")
    receiver_id = data.get("receiver_id")
    message = data.get("message", "").strip()

    if not sender_id or not receiver_id:

        return jsonify({
            "success": False,
            "message": "Foydalanuvchi ID'lari kerak."
        })

    if not message:

        return jsonify({
            "success": False,
            "message": "Xabar bo‘sh bo‘lishi mumkin emas."
        })

    conn = get_db()

    # Foydalanuvchilar mavjudligini tekshirish

    sender = conn.execute(
        """
        SELECT id
        FROM users
        WHERE id = ?
        """,
        (sender_id,)
    ).fetchone()

    receiver = conn.execute(
        """
        SELECT id
        FROM users
        WHERE id = ?
        """,
        (receiver_id,)
    ).fetchone()

    if not sender or not receiver:

        conn.close()

        return jsonify({
            "success": False,
            "message": "Foydalanuvchi topilmadi."
        })

    conn.execute(
        """
        INSERT INTO messages
        (
            sender_id,
            receiver_id,
            message
        )
        VALUES (?, ?, ?)
        """,
        (
            sender_id,
            receiver_id,
            message
        )
    )

    conn.commit()

    conn.close()

    return jsonify({
        "success": True,
        "message": "Xabar yuborildi."
    })


# =========================================================
# GET MESSAGES
# =========================================================

@app.route("/messages", methods=["GET"])
def messages():

    user_id = request.args.get("user_id")
    receiver_id = request.args.get("receiver_id")

    if not user_id or not receiver_id:

        return jsonify({
            "success": False,
            "message": "user_id va receiver_id kerak."
        }), 400

    conn = get_db()

    result = conn.execute(
        """
        SELECT
            messages.id,
            messages.sender_id,
            messages.receiver_id,
            messages.message,
            messages.created_at,
            users.username
        FROM messages

        JOIN users
        ON users.id = messages.sender_id

        WHERE
            (
                messages.sender_id = ?
                AND
                messages.receiver_id = ?
            )

            OR

            (
                messages.sender_id = ?
                AND
                messages.receiver_id = ?
            )

        ORDER BY messages.id ASC
        """,
        (
            user_id,
            receiver_id,
            receiver_id,
            user_id
        )
    ).fetchall()

    conn.close()

    messages_list = []

    for row in result:

        messages_list.append({
            "id": row["id"],
            "sender_id": row["sender_id"],
            "receiver_id": row["receiver_id"],
            "message": row["message"],
            "username": row["username"],
            "created_at": row["created_at"]
        })

    return jsonify(messages_list)


# =========================================================
# SERVER TEST
# =========================================================

@app.route("/")
def home():

    return jsonify({
        "success": True,
        "app": "MyChat",
        "message": "MyChat server ishlayapti."
    })


# =========================================================
# DATABASENI ISHGA TUSHIRISH
# =========================================================

init_db()


# =========================================================
# LOCAL / RENDER SERVER
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    print("================================")
    print("       MYCHAT SERVER")
    print("================================")
    print(f"PORT: {port}")
    print("Server ishga tushdi...")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
