import os
from pathlib import Path

from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

# Load backend/.env regardless of current working directory
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path)


def get_db_connection():
    """
    Establishes a connection to MySQL.
    Set MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD in backend/.env
    """
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "127.0.0.1"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            database=os.getenv("MYSQL_DATABASE", "legal_analyzer_db"),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            connection_timeout=10,
        )
        if connection.is_connected():
            print("Successfully connected to MySQL database")
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        if e.errno == 1045:
            print("Hint: Access denied - set MYSQL_USER and MYSQL_PASSWORD in backend/.env (copy from .env.example)")
        elif e.errno == 1049:
            print("Hint: Unknown database - create it in MySQL or fix MYSQL_DATABASE in backend/.env")
        elif e.errno in (2003, 2005):
            print("Hint: Server not reachable - is the MySQL Windows service running? Is the port correct?")
        return None

def close_db_connection(connection):
    if connection and connection.is_connected():
        connection.close()
        print("MySQL connection is closed")
