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
                is_banned BOOLEAN DEFAULT 0,
                ban_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول الرسائل
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER,
                recipient_id INTEGER,
                content TEXT,
                message_type TEXT DEFAULT 'anonymous',
                is_channel_message BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users (user_id),
                FOREIGN KEY (recipient_id) REFERENCES users (user_id)
            )
        ''')
        
        # جدول الرسائل المعلقة للمراجعة
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER,
                anonymous_id TEXT,
                content TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_or_create_user(self, user_id, username=None):
        """الحصول على مستخدم أو إنشائه مع معرف مجهول"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT anonymous_id FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            anonymous_id = user[0]
            cursor.execute("UPDATE users SET username = ?, last_active = CURRENT_TIMESTAMP WHERE user_id = ?", 
                         (username, user_id))
            conn.commit()
        else:
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
        """الحصول على معلومات المستخدم من المعرف المجهول"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT user_id, username, is_blocked FROM users WHERE anonymous_id = ?",
            (anonymous_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'user_id': result[0],
                'username': result[1],
                'is_blocked': bool(result[2])
            }
        return None
    
    def is_blocked(self, user_id):
        """التحقق مما إذا كان المستخدم محظوراً من استقبال الرسائل"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return bool(result[0]) if result else False
    
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
    
    def is_user_banned(self, user_id):
        """التحقق مما إذا كان المستخدم محظوراً تماماً"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return bool(result[0]) if result else False
    
    def ban_user(self, user_id, reason=""):
        """حظر مستخدم"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT OR REPLACE INTO users (user_id, is_banned, ban_reason) VALUES (?, 1, ?)",
            (user_id, reason)
        )
        conn.commit()
        conn.close()
    
    def unban_user(self, user_id):
        """فك حظر مستخدم"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE users SET is_banned = 0, ban_reason = NULL WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    
    def get_banned_users(self):
        """الحصول على قائمة المحظورين"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT user_id, username, ban_reason FROM users WHERE is_banned = 1"
        )
        results = cursor.fetchall()
        conn.close()
        
        return [{'user_id': r[0], 'username': r[1], 'ban_reason': r[2]} for r in results]
    
    def record_message(self, sender_id, recipient_id, content=""):
        """تسجيل رسالة في قاعدة البيانات"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO messages (sender_id, recipient_id, content) VALUES (?, ?, ?)",
            (sender_id, recipient_id, content)
        )
        
        conn.commit()
        conn.close()
    
    def record_channel_message(self, sender_id, content):
        """تسجيل رسالة قناة"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO messages (sender_id, recipient_id, content, is_channel_message) VALUES (?, 0, ?, 1)",
            (sender_id, content)
        )
        
        conn.commit()
        conn.close()
    
    def add_pending_message(self, sender_id, anonymous_id, content):
        """إضافة رسالة معلقة للمراجعة"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO pending_messages (sender_id, anonymous_id, content) VALUES (?, ?, ?)",
            (sender_id, anonymous_id, content)
        )
        
        conn.commit()
        conn.close()
    
    def get_pending_messages(self):
        """الحصول على الرسائل المعلقة"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, sender_id, anonymous_id, content, created_at 
            FROM pending_messages 
            WHERE status = 'pending' 
            ORDER BY created_at DESC
            """
        )
        results = cursor.fetchall()
        conn.close()
        
        return [{
            'id': r[0],
            'sender_id': r[1],
            'anonymous_id': r[2],
            'content': r[3],
            'created_at': r[4]
        } for r in results]
    
    def get_pending_message_content(self, message_id):
        """الحصول على محتوى رسالة معلقة"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT content FROM pending_messages WHERE id = ?", (message_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def approve_message(self, message_id):
        """الموافقة على رسالة"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE pending_messages SET status = 'approved', reviewed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (message_id,)
        )
        conn.commit()
        conn.close()
    
    def reject_message(self, message_id):
        """رفض رسالة"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE pending_messages SET status = 'rejected', reviewed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (message_id,)
        )
        conn.commit()
        conn.close()
    
    def get_received_messages(self, user_id, limit=10):
        """الحصول على أحدث الرسائل المستلمة"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT content, created_at 
            FROM messages 
            WHERE recipient_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
            """,
            (user_id, limit)
        )
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'content': row[0],
                'date': row[1]
            })
        
        conn.close()
        return messages
    
    def get_user_stats(self, user_id):
        """الحصول على إحصائيات المستخدم"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM messages WHERE sender_id = ?", (user_id,))
        sent_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM messages WHERE recipient_id = ?", (user_id,))
        received_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
        blocked = cursor.fetchone()
        
        conn.close()
        
        return {
            'sent': sent_count,
            'received': received_count,
            'blocked': bool(blocked[0]) if blocked else False
        }
    
    def get_all_users(self):
        """الحصول على جميع المستخدمين"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id, username FROM users WHERE is_banned = 0")
        results = cursor.fetchall()
        conn.close()
        
        return [{'user_id': r[0], 'username': r[1]} for r in results]
    
    def get_global_stats(self):
        """الحصول على إحصائيات عامة"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned = 0")
        active_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
        banned_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM messages")
        total_messages = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM messages WHERE is_channel_message = 1")
        channel_messages = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'banned_users': banned_users,
            'total_messages': total_messages,
            'channel_messages': channel_messages,
            'last_update': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
