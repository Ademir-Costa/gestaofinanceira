import os
import sqlite3
from datetime import datetime

DATABASE_DIR = 'instance'
DATABASE_PATH = os.path.join(DATABASE_DIR, 'finance.db')

def init_db():
    os.makedirs(DATABASE_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                type TEXT NOT NULL,
                installments INTEGER DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0,
                target_date TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    except Exception as e:
        print(f"Erro ao criar tabelas: {e}")
        conn.rollback()
    finally:
        conn.close()
        
def add_goal(name, target_amount, current_amount, target_date):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO goals (name, target_amount, current_amount, target_date)
        VALUES (?, ?, ?, ?)
    ''', (name, target_amount, current_amount, target_date))
    conn.commit()
    conn.close()
    
def get_goal_by_id(goal_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM goals WHERE id = ?', (goal_id,))
    goal = cursor.fetchone()
    conn.close()
    
    if goal:
        return {
            'id': goal[0],
            'name': goal[1],
            'target_amount': goal[2],
            'current_amount': goal[3],
            'target_date': goal[4]
        }
    return None

def add_entry(date, category, amount, entry_type, installments):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO entries (date, category, amount, type, installments)
        VALUES (?, ?, ?, ?, ?)
    ''', (date, category, amount, entry_type, installments))
    conn.commit()
    conn.close()

def get_entries():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM entries ORDER BY date DESC')
    entries = cursor.fetchall()
    conn.close()
    return entries

def delete_entry(entry_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM entries WHERE id = ?', (entry_id,))
    conn.commit()
    conn.close()

def add_to_goal(goal_id, amount):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE goals
        SET current_amount = current_amount + ?
        WHERE id = ?
    ''', (amount, goal_id))
    conn.commit()
    conn.close()

def get_goals():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM goals ORDER BY target_date')
    goals = cursor.fetchall()
    conn.close()
    return goals

def delete_goal(goal_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM goals WHERE id = ?', (goal_id,))
    conn.commit()
    conn.close()

def update_goal(goal_id, name, target_amount, current_amount, target_date):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE goals
        SET name = ?, target_amount = ?, current_amount = ?, target_date = ?
        WHERE id = ?
    ''', (name, target_amount, current_amount, target_date, goal_id))
    conn.commit()
    conn.close()