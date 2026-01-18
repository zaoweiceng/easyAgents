"""
文件存储服务
提供文件上传、下载、管理等功能
"""

import os
import uuid
import shutil
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import aiofiles
import hashlib
from fastapi import UploadFile, HTTPException
import logging

logger = logging.getLogger(__name__)


class FileRecord:
    """文件记录"""

    def __init__(
        self,
        file_id: str,
        original_filename: str,
        stored_filename: str,
        file_path: str,
        file_size: int,
        content_type: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.file_id = file_id
        self.original_filename = original_filename
        self.stored_filename = stored_filename
        self.file_path = file_path
        self.file_size = file_size
        self.content_type = content_type
        self.session_id = session_id
        self.metadata = metadata or {}
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "file_id": self.file_id,
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "file_size": self.file_size,
            "content_type": self.content_type,
            "session_id": self.session_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


class FileStorageService:
    """文件存储服务"""

    # 允许的文件类型
    ALLOWED_EXTENSIONS = {
        # 文档类
        'pdf', 'doc', 'docx', 'txt', 'md', 'rtf', 'odt',
        # 表格类
        'xls', 'xlsx', 'csv',
        # 图片类
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg',
        # 压缩包
        'zip', 'rar', '7z', 'tar', 'gz',
        # 代码文件
        'py', 'js', 'ts', 'jsx', 'tsx', 'java', 'c', 'cpp', 'h', 'go', 'rs',
        'json', 'xml', 'yaml', 'yml',
        # 数据文件
        'sql', 'db', 'sqlite',
        # 其他
        'log', 'conf', 'ini', 'env'
    }

    # 最大文件大小 (100MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024

    def __init__(self, storage_root: str = "data/files", db_service=None):
        """
        初始化文件存储服务

        Args:
            storage_root: 文件存储根目录
            db_service: 数据库服务实例 (可选)
        """
        self.storage_root = Path(storage_root)
        self._ensure_storage_dirs()
        # 内存中的文件记录缓存
        self._files: Dict[str, FileRecord] = {}
        self._db = db_service

        # 从数据库加载现有文件记录
        if self._db:
            self._load_files_from_db()

    def _ensure_storage_dirs(self):
        """确保存储目录存在"""
        self.storage_root.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        subdirs = ['uploads', 'downloads', 'temp']
        for subdir in subdirs:
            (self.storage_root / subdir).mkdir(exist_ok=True)

    def _load_files_from_db(self):
        """从数据库加载文件记录到内存"""
        try:
            records = self._db.list_file_records(limit=1000)
            for record in records:
                file_record = FileRecord(
                    file_id=record['file_id'],
                    original_filename=record['original_filename'],
                    stored_filename=record['stored_filename'],
                    file_path=record['file_path'],
                    file_size=record['file_size'],
                    content_type=record['content_type'],
                    session_id=record.get('session_id'),
                    metadata=record.get('metadata', {})
                )
                self._files[file_record.file_id] = file_record
            logger.info(f"从数据库加载了 {len(records)} 条文件记录")
        except Exception as e:
            logger.warning(f"从数据库加载文件记录失败: {e}")

    def _get_file_hash(self, content: bytes) -> str:
        """计算文件哈希值"""
        return hashlib.sha256(content).hexdigest()

    def _validate_file(self, filename: str, content_type: str, file_size: int) -> None:
        """
        验证文件

        Args:
            filename: 文件名
            content_type: 内容类型
            file_size: 文件大小

        Raises:
            ValueError: 文件验证失败
        """
        # 检查文件大小
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(
                f"文件大小超过限制 ({self.MAX_FILE_SIZE / 1024 / 1024}MB)"
            )

        # 检查文件扩展名
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"不支持的文件类型: {ext}。"
                f"支持的类型: {', '.join(sorted(self.ALLOWED_EXTENSIONS))}"
            )

    def _generate_stored_filename(self, original_filename: str) -> str:
        """
        生成存储文件名

        Args:
            original_filename: 原始文件名

        Returns:
            存储文件名 (UUID_原文件名)
        """
        ext = original_filename.rsplit('.', 1)[-1] if '.' in original_filename else ''
        unique_id = str(uuid.uuid4())
        return f"{unique_id}.{ext}" if ext else unique_id

    async def upload_file(
        self,
        file: UploadFile,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> FileRecord:
        """
        上传文件

        Args:
            file: FastAPI UploadFile对象
            session_id: 会话ID (可选)
            metadata: 额外的元数据 (可选)

        Returns:
            FileRecord: 文件记录

        Raises:
            ValueError: 文件验证失败
            HTTPException: 文件操作失败
        """
        # 读取文件内容
        content = await file.read()

        # 验证文件
        try:
            self._validate_file(file.filename, file.content_type, len(content))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # 生成存储文件名和路径
        stored_filename = self._generate_stored_filename(file.filename)
        file_path = self.storage_root / 'uploads' / stored_filename

        # 保存文件
        try:
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"文件保存失败: {str(e)}"
            )

        # 创建文件记录
        file_id = str(uuid.uuid4())
        file_record = FileRecord(
            file_id=file_id,
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_path=str(file_path),
            file_size=len(content),
            content_type=file.content_type,
            session_id=session_id,
            metadata=metadata or {}
        )

        # 存储文件记录
        self._files[file_id] = file_record

        # 保存到数据库
        if self._db:
            try:
                self._db.save_file_record(
                    file_id=file_id,
                    original_filename=file.filename,
                    stored_filename=stored_filename,
                    file_path=str(file_path),
                    file_size=len(content),
                    content_type=file.content_type,
                    session_id=session_id,
                    metadata=metadata or {}
                )
                logger.info(f"文件记录已保存到数据库: {file_id}")
            except Exception as e:
                logger.error(f"保存文件记录到数据库失败: {e}")

        return file_record

    def get_file(self, file_id: str) -> Optional[FileRecord]:
        """
        获取文件记录

        Args:
            file_id: 文件ID

        Returns:
            FileRecord or None
        """
        # 先从内存缓存查找
        if file_id in self._files:
            return self._files.get(file_id)

        # 如果内存中没有，尝试从数据库查找
        if self._db:
            try:
                record = self._db.get_file_record(file_id)
                if record:
                    file_record = FileRecord(
                        file_id=record['file_id'],
                        original_filename=record['original_filename'],
                        stored_filename=record['stored_filename'],
                        file_path=record['file_path'],
                        file_size=record['file_size'],
                        content_type=record['content_type'],
                        session_id=record.get('session_id'),
                        metadata=record.get('metadata', {})
                    )
                    # 加载到内存缓存
                    self._files[file_id] = file_record
                    return file_record
            except Exception as e:
                logger.warning(f"从数据库获取文件记录失败: {e}")

        return None

    def get_file_path(self, file_id: str) -> Optional[str]:
        """
        获取文件路径

        Args:
            file_id: 文件ID

        Returns:
            文件路径 or None
        """
        record = self.get_file(file_id)
        if record and os.path.exists(record.file_path):
            return record.file_path
        return None

    def list_files(
        self,
        session_id: Optional[str] = None,
        limit: int = 100
    ) -> List[FileRecord]:
        """
        列出文件

        Args:
            session_id: 会话ID (可选，如果提供则只返回该会话的文件)
            limit: 最大返回数量

        Returns:
            文件记录列表
        """
        files = list(self._files.values())

        if session_id:
            files = [f for f in files if f.session_id == session_id]

        # 按创建时间倒序排序
        files.sort(key=lambda x: x.created_at, reverse=True)

        return files[:limit]

    def delete_file(self, file_id: str) -> bool:
        """
        删除文件

        Args:
            file_id: 文件ID

        Returns:
            是否删除成功
        """
        record = self.get_file(file_id)
        if not record:
            return False

        # 删除物理文件
        try:
            if os.path.exists(record.file_path):
                os.remove(record.file_path)
        except Exception:
            pass

        # 删除内存记录
        if file_id in self._files:
            del self._files[file_id]

        # 删除数据库记录
        if self._db:
            try:
                self._db.delete_file_record(file_id)
            except Exception as e:
                logger.warning(f"删除数据库文件记录失败: {e}")

        return True

    async def create_download_file(
        self,
        content: str | bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        session_id: Optional[str] = None
    ) -> FileRecord:
        """
        创建下载文件

        Args:
            content: 文件内容 (字符串或字节)
            filename: 文件名
            content_type: 内容类型
            session_id: 会话ID

        Returns:
            FileRecord: 文件记录
        """
        # 转换为字节
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content

        # 生成存储文件名
        stored_filename = self._generate_stored_filename(filename)
        file_path = self.storage_root / 'downloads' / stored_filename

        # 保存文件
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content_bytes)

        # 创建文件记录
        file_id = str(uuid.uuid4())
        file_record = FileRecord(
            file_id=file_id,
            original_filename=filename,
            stored_filename=stored_filename,
            file_path=str(file_path),
            file_size=len(content_bytes),
            content_type=content_type,
            session_id=session_id,
            metadata={"source": "agent_generated"}
        )

        self._files[file_id] = file_record

        # 保存到数据库
        if self._db:
            try:
                self._db.save_file_record(
                    file_id=file_id,
                    original_filename=filename,
                    stored_filename=stored_filename,
                    file_path=str(file_path),
                    file_size=len(content_bytes),
                    content_type=content_type,
                    session_id=session_id,
                    metadata={"source": "agent_generated"}
                )
            except Exception as e:
                logger.warning(f"保存下载文件记录到数据库失败: {e}")

        return file_record

    def cleanup_session_files(self, session_id: str) -> int:
        """
        清理会话相关的临时文件

        Args:
            session_id: 会话ID

        Returns:
            清理的文件数量
        """
        files = self.list_files(session_id=session_id)
        count = 0
        for file_record in files:
            if self.delete_file(file_record.file_id):
                count += 1
        return count


# 全局单例
_file_service_instance: Optional[FileStorageService] = None


def get_file_service() -> FileStorageService:
    """获取文件存储服务单例"""
    global _file_service_instance
    if _file_service_instance is None:
        # 尝试获取数据库服务
        db_service = None
        try:
            from api.database import get_db
            db_service = get_db()
        except Exception as e:
            logger.warning(f"无法获取数据库服务，文件记录将不会持久化: {e}")

        _file_service_instance = FileStorageService(db_service=db_service)
    return _file_service_instance
