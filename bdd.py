import sqlite3
import time
from datetime import datetime

class Database:
    def __init__(self, db_path="./data/bdd.sqlite"):
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        """Initialise la base de données et crée la table si elle n'existe pas."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    task_id TEXT UNIQUE NOT NULL,
                    title TEXT,
                    thumbnail TEXT,
                    duration_string TEXT,
                    filesize_approx TEXT,
                    resolution TEXT,
                    filename TEXT,
                    progress REAL,
                    original_url TEXT,
                    status TEXT DEFAULT 'ongoing'  -- Unix timestamp ou '1'
                )
            """)
            conn.commit()

    def add_task(self, task_id, title, thumbnail, duration_string, filesize_approx, resolution, filename, original_url):
        """Ajoute une nouvelle tâche avec un timestamp Unix."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        timestamp = str(int(time.time()))
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO tasks (
                    date, task_id, title, thumbnail, duration_string,
                    filesize_approx, resolution, filename, progress,
                    original_url, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """, (now, task_id, title, thumbnail, duration_string,
                  filesize_approx, resolution, filename, original_url, timestamp))
            conn.commit()
            return self.get_task_by_id(task_id)

    def update_progress(self, task_id, progress):
        """Met à jour la progression avec un timestamp Unix, ou '1' si terminé."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if progress >= 100:
                cursor.execute("""
                    UPDATE tasks SET progress = ?, status = '1'
                    WHERE task_id = ?
                """, (progress, task_id))
            else:
                timestamp = str(int(time.time()))
                cursor.execute("""
                    UPDATE tasks SET progress = ?, status = ?
                    WHERE task_id = ?
                """, (progress, timestamp, task_id))
            conn.commit()

    def get_all_tasks_paginated(self, page=1, per_page=5):
        """Récupère les tâches triées par date décroissante avec pagination."""
        offset = (page - 1) * per_page
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tasks")
            total = cursor.fetchone()[0]
            cursor.execute("""
                SELECT date, task_id, title, thumbnail, duration_string,
                       filesize_approx, resolution, filename, progress,
                       original_url, status
                FROM tasks ORDER BY date DESC LIMIT ? OFFSET ?
            """, (per_page, offset))
            tasks = cursor.fetchall()
            total_pages = (total + per_page - 1) // per_page if total > 0 else 1
            return tasks, total_pages, total

    def get_task_by_id(self, task_id):
        """Récupère une tâche spécifique par task_id."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, task_id, title, thumbnail, duration_string,
                       filesize_approx, resolution, filename, progress,
                       original_url, status
                FROM tasks WHERE task_id = ?
            """, (task_id,))
            return cursor.fetchone()

# Instance globale
db = Database()
