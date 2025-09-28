#!/usr/bin/env python3
"""
Migrate data from SQLite to PostgreSQL
"""
import sqlite3
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_sqlite_to_postgres():
    """Migrate test_memory.db to PostgreSQL"""
    
    # Connect to SQLite
    sqlite_conn = sqlite3.connect('chatbot/test_memory.db')
    sqlite_cursor = sqlite_conn.cursor()
    
    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    pg_cursor = pg_conn.cursor()
    
    try:
        # Get all tables from SQLite
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = sqlite_cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            print(f"Migrating table: {table_name}")
            
            # Get table data
            sqlite_cursor.execute(f"SELECT * FROM {table_name}")
            rows = sqlite_cursor.fetchall()
            
            # Get column names
            sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in sqlite_cursor.fetchall()]
            
            # Create table in PostgreSQL (simplified - you may need to adjust types)
            create_query = f"CREATE TABLE IF NOT EXISTS {table_name} ("
            for col in columns:
                create_query += f"{col} TEXT, "
            create_query = create_query[:-2] + ")"
            pg_cursor.execute(create_query)
            
            # Insert data
            for row in rows:
                placeholders = ', '.join(['%s'] * len(row))
                insert_query = f"INSERT INTO {table_name} VALUES ({placeholders})"
                pg_cursor.execute(insert_query, row)
        
        pg_conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        pg_conn.rollback()
        
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == "__main__":
    migrate_sqlite_to_postgres()