import sqlite3
import os
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
                    progress REAL
                )
            """)
            conn.commit()

    def add_task(self, task_id, title, thumbnail, duration_string, filesize_approx, resolution, filename):
        """Ajoute une nouvelle tâche avec une date actuelle et progress = 0."""
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO tasks (date, task_id, title, thumbnail, duration_string, filesize_approx, resolution, filename, progress)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (date, task_id, title, thumbnail, duration_string, filesize_approx, resolution, filename))
            conn.commit()
            return self.get_task_by_id(task_id)

    def update_progress(self, task_id, progress):
        """Met à jour la progression d'une tâche."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks SET progress = ? WHERE task_id = ?
            """, (progress, task_id))
            conn.commit()

    def get_all_tasks(self):
        """Récupère toutes les tâches triées par date décroissante."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, task_id, title, thumbnail, duration_string, filesize_approx, resolution, filename, progress
                FROM tasks ORDER BY date DESC
            """)
            return cursor.fetchall()

    def get_task_by_id(self, task_id):
        """Récupère une tâche spécifique par task_id."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, task_id, title, thumbnail, duration_string, filesize_approx, resolution, filename, progress
                FROM tasks WHERE task_id = ?
            """, (task_id,))
            return cursor.fetchone()

# Instance globale pour simplifier l'accès
db = Database()
