"""
对话上下文管理器
管理每个对话的完整历史和简化上下文
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class ConversationContext:
    """单个对话的上下文"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.full_messages: List[Dict[str, Any]] = []  # 完整消息历史
        self.context_for_llm: List[Dict[str, Any]] = []  # 传给LLM的简化上下文
        self.created_at = datetime.now()

    def add_user_message(self, content: str):
        """添加用户消息"""
        user_msg = {
            "role": "user",
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.full_messages.append(user_msg)
        self.context_for_llm.append({
            "role": "user",
            "content": content
        })

    def add_assistant_message(
        self,
        full_response: str,  # 完整的原始响应（包含所有agent的调用）
        final_answer: str,   # general_agent的最终答案
        thinking_steps: List[Dict]  # 思考过程（用于前端显示）
    ):
        """添加助手消息"""
        assistant_msg = {
            "role": "assistant",
            "content": full_response,
            "final_answer": final_answer,
            "thinking_steps": thinking_steps,
            "timestamp": datetime.now().isoformat()
        }
        self.full_messages.append(assistant_msg)

        # 只保存最终答案到LLM上下文
        self.context_for_llm.append({
            "role": "assistant",
            "content": final_answer
        })

    def get_context_for_llm(self) -> List[Dict[str, str]]:
        """获取传给LLM的简化上下文"""
        return self.context_for_llm.copy()

    def get_full_history(self) -> List[Dict[str, Any]]:
        """获取完整历史（用于前端显示和数据库保存）"""
        return self.full_messages.copy()

    def clear(self):
        """清空上下文"""
        self.full_messages = []
        self.context_for_llm = []


class ContextManager:
    """管理所有对话的上下文"""

    def __init__(self, db_service=None):
        self.conversations: Dict[str, ConversationContext] = {}
        self.db_service = db_service

    def get_or_create_context(self, session_id: str) -> ConversationContext:
        """获取或创建对话上下文"""
        if session_id not in self.conversations:
            # 创建新的上下文
            ctx = ConversationContext(session_id)

            # 如果提供了数据库服务，尝试从数据库加载历史
            if self.db_service:
                self._load_context_from_db(ctx, session_id)

            self.conversations[session_id] = ctx

        return self.conversations[session_id]

    def _load_context_from_db(self, ctx: ConversationContext, session_id: str):
        """从数据库加载并重建上下文"""
        try:
            # 获取会话信息
            conv = self.db_service.get_conversation_by_session(session_id)
            if not conv:
                # 新会话，数据库中不存在
                return

            # 获取消息历史
            messages = self.db_service.get_messages(conv['id'])
            logger.info(f"从数据库加载会话 {session_id} 的 {len(messages)} 条消息")

            # 重建上下文
            for msg in messages:
                if msg['role'] == 'user':
                    # 用户消息直接添加
                    ctx.add_user_message(msg['content'])

                elif msg['role'] == 'assistant':
                    # 助手消息需要提取final_answer
                    final_answer = self._extract_final_answer(msg['content'])
                    thinking_steps = self._extract_thinking_steps(msg['content'])

                    ctx.add_assistant_message(
                        full_response=msg['content'],
                        final_answer=final_answer,
                        thinking_steps=thinking_steps
                    )

            logger.info(f"会话 {session_id} 上下文重建完成: {len(ctx.context_for_llm)} 条简化消息")

        except Exception as e:
            logger.error(f"从数据库加载上下文失败: {e}")

    def _extract_final_answer(self, content: str) -> str:
        """从完整响应中提取最终答案"""
        try:
            # 尝试找到所有JSON对象
            import re
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            json_matches = re.findall(json_pattern, content.replace('\n', ''))

            if json_matches:
                # 从后往前找第一个有answer且没有form_config的JSON（general_agent的最终响应）
                for last_json in reversed(json_matches):
                    data = json.loads(last_json)
                    data_field = data.get('data')
                    if data_field:
                        # 跳过包含form_config的消息（表单请求不算最终答案）
                        if isinstance(data_field, dict) and data_field.get('form_config'):
                            continue

                        # 处理dict和对象两种情况
                        if isinstance(data_field, dict) and data_field.get('answer'):
                            return data_field['answer']
                        elif hasattr(data_field, 'answer') and data_field.answer:
                            return data_field.answer
        except Exception as e:
            logger.debug(f"提取final_answer失败: {e}")

        # 如果解析失败，返回原文
        return content

    def _extract_thinking_steps(self, content: str) -> List[Dict]:
        """从完整响应中提取思考步骤"""
        try:
            # 尝试找到所有JSON对象
            import re
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            json_matches = re.findall(json_pattern, content.replace('\n', ''))

            thinking_steps = []
            for match in json_matches:
                try:
                    json_obj = json.loads(match)
                    # 跳过entrance_agent和没有实际工作的agent
                    if json_obj.get('agent_selection_reason') or json_obj.get('data'):
                        agent_name = self._extract_agent_name(json_obj)
                        if agent_name and agent_name not in ['entrance_agent', 'general_agent']:
                            task_list = json_obj.get('task_list')
                            thinking_steps.append({
                                "agent_name": agent_name,
                                "reason": json_obj.get('agent_selection_reason', ''),
                                "task": task_list[0] if task_list else None
                            })
                except json.JSONDecodeError:
                    continue

            return thinking_steps
        except Exception as e:
            logger.debug(f"提取thinking_steps失败: {e}")
            return []

    def _extract_agent_name(self, json_obj: Dict) -> Optional[str]:
        """从JSON对象中提取agent名称"""
        # 从next_agent字段提取
        if json_obj.get('next_agent') and json_obj['next_agent'] != 'none':
            return json_obj['next_agent']

        # 从content中提取（## agent_name格式）
        content = json_obj.get('content', '')
        if content and '##' in content:
            parts = content.split('##')
            if len(parts) > 1:
                agent_name = parts[1].strip().split()[0]
                if agent_name and agent_name != 'none':
                    return agent_name

        return None

    def set_db_service(self, db_service):
        """设置数据库服务（用于延迟初始化）"""
        self.db_service = db_service

    def remove_context(self, session_id: str):
        """删除对话上下文"""
        if session_id in self.conversations:
            del self.conversations[session_id]

    def clear_all(self):
        """清空所有上下文"""
        self.conversations.clear()


# 全局上下文管理器实例
context_manager = ContextManager()
