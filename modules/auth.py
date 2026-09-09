import hashlib
from database.db_config import get_connection, close_connection

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def check_password(password, hashed):
    return hash_password(password) == hashed

def create_user(fullname, email, user_id, password):
    conn = get_connection()
    if not conn: return False
    
    cursor = conn.cursor()
    pw_hash = hash_password(password)
    
    try:
        cursor.execute(
            "INSERT INTO users (fullname, email, user_id, password_hash) VALUES (?, ?, ?, ?)",
            (fullname, email, user_id, pw_hash)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Auth Error: {e}")
        return False
    finally:
        close_connection(conn)

def authenticate_user(user_id, password):
    conn = get_connection()
    if not conn: return None
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user:
        # result is sqlite Row or tuple
        if isinstance(user, dict):
            stored_hash = user['password_hash']
        else:
            stored_hash = user[4] # password_hash index
            
        if check_password(password, stored_hash):
            return user
            
    return None

def update_password(user_id, new_password):
    conn = get_connection()
    if not conn: return False
    
    cursor = conn.cursor()
    pw_hash = hash_password(new_password)
    
    try:
        cursor.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (pw_hash, user_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        close_connection(conn)

def update_user_profile(user_id, fullname, email):
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET fullname = ?, email = ? WHERE user_id = ?", (fullname, email, user_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        return False
    finally:
        close_connection(conn)

def get_user_by_id(user_id):
    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()
    except Exception:
        return None
    finally:
        close_connection(conn)

