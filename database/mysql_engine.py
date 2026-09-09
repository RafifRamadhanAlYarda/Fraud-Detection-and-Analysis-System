import mysql.connector
from mysql.connector import Error
import os

class MySQLEngine:
    """
    Enterprise-grade MySQL connector for fdas_db.
    Handles history, results, and investigation logs.
    """
    def __init__(self):
        self.host = os.environ.get("MYSQL_HOST", "localhost")
        self.user = os.environ.get("MYSQL_USER", "root")
        self.password = os.environ.get("MYSQL_PASSWORD", "")
        self.database = os.environ.get("MYSQL_DATABASE", "fdas_db")

    def get_connection(self):
        try:
            return mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
        except Error as e:
            print(f"MySQL Error: {e}")
            return None

    def execute_query(self, query, params=None):
        conn = self.get_connection()
        if not conn: return None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            if query.strip().upper().startswith("SELECT"):
                result = cursor.fetchall()
            else:
                conn.commit()
                result = cursor.rowcount
            return result
        except Error as e:
            print(f"Query Error: {e}")
            return None
        finally:
            conn.close()

    def save_investigation_log(self, account_id, decision, reason, analyst_id):
        query = """
        INSERT INTO investigation_log (account_id, decision, reason, analyst_id)
        VALUES (%s, %s, %s, %s)
        """
        return self.execute_query(query, (account_id, decision, reason, analyst_id))
