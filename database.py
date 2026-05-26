import sqlite3
import uuid
from datetime import datetime
import os

class Database:
    def __init__(self, db_path="anonymous_bot.db"):
        """تهيئة قاعدة البيانات"""
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """إنشاء الجداول إذا لم تكن موجودة"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # جدول المستخدمين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                anonymous_id TEXT UNIQUE NOT NULL,
                is_blocked BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول الرسائل
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER,
                recipient_id INTEGER,
                message_type TEXT DEFAULT 'anonymous',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users (user_id),
                FOREIGN KEY (recipient_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_or_create_user(self, user_id, username=None):
        """الحصول على مستخدم أو إنشائه مع معرف مجهول"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # التحقق من وجود المستخدم
        cursor.execute("SELECT anonymous_id FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            anonymous_id = user[0]
            # تحديث اسم المستخدم
            cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
            conn.commit()
        else:
            # إنشاء معرف مجهول جديد
            anonymous_id = str(uuid.uuid4())[:8]
            cursor.execute(
                "INSERT INTO users (user_id, username, anonymous_id) VALUES (?, ?, ?)",
                (user_id, username, anonymous_id)
            )
            conn.commit()
        
        conn.close()
        return anonymous_id
    
    def get_anonymous_id(self, user_id):
        """الحصول على المعرف المجهول لمستخدم"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT anonymous_id FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def get_user_by_anonymous_id(self, anonymous_id):
        """الحصول على معرف المستخدم الحقيقي من المعرف المجهول"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id FROM users WHERE anonymous_id = ?", (anonymous_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def is_blocked(self, user_id):
        """التحقق مما إذا كان المستخدم محظوراً من استقبال الرسائل"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else False
    
    def toggle_block(self, user_id):
        """تبديل حالة الحظر"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
        current = cursor.fetchone()
        
        if current:
            new_status = not current[0]
            cursor.execute("UPDATE users SET is_blocked = ? WHERE user_id = ?", (new_status, user_id))
            conn.commit()
            conn.close()
            return new_status
        
        conn.close()
        return False
    
    def record_message(self, sender_id, recipient_id):
        """تسجيل رسالة في قاعدة البيانات"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO messages (sender_id, recipient_id) VALUES (?, ?)",
            (sender_id, recipient_id)
        )
        
        conn.commit()
        conn.close()
    
    def get_user_stats(self, user_id):
        """الحصول على إحصائيات المستخدم"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # عدد الرسائل المرسلة
        cursor.execute("SELECT COUNT(*) FROM messages WHERE sender_id = ?", (user_id,))
        sent_count = cursor.fetchone()[0]
        
        # عدد الرسائل المستلمة
        cursor.execute("SELECT COUNT(*) FROM messages WHERE recipient_id = ?", (user_id,))
        received_count = cursor.fetchone()[0]
        
        # حالة الحظر
        cursor.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
        blocked = cursor.fetchone()
        
        conn.close()
        
        return {
            'sent': sent_count,
            'received': received_count,
            'blocked': bool(blocked[0]) if blocked else False
        }
