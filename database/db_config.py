import os
import sqlite3
import mysql.connector
from mysql.connector import Error

# Configuration toggles between SQLite and MySQL
# Use SQLite by default for easy demo initialization
USE_MYSQL = os.environ.get("USE_MYSQL", "false").lower() == "true"

def get_connection():
    if USE_MYSQL:
        try:
            return mysql.connector.connect(
                host=os.environ.get("MYSQL_HOST", "localhost"),
                user=os.environ.get("MYSQL_USER", "root"),
                password=os.environ.get("MYSQL_PASSWORD", ""),
                database=os.environ.get("MYSQL_DATABASE", "fdas_db")
            )
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return None
    else:
        # Fallback to SQLite
        try:
            conn = sqlite3.connect("fdas_local.db")
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            print(f"Error connecting to SQLite: {e}")
            return None

def close_connection(conn):
    if conn:
        conn.close()
