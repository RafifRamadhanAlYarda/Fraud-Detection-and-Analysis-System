from .db_config import get_connection, close_connection

def init_db():
    conn = get_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Table users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT NOT NULL,
        email TEXT NOT NULL,
        user_id TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Table transaction_dictionary
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transaction_dictionary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grup TEXT,
        jenis_transaksi TEXT,
        deskripsi TEXT,
        keterangan_remark TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Table analysis_history (Scientific refinement)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        filename TEXT NOT NULL,
        lightgbm_score REAL,
        lstm_score REAL,
        hybrid_score REAL,
        alpha REAL,
        fraud_status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Table investigation_log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS investigation_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id TEXT NOT NULL,
        decision TEXT,
        reason TEXT,
        analyst_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Table operational_decision_log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS operational_decision_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        investigation_id INTEGER,
        action TEXT,
        priority TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(investigation_id) REFERENCES investigation_log(id)
    )
    """)

    conn.commit()
    close_connection(conn)

if __name__ == "__main__":
    init_db()
