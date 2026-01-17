"""
数据库服务模块
提供SQLite数据库的同步访问接口
"""
import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import threading

class DatabaseService:
    """数据库服务类"""

    def __init__(self, db_path: str = "data/easyagent.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        # 确保数据目录存在
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def initialize(self):
        """初始化数据库，创建表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    session_id TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0,
                    is_pinned BOOLEAN DEFAULT 0,
                    model_name TEXT,
                    total_tokens INTEGER DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    data TEXT,
                    events TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    token_count INTEGER DEFAULT 0,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                        ON DELETE CASCADE
                )
            """)

            # 创建索引
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_session_id
                ON conversations(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_created_at
                ON conversations(created_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_updated_at
                ON conversations(updated_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
                ON messages(conversation_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_created_at
                ON messages(created_at)
            """)

            conn.commit()

    # Conversation 相关方法
    def create_conversation(
        self,
        title: str,
        session_id: str,
        model_name: str = None
    ) -> int:
        """创建新会话"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO conversations
                    (title, session_id, model_name)
                    VALUES (?, ?, ?)
                    """,
                    (title, session_id, model_name)
                )
                conn.commit()
                return cursor.lastrowid

    def get_conversation_by_session(self, session_id: str) -> Optional[Dict]:
        """根据session_id获取会话"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM conversations WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_conversations(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """列出会话（按更新时间降序）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM conversations
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def update_conversation_title(
        self,
        session_id: str,
        title: str
    ) -> bool:
        """更新会话标题"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE conversations
                    SET title = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                    """,
                    (title, session_id)
                )
                conn.commit()
                return True

    def delete_conversation(self, session_id: str) -> bool:
        """删除会话（级联删除消息）"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "DELETE FROM conversations WHERE session_id = ?",
                    (session_id,)
                )
                conn.commit()
                return True

    def search_conversations(
        self,
        query: str,
        limit: int = 20
    ) -> List[Dict]:
        """搜索会话（标题或消息内容）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            search_pattern = f"%{query}%"
            cursor = conn.execute(
                """
                SELECT DISTINCT c.* FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.title LIKE ? OR m.content LIKE ?
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (search_pattern, search_pattern, limit)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    # Message 相关方法
    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        data: Dict = None,
        events: List[Dict] = None
    ) -> int:
        """添加消息"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO messages
                    (conversation_id, role, content, data, events)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        conversation_id,
                        role,
                        content,
                        json.dumps(data, ensure_ascii=False) if data else None,
                        json.dumps(events, ensure_ascii=False) if events else None
                    )
                )
                message_id = cursor.lastrowid

                # 更新会话的 message_count 和 updated_at
                conn.execute(
                    """
                    UPDATE conversations
                    SET message_count = message_count + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (conversation_id,)
                )

                conn.commit()
                return message_id

    def get_messages(
        self,
        conversation_id: int
    ) -> List[Dict]:
        """获取会话的所有消息"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                """,
                (conversation_id,)
            )
            rows = cursor.fetchall()
            messages = []
            for row in rows:
                msg = dict(row)
                # 解析 JSON 字段
                if msg['data']:
                    try:
                        msg['data'] = json.loads(msg['data'])
                    except json.JSONDecodeError:
                        msg['data'] = None
                if msg['events']:
                    try:
                        msg['events'] = json.loads(msg['events'])
                    except json.JSONDecodeError:
                        msg['events'] = None
                messages.append(msg)
            return messages

    def export_conversation(
        self,
        session_id: str
    ) -> Dict:
        """导出会话（包括所有消息）"""
        conv = self.get_conversation_by_session(session_id)
        if not conv:
            return None

        messages = self.get_messages(conv['id'])

        return {
            "conversation": conv,
            "messages": messages,
            "exported_at": datetime.now().isoformat()
        }


# 全局数据库实例
db_service: Optional[DatabaseService] = None

def get_db() -> DatabaseService:
    """获取数据库服务实例"""
    global db_service
    if db_service is None:
        db_path = "data/easyagent.db"
        db_service = DatabaseService(db_path)
        db_service.initialize()
    return db_service
