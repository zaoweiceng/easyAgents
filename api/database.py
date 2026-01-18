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
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import markdown as md_lib
from html.parser import HTMLParser
import re

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
                    total_tokens INTEGER DEFAULT 0,
                    paused_context TEXT
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

    # 暂停上下文相关方法
    def save_paused_context(
        self,
        session_id: str,
        paused_context: Dict
    ) -> bool:
        """保存暂停的上下文（用于恢复执行）"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE conversations
                    SET paused_context = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                    """,
                    (json.dumps(paused_context, ensure_ascii=False), session_id)
                )
                conn.commit()
                return True

    def get_paused_context(
        self,
        session_id: str
    ) -> Optional[Dict]:
        """获取暂停的上下文"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT paused_context FROM conversations WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            if row and row['paused_context']:
                try:
                    return json.loads(row['paused_context'])
                except json.JSONDecodeError:
                    return None
            return None

    def clear_paused_context(
        self,
        session_id: str
    ) -> bool:
        """清除暂停的上下文"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE conversations
                    SET paused_context = NULL
                    WHERE session_id = ?
                    """,
                    (session_id,)
                )
                conn.commit()
                return True

    def _extract_thinking_steps(self, events: List[Dict]) -> List[Dict]:
        """从events中提取思考步骤"""
        if not events:
            return []

        thinking_steps = []
        for event in events:
            if event.get('type') == 'agent_end':
                data = event.get('data', {})
                step = {
                    'agent_name': data.get('agent_name', ''),
                    'reason': data.get('agent_selection_reason', ''),
                    'task': None
                }

                task_list = data.get('task_list', [])
                if task_list and len(task_list) > 0:
                    step['task'] = task_list[0]

                thinking_steps.append(step)

        # 过滤掉general_agent（只显示中间过程，不显示最终输出）
        thinking_steps = [s for s in thinking_steps if s['agent_name'] != 'general_agent']
        return thinking_steps

    def _markdown_to_pdf_html(self, markdown_text: str) -> str:
        """将Markdown转换为PDF可用的HTML格式"""
        if not markdown_text:
            return ''

        # 转换markdown为HTML
        html = md_lib.markdown(
            markdown_text,
            extensions=['extra', 'codehilite', 'tables', 'fenced_code']
        )

        # 简化HTML标签以适应ReportLab
        # 标题
        html = re.sub(r'<h1[^>]*>(.*?)</h1>', r'<b><font size="18">\1</font></b><br/>', html)
        html = re.sub(r'<h2[^>]*>(.*?)</h2>', r'<b><font size="16">\1</font></b><br/>', html)
        html = re.sub(r'<h3[^>]*>(.*?)</h3>', r'<b><font size="14">\1</font></b><br/>', html)

        # 粗体和斜体
        html = re.sub(r'<strong>(.*?)</strong>', r'<b>\1</b>', html)
        html = re.sub(r'<b>(.*?)</b>', r'<b>\1</b>', html)
        html = re.sub(r'<em>(.*?)</em>', r'<i>\1</i>', html)
        html = re.sub(r'<i>(.*?)</i>', r'<i>\1</i>', html)

        # 代码块
        html = re.sub(
            r'<pre[^>]*>.*?<code[^>]*>(.*?)</code>.*?</pre>',
            r'<br/><font face="Courier" bgColor="#eeeeee" size="10">\1</font><br/>',
            html,
            flags=re.DOTALL
        )
        html = re.sub(r'<code[^>]*>(.*?)</code>', r'<font face="Courier" size="10">\1</font>', html)

        # 列表
        html = re.sub(r'<ul[^>]*>(.*?)</ul>', lambda m: m.group(1).replace('<li>', '• ').replace('</li>', '<br/>'), html)
        html = re.sub(r'<ol[^>]*>(.*?)</ol>', lambda m: self._number_list(m.group(1)), html)
        html = re.sub(r'<li[^>]*>(.*?)</li>', r'• \1<br/>', html)

        # 表格转换为简单文本
        html = re.sub(r'<table[^>]*>.*?</table>', self._extract_table_text, html, flags=re.DOTALL)

        # 段落和换行
        html = re.sub(r'<p[^>]*>(.*?)</p>', r'\1<br/>', html)
        html = re.sub(r'<br\s*/?>', '<br/>', html)

        # 清理剩余HTML标签
        html = re.sub(r'<[^>]+>', '', html)

        # 清理多余空白
        html = re.sub(r'<br/>+\s*<br/>+', '<br/><br/>', html)
        html = html.strip()

        return html

    def _number_list(self, content: str) -> str:
        """处理有序列表"""
        items = re.findall(r'<li[^>]*>(.*?)</li>', content)
        result = []
        for i, item in enumerate(items, 1):
            result.append(f'{i}. {item}<br/>')
        return ''.join(result)

    def _extract_table_text(self, match) -> str:
        """从表格HTML中提取文本"""
        table_html = match.group(0)
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
        result = []
        for row in rows:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
            text = ' | '.join(cell.strip() for cell in cells)
            result.append(text)
        return '<br/>' + '<br/>'.join(result) + '<br/>'

    def export_conversation_to_pdf(
        self,
        session_id: str
    ) -> Optional[bytes]:
        """导出会话为PDF格式（返回PDF字节流）"""
        conv = self.get_conversation_by_session(session_id)
        if not conv:
            return None

        messages = self.get_messages(conv['id'])

        # 创建PDF字节流
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )

        # 尝试注册中文字体（macOS系统）
        try:
            # macOS中文字体路径
            # 注意：TTC文件需要指定subfontIndex
            font_configs = [
                ('/System/Library/Fonts/STHeiti Light.ttc', 0, 'STHeitiLight'),
                ('/System/Library/Fonts/STHeiti Medium.ttc', 0, 'STHeitiMedium'),
                ('/System/Library/Fonts/PingFang.ttc', 0, 'PingFang'),
            ]

            chinese_font = 'Helvetica'  # 默认回退字体
            for font_path, subfont_index, font_name in font_configs:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('ChineseFont', font_path, subfontIndex=subfont_index))
                        chinese_font = 'ChineseFont'
                        print(f"✓ 成功注册中文字体: {font_name} (从 {font_path})")
                        break
                    except Exception as e:
                        print(f"尝试注册字体 {font_name} 失败: {e}")
                        continue
        except Exception as e:
            print(f"Warning: Could not register Chinese font: {e}")
            chinese_font = 'Helvetica'

        # 创建样式
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=30,
            alignment=1,  # 居中
            fontName=chinese_font
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=12,
            fontName=chinese_font
        )
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            leading=16,
            fontName=chinese_font
        )

        # 构建PDF内容
        elements = []

        # 标题
        elements.append(Paragraph(f"Conversation Record", title_style))
        elements.append(Spacer(1, 12))

        # 元信息表格
        info_data = [
            ['Session ID:', session_id[:20] + '...'],
            ['Created:', conv['created_at']],
            ['Updated:', conv['updated_at']],
            ['Messages:', str(conv['message_count'])]
        ]
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))

        # 添加消息
        for msg in messages:
            # 提取思考步骤
            thinking_steps = []
            if msg.get('events'):
                events = msg['events']
                if isinstance(events, str):
                    try:
                        events = json.loads(events)
                    except:
                        events = []
                thinking_steps = self._extract_thinking_steps(events)

            # 显示思考过程
            if thinking_steps and msg['role'] == 'assistant':
                elements.append(Spacer(1, 12))

                thinking_heading = ParagraphStyle(
                    'ThinkingHeading',
                    parent=styles['Heading3'],
                    fontSize=12,
                    textColor=colors.HexColor('#9333ea'),
                    spaceAfter=8,
                    fontName=chinese_font
                )
                elements.append(Paragraph("🧠 思考过程", thinking_heading))

                for step in thinking_steps:
                    # Agent名称
                    agent_style = ParagraphStyle(
                        'AgentStyle',
                        parent=styles['Normal'],
                        fontSize=10,
                        textColor=colors.HexColor('#6b7280'),
                        fontName=chinese_font,
                        leftIndent=10
                    )
                    elements.append(Paragraph(
                        f"<b>▶ {step['agent_name']}</b>",
                        agent_style
                    ))

                    # 原因
                    if step.get('reason'):
                        reason_style = ParagraphStyle(
                            'ReasonStyle',
                            parent=styles['Normal'],
                            fontSize=9,
                            textColor=colors.HexColor('#4b5563'),
                            fontName=chinese_font,
                            leftIndent=20
                        )
                        # 处理原因中的中文
                        reason_text = step['reason']
                        if chinese_font == 'Helvetica':
                            reason_text = reason_text.encode('ascii', 'ignore').decode('ascii')

                        elements.append(Paragraph(
                            f"<i>{reason_text}</i>",
                            reason_style
                        ))

                    # 任务
                    if step.get('task'):
                        task_style = ParagraphStyle(
                            'TaskStyle',
                            parent=styles['Normal'],
                            fontSize=9,
                            textColor=colors.HexColor('#059669'),
                            fontName=chinese_font,
                            leftIndent=20
                        )
                        task_text = step['task']
                        if chinese_font == 'Helvetica':
                            task_text = task_text.encode('ascii', 'ignore').decode('ascii')

                        elements.append(Paragraph(
                            f"任务: {task_text}",
                            task_style
                        ))

                    elements.append(Spacer(1, 6))

                elements.append(Spacer(1, 8))

            # 角色标题
            if msg['role'] == 'user':
                role_name = 'User'
                role_color = '#3498db'
            else:
                role_name = 'AI Assistant'
                role_color = '#27ae60'

            role_style = ParagraphStyle(
                'RoleStyle',
                parent=styles['Heading3'],
                fontSize=14,
                textColor=colors.HexColor(role_color),
                spaceAfter=8,
                fontName=chinese_font
            )
            elements.append(Paragraph(f"{role_name}", role_style))

            # 时间戳
            if msg['created_at']:
                elements.append(Paragraph(
                    f"<font size='9' color='#7f8c8d'>{msg['created_at']}</font>",
                    normal_style
                ))

            # 消息内容处理
            content = ''

            # 对于用户消息，直接使用content
            if msg['role'] == 'user':
                content = msg.get('content', '')
                if chinese_font == 'Helvetica':
                    content = content.encode('ascii', 'ignore').decode('ascii')

            # 对于AI助手消息，尝试提取结构化数据
            else:
                # 1. 优先从data字段获取（结构化数据）
                if msg.get('data'):
                    msg_data = msg['data']
                    if isinstance(msg_data, str):
                        try:
                            msg_data = json.loads(msg_data)
                        except:
                            pass

                    if isinstance(msg_data, dict):
                        # 尝试提取answer字段
                        if 'data' in msg_data and isinstance(msg_data['data'], dict):
                            content = msg_data['data'].get('answer', '')
                        elif 'answer' in msg_data:
                            content = str(msg_data['answer'])
                        elif 'message' in msg_data:
                            content = str(msg_data['message'])
                        else:
                            content = json.dumps(msg_data, ensure_ascii=False, indent=2)
                    else:
                        content = str(msg_data)

                # 2. 如果data字段为空，尝试从content字段获取
                if not content and msg.get('content'):
                    content = msg['content']

                    # 尝试解析content中的JSON
                    try:
                        if isinstance(content, str) and (content.strip().startswith('{') or content.strip().startswith('[')):
                            # 移除markdown代码块标记
                            content_clean = content.strip()
                            if content_clean.startswith('```'):
                                lines = content_clean.split('\n')
                                if len(lines) > 2:
                                    content_clean = '\n'.join(lines[1:-1])
                                    if content_clean.startswith('json'):
                                        content_clean = content_clean[4:].strip()

                            data = json.loads(content_clean)

                            # 提取answer
                            if isinstance(data, dict):
                                if 'data' in data and isinstance(data['data'], dict):
                                    content = data['data'].get('answer', '')
                                elif 'answer' in data:
                                    content = str(data['answer'])
                                elif 'message' in data:
                                    content = str(data['message'])
                                else:
                                    content = json.dumps(data, ensure_ascii=False, indent=2)
                            else:
                                content = str(data)
                    except (json.JSONDecodeError, ValueError, TypeError):
                        # 解析失败，使用原始内容（可能是markdown）
                        pass

            # 如果还是没有内容，使用默认文本
            if not content:
                content = "(No content available)"

            # 处理长内容
            if len(content) > 10000:
                content = content[:10000] + '\n\n... (Content truncated)'

            # 对于AI助手消息，尝试将Markdown转换为格式化的HTML
            if msg['role'] == 'assistant':
                try:
                    content = self._markdown_to_pdf_html(content)
                except Exception as e:
                    # 如果markdown转换失败，使用原始处理方式
                    print(f"Warning: Markdown conversion failed: {e}")
                    content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    content = content.replace('\n', '<br/>')
            else:
                # 用户消息简单处理换行
                content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                content = content.replace('\n', '<br/>')

            # 如果仍然没有中文字体，检查是否包含中文
            if chinese_font == 'Helvetica':
                # 检查是否包含中文
                has_chinese = any('\u4e00' <= char <= '\u9fff' for char in content)
                if has_chinese:
                    content = "(此PDF包含中文字符，但服务器未成功注册中文字体。中文字符已被过滤。)\n\n" + content.encode('ascii', 'ignore').decode('ascii')
                else:
                    # 只保留ASCII字符
                    content = content.encode('ascii', 'ignore').decode('ascii')

            elements.append(Paragraph(content, normal_style))
            elements.append(Spacer(1, 12))

        # 构建PDF
        try:
            doc.build(elements)
            pdf_bytes = buffer.getvalue()
            buffer.close()
            return pdf_bytes
        except Exception as e:
            print(f"Error building PDF: {e}")
            buffer.close()
            return None


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
