"""
文本文件读取Agent - 读取和分析文本文件

功能：
1. 读取用户上传的文本文件（txt, md, csv, json, xml, yaml, log等）
2. 根据用户问题智能提取相关部分
3. 将提取的内容交给后续Agent进行总结和分析
"""

import re
import os
import json
import logging
from typing import Dict, Any, List, Optional
from core.agent import Agent
from core.base_model import Message
from core.prompt.template_model import PromptTemplate

logger = logging.getLogger(__name__)

# ================================
# 提示词模板
# ================================

system_instructions = """
你是一位专业的文件内容分析专家，擅长从文本文件中提取和整理信息。

你需要能够：
1. 识别用户上传的文本文件
2. 理解用户的问题和需求
3. 从文件中提取相关的内容片段
4. 将提取的内容整理成易于理解的格式
"""

core_instructions = """
# 任务流程

1. 分析用户请求：
   - 识别文件ID（格式：[文件: filename.txt, ID: xxx]）
   - 理解用户的问题或需求
   - 确定需要提取的内容类型

2. 读取并处理文件：
   - 根据文件ID读取文件内容
   - 根据用户问题提取相关部分
   - 如果用户没有特定问题，返回文件开头部分

3. 返回结果：
   - 将提取的完整内容放在answer字段中
   - 提供文件的基本信息（行数、字符数等）
   - 返回成功状态

# 重要说明

- 你的任务是读取和提取文件内容，不要进行复杂的分析
- 将完整的文件内容传递给general_agent进行最终总结
- 如果文件ID不存在，返回友好的错误提示
"""


class TextReaderAgent(Agent):
    """文本文件读取和分析Agent"""

    def __init__(self):
        super().__init__(
            name="text_reader_agent",
            description="读取用户上传的文本文件，提取与用户问题相关的内容。支持txt、md、csv、json、xml、yaml、log等多种文本文件格式。",
            handles=[
                "读取文件", "分析文件", "文件内容", "查看文件", "提取文件",
                "文件", "文档", "读取", "分析", "查看",
                "txt", "csv", "json", "xml", "yaml", "log",
                "[文件:", "ID:",  # 文件ID格式
            ],
            parameters={
                "query": "用户的问题或需求",
                "file_id": "上传文件的ID"
            }
        )

        # 初始化提示词模板
        self.prompt_template = PromptTemplate(
            system_instructions=system_instructions,
            available_agents=None,  # 由agent_manager动态设置
            core_instructions=core_instructions,
            data_fields=None
        )

    def run(self, message: Message) -> Message:
        """主处理逻辑"""
        # 从消息中提取文件ID（参考 web_summarizer_agent 的做法）
        file_id = self._extract_file_id(message)

        # 验证文件ID
        if not file_id:
            return Message(
                status="error",
                task_list=["读取文件"],
                data={"error": "未找到文件ID"},
                next_agent="none",
                agent_selection_reason="文件ID提取失败",
                message="请在消息中包含文件ID，格式：[文件: filename.txt, ID: xxx]"
            )

        # 读取文件
        file_data = self._read_text_file(file_id)

        if not file_data.get("success"):
            error_msg = file_data.get("error", "文件读取失败")
            logger.error(f"读取文件失败: {error_msg}")
            return Message(
                status="error",
                task_list=["读取文件"],
                data={"file_id": file_id, "error": error_msg},
                next_agent="none",
                agent_selection_reason="文件读取失败",
                message=f"无法读取文件: {error_msg}"
            )

        # 获取用户问题
        user_query = self._extract_user_query(message)

        # 格式化文件内容
        full_content = self._format_content_for_llm(
            file_data["content"],
            file_data["filename"],
            user_query
        )

        # 传递给 general_agent 进行分析
        # 构建简短的摘要消息
        file_summary = (f"已成功读取文件 {file_data['filename']}，共 {file_data['line_count']} 行，"
                       f"{file_data['char_count']} 个字符。文件类型: .{file_data['extension']}")

        # 为了避免上下文溢出，不传递完整的 raw_content
        # 只传递格式化后的内容（已经截断）
        return Message(
            status="success",
            task_list=["读取文件", "提取内容"],
            data={
                "file_info": {
                    "filename": file_data["filename"],
                    "file_id": file_id,
                    "line_count": file_data["line_count"],
                    "char_count": file_data["char_count"],
                    "extension": file_data["extension"]
                },
                "answer": file_summary,
                "user_query": user_query,
                "formatted_content": full_content,  # 已截断的格式化内容
                # 不传递 raw_content 以避免上下文溢出
            },
            next_agent="general_agent",
            agent_selection_reason="文件内容已读取并格式化，传递给general_agent进行分析和回答",
            message=file_summary
        )

    def _extract_file_id(self, message: Message) -> Optional[str]:
        """从消息中提取文件ID（参考 web_summarizer_agent 的 URL 提取逻辑）"""

        # 🔍 详细调试：打印完整的 message 对象
        logger.info(f"[text_reader_agent] ===== 开始提取文件ID =====")
        logger.info(f"[text_reader_agent] message.data: {message.data}")
        logger.info(f"[text_reader_agent] message.task_list: {message.task_list}")
        logger.info(f"[text_reader_agent] message.message: {getattr(message, 'message', 'N/A')}")

        # 尝试使用 model_dump() 获取完整结构
        try:
            message_dict = message.model_dump()
            logger.info(f"[text_reader_agent] message.model_dump(): {json.dumps(message_dict, ensure_ascii=False, indent=2)[:500]}")
        except:
            pass

        # 1. 先尝试从 message.data 获取
        if message.data:
            if isinstance(message.data, dict):
                logger.info(f"[text_reader_agent] message.data 是 dict，包含键: {list(message.data.keys())}")
                # 检查常见的字段名
                for key in ["file_id", "fileId", "id", "content"]:
                    value = message.data.get(key)
                    logger.info(f"[text_reader_agent] 检查字段 '{key}': {value}")
                    if value:
                        # 如果是字符串，尝试提取文件ID
                        if isinstance(value, str):
                            file_id = self._find_file_id_in_text(value)
                            if file_id:
                                logger.info(f"[text_reader_agent] ✓ 从字段 '{key}' 提取到文件ID: {file_id}")
                                return file_id

        # 2. 从 message.message 中提取
        if hasattr(message, 'message') and message.message:
            logger.info(f"[text_reader_agent] 从 message.message 中查找...")
            file_id = self._find_file_id_in_text(message.message)
            if file_id:
                logger.info(f"[text_reader_agent] ✓ 从 message.message 提取到文件ID: {file_id}")
                return file_id

        # 3. 从 message.task_list 中提取
        if message.task_list:
            logger.info(f"[text_reader_agent] 检查 task_list: {message.task_list}")
            for i, task in enumerate(message.task_list):
                logger.info(f"[text_reader_agent] 检查 task_list[{i}]: {task}")
                if isinstance(task, str):
                    file_id = self._find_file_id_in_text(task)
                    if file_id:
                        logger.info(f"[text_reader_agent] ✓ 从 task_list[{i}] 提取到文件ID: {file_id}")
                        return file_id

        # 4. 最后的尝试：从完整的 model_dump JSON 中查找
        try:
            message_json = json.dumps(message.model_dump(), ensure_ascii=False)
            logger.info(f"[text_reader_agent] 从完整 JSON 中查找...")
            file_id = self._find_file_id_in_text(message_json)
            if file_id:
                logger.info(f"[text_reader_agent] ✓ 从完整 JSON 提取到文件ID: {file_id}")
                return file_id
        except:
            pass

        logger.warning(f"[text_reader_agent] ✗ 未能从消息中提取文件ID")
        logger.info(f"[text_reader_agent] ===== 提取结束 =====")
        return None

    def _find_file_id_in_text(self, text: str) -> Optional[str]:
        """从文本中查找文件ID"""
        # 支持的格式：
        # [文件: name.txt, ID: uuid]
        # ID: uuid
        # file_id: uuid
        patterns = [
            r'\[文件:\s*[^,\]]+,\s*ID:\s*([a-f0-9-]+)\]',  # [文件: name, ID: uuid]
            r'ID:\s*([a-f0-9-]+)',  # ID: uuid
            r'file[_-]?id:\s*([a-f0-9-]+)',  # file_id: uuid (忽略大小写)
            r'"file_id"\s*:\s*"([a-f0-9-]+)"',  # JSON格式
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                file_id = match.group(1)
                logger.info(f"[text_reader_agent] 找到文件ID: {file_id}")
                return file_id

        return None

    def _extract_user_query(self, message: Message) -> str:
        """从消息中提取用户的问题"""
        # 收集所有可能的文本
        query_parts = []

        # 从 message.data 获取
        if message.data and isinstance(message.data, dict):
            for key in ["content", "query", "user_query", "question"]:
                value = message.data.get(key)
                if value and isinstance(value, str):
                    query_parts.append(value)

        # 从 message.message 获取
        if hasattr(message, 'message') and message.message:
            query_parts.append(message.message)

        # 从 task_list 获取
        if message.task_list:
            query_parts.extend([str(t) for t in message.task_list])

        # 合并并移除文件引用
        combined = " ".join(query_parts)
        # 移除文件引用
        combined = re.sub(r'\[文件:\s*[^,\]]+,\s*ID:\s*[a-f0-9-]+\]', '', combined)
        combined = combined.strip()

        return combined if combined else "请总结这个文件的内容"

    def _read_text_file(self, file_id: str) -> Dict[str, Any]:
        """读取文本文件"""
        from core.file_service import get_file_service

        # 使用文件服务查找文件记录
        file_service = get_file_service()
        file_record = file_service.get_file(file_id)

        if not file_record:
            # 如果直接通过file_id找不到，尝试遍历目录
            logger.warning(f"[text_reader_agent] 无法通过file_id找到记录，尝试遍历目录")
            return self._read_text_file_by_scan(file_id)

        # 获取文件路径
        file_path = file_service.get_file_path(file_id)
        if not file_path:
            return {
                "success": False,
                "error": "文件路径不存在"
            }

        filename = file_record.original_filename
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

        # 支持的文本文件类型
        text_extensions = {
            'txt', 'md', 'markdown', 'csv', 'json', 'xml', 'yaml', 'yml',
            'log', 'conf', 'ini', 'env', 'py', 'js', 'ts', 'jsx', 'tsx',
            'java', 'c', 'cpp', 'h', 'go', 'rs', 'sql', 'html', 'css'
        }

        if ext not in text_extensions:
            return {
                "success": False,
                "error": f"不支持的文件类型: .{ext}"
            }

        # 读取文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')

            logger.info(f"[text_reader_agent] ✓ 成功读取文件: {filename}")

            return {
                "success": True,
                "filename": filename,
                "file_id": file_id,
                "content": content,
                "line_count": len(lines),
                "char_count": len(content),
                "extension": ext
            }

        except UnicodeDecodeError:
            # 尝试GBK编码
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()

                lines = content.split('\n')

                return {
                    "success": True,
                    "filename": filename,
                    "file_id": file_id,
                    "content": content,
                    "line_count": len(lines),
                    "char_count": len(content),
                    "extension": ext
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"文件编码错误: {str(e)}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"读取异常: {str(e)}"
            }

    def _read_text_file_by_scan(self, file_id: str) -> Dict[str, Any]:
        """通过遍历目录查找文件（备用方案）"""
        storage_dir = "data/files/uploads"

        if not os.path.exists(storage_dir):
            return {
                "success": False,
                "error": "上传目录不存在"
            }

        # 列出所有文件，查找匹配的
        all_files = []
        for filename in os.listdir(storage_dir):
            filepath = os.path.join(storage_dir, filename)
            try:
                # 获取文件的完整信息（读取文件的前几个字节）
                with open(filepath, 'rb') as f:
                    header = f.read(100)
                    # 尝试解析是否有文件ID信息
                    # 这里简单处理：返回所有文件列表供调试
                    all_files.append(filename)
            except:
                pass

        logger.warning(f"[text_reader_agent] 目录中的文件: {all_files}")
        return {
            "success": False,
            "error": f"文件ID {file_id} 不存在，目录中的文件: {all_files}"
        }

    def _format_content_for_llm(
        self,
        content: str,
        filename: str,
        user_query: str
    ) -> str:
        """格式化文件内容供LLM使用（智能分段和检索）"""
        lines = content.split('\n')

        parts = []
        parts.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        parts.append(f"文件名: {filename}\n")
        parts.append(f"总行数: {len(lines)}\n")
        parts.append(f"字符数: {len(content)}\n")
        parts.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

        # 检查文件大小
        max_safe_chars = 2500  # 安全字符数，约 1200-1500 tokens

        if len(content) <= max_safe_chars:
            # 文件较小，直接返回完整内容
            parts.append("【完整文件内容】\n")
            parts.append(content)
        else:
            # 文件较大，使用智能分段检索
            parts.append(f"⚠️ 文件较大 ({len(content)} 字符)，已根据问题智能检索相关片段\n")
            parts.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

            # 检查是否是代码文件
            is_code_file = any(filename.endswith(ext) for ext in ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs'])

            if is_code_file:
                # 代码文件：提取结构
                relevant_content = self._extract_relevant_code_sections(content, filename, user_query)
            else:
                # 文本文件：分段检索
                relevant_content = self._search_relevant_chunks(content, user_query)

            parts.append("【检索到的相关内容】\n")
            parts.append(relevant_content)

            parts.append(f"\n{'='*50}\n")
            parts.append(f"提示：以上是根据您的问题检索到的最相关片段。\n")
            parts.append(f"如果需要查看其他部分，请提出更具体的问题。\n")
            parts.append(f"{'='*50}\n")

        # 添加用户问题
        if user_query and user_query != "请总结这个文件的内容":
            parts.append(f"\n{'='*50}\n")
            parts.append(f"【用户问题】\n{user_query}\n")
            parts.append(f"{'='*50}\n")

        return "\n".join(parts)

    def _split_into_chunks(self, text: str, chunk_size: int = 500, overlap: int = 50) -> list:
        """
        将文本分割成重叠的块

        Args:
            text: 要分割的文本
            chunk_size: 每块的大小（字符数）
            overlap: 块之间的重叠字符数

        Returns:
            文本块列表
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + chunk_size

            # 尽量在换行符处分割，避免截断句子
            if end < text_length:
                # 查找最近的换行符
                newline_pos = text.rfind('\n', start, end)
                if newline_pos > start + chunk_size // 2:  # 确保不会太小
                    end = newline_pos + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # 移动到下一个块，保留重叠部分
            start = end - overlap if end < text_length else text_length

        return chunks

    def _extract_keywords(self, query: str) -> list:
        """
        从用户问题中提取关键词

        Args:
            query: 用户问题

        Returns:
            关键词列表
        """
        import re

        # 移除常见的无意义词
        stop_words = {'的', '是', '在', '有', '和', '与', '或', '但', '如果', '那么',
                     '什么', '怎么', '如何', '为什么', '哪些', '这个', '那个', '这些',
                     'the', 'is', 'a', 'an', 'and', 'or', 'but', 'if', 'then', 'what',
                     'how', 'why', 'which', 'this', 'that', 'these', 'those', 'file',
                     '文件', '内容', '作用', '功能', '用于', '做什么'}

        # 提取中文和英文单词
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z0-9_]+', query.lower())

        # 过滤停用词和短词
        keywords = [w for w in words if w not in stop_words and len(w) > 1]

        return keywords

    def _calculate_chunk_relevance(self, chunk: str, keywords: list) -> float:
        """
        计算文本块与关键词的相关性得分

        Args:
            chunk: 文本块
            keywords: 关键词列表

        Returns:
            相关性得分
        """
        if not keywords:
            return 0.5  # 没有关键词时返回中等得分

        chunk_lower = chunk.lower()
        score = 0.0

        for keyword in keywords:
            keyword_lower = keyword.lower()
            # 精确匹配得高分
            count = chunk_lower.count(keyword_lower)
            score += count * 2

            # 词首匹配（如 "def" 匹配 "define"）
            if keyword_lower in chunk_lower:
                score += 1

        # 标准化得分
        return min(score / len(keywords), 10.0)

    def _search_relevant_chunks(self, content: str, query: str) -> str:
        """
        根据用户问题搜索最相关的文本片段

        Args:
            content: 文件内容
            query: 用户问题

        Returns:
            组合的相关片段
        """
        # 提取关键词
        keywords = self._extract_keywords(query)

        # 分割成块
        chunks = self._split_into_chunks(content, chunk_size=600, overlap=100)

        if not chunks:
            return content[:2500]  # 降级方案

        # 计算每个块的相关性
        chunk_scores = []
        for i, chunk in enumerate(chunks):
            score = self._calculate_chunk_relevance(chunk, keywords)
            chunk_scores.append((i, chunk, score))

        # 按相关性排序
        chunk_scores.sort(key=lambda x: x[2], reverse=True)

        # 选择最相关的几个块（控制总长度）
        selected_chunks = []
        total_chars = 0
        max_chars = 2000

        for i, chunk, score in chunk_scores:
            if total_chars + len(chunk) > max_chars:
                break
            selected_chunks.append((i, chunk, score))
            total_chars += len(chunk)

        # 按原始顺序重新排列
        selected_chunks.sort(key=lambda x: x[0])

        # 组合结果
        result_parts = []
        for i, chunk, score in selected_chunks:
            result_parts.append(f"【片段 {i+1}】(相关度: {score:.1f})\n{chunk}\n")

        return '\n'.join(result_parts) if result_parts else content[:2500]

    def _extract_relevant_code_sections(self, content: str, filename: str, query: str) -> str:
        """
        从代码文件中提取与问题相关的部分

        Args:
            content: 代码内容
            filename: 文件名
            query: 用户问题

        Returns:
            相关的代码段
        """
        lines = content.split('\n')

        # 提取关键词
        keywords = self._extract_keywords(query)

        # 根据文件扩展名确定关键字
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

        # 定义代码结构关键字
        structure_keywords = {
            '.py': ['def ', 'class ', 'import ', 'from '],
            '.js': ['function ', 'class ', 'const ', 'let ', 'var ', 'import '],
            '.ts': ['function ', 'class ', 'const ', 'let ', 'var ', 'import ', 'interface ', 'type '],
            '.jsx': ['function ', 'class ', 'const ', 'let ', 'import '],
            '.tsx': ['function ', 'class ', 'const ', 'let ', 'import ', 'interface '],
            '.java': ['public ', 'private ', 'protected ', 'class ', 'interface '],
            '.go': ['func ', 'type ', 'import ', 'package '],
            '.rs': ['fn ', 'struct ', 'enum ', 'impl ', 'use ', 'mod '],
        }

        search_patterns = structure_keywords.get(f'.{ext}', [])

        # 提取代码段（每个函数/类作为一个段）
        code_sections = []
        current_section = []
        section_start_line = 0
        indent_level = 0

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 检测新的代码段（函数/类定义）
            if any(pattern in stripped for pattern in search_patterns):
                # 保存前一个段
                if current_section:
                    section_text = '\n'.join(current_section)
                    score = self._calculate_chunk_relevance(section_text, keywords)
                    code_sections.append({
                        'start': section_start_line,
                        'end': i - 1,
                        'content': section_text,
                        'score': score
                    })

                # 开始新段
                current_section = [line]
                section_start_line = i
            elif current_section:
                # 继续当前段
                current_section.append(line)

        # 保存最后一个段
        if current_section:
            section_text = '\n'.join(current_section)
            score = self._calculate_chunk_relevance(section_text, keywords)
            code_sections.append({
                'start': section_start_line,
                'end': len(lines) - 1,
                'content': section_text,
                'score': score
            })

        # 如果没有找到结构化段，降级到行级别检索
        if not code_sections:
            return self._search_relevant_chunks(content, query)

        # 按相关性排序
        code_sections.sort(key=lambda x: x['score'], reverse=True)

        # 选择最相关的段
        selected_sections = []
        total_chars = 0
        max_chars = 2000

        for section in code_sections:
            if total_chars + len(section['content']) > max_chars:
                break
            selected_sections.append(section)
            total_chars += len(section['content'])

        # 按原始顺序重新排列
        selected_sections.sort(key=lambda x: x['start'])

        # 组合结果
        result_parts = []
        for section in selected_sections:
            result_parts.append(f"【代码段 行{section['start']+1}-{section['end']+1}】(相关度: {section['score']:.1f})")
            result_parts.append(section['content'])
            result_parts.append("")

        return '\n'.join(result_parts) if selected_sections else content[:2500]


# 导出Agent实例
text_reader_agent = TextReaderAgent()
