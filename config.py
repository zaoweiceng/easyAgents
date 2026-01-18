"""
配置管理模块

支持从环境变量、.env文件和默认值加载配置
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""

    # LLM服务配置
    LLM_BASE_URL: str = Field(
        default="http://127.0.0.1:9999/v1",
        description="LLM服务地址"
    )

    LLM_API_KEY: str = Field(
        default="None",
        description="LLM API密钥"
    )

    LLM_MODEL_NAME: str = Field(
        default="openai/gpt-oss-20b",
        description="LLM模型名称"
    )

    # LLM参数配置
    LLM_TEMPERATURE: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="LLM温度参数（控制随机性，0-2）"
    )

    LLM_TOP_P: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="LLM top_p参数（核采样，0-1）"
    )

    LLM_TOP_K: int = Field(
        default=40,
        ge=1,
        description="LLM top_k参数（保留前k个概率最高的词，默认40）"
    )

    LLM_STREAM_CHUNK_SIZE: int = Field(
        default=10,
        ge=1,
        description="流式输出时每N个delta记录一次日志（控制日志详细程度）"
    )

    # Agent配置
    PLUGIN_DIR: str = Field(
        default="plugin",
        description="Agent插件目录"
    )

    START_AGENT_NAME: str = Field(
        default="entrance_agent",
        description="起始Agent名称"
    )

    END_AGENT_NAME: str = Field(
        default="general_agent",
        description="结束Agent名称"
    )

    MAX_RETRIES: int = Field(
        default=3,
        description="最大重试次数"
    )

    # MCP配置
    MCP_ENABLED: bool = Field(
        default=False,
        description="是否启用MCP支持"
    )

    MCP_CONFIG_FILE: Optional[str] = Field(
        default=None,
        description="MCP配置文件路径（JSON格式）"
    )

    # MCP服务器配置列表
    # 注意：这是一个复杂的配置，建议通过配置文件设置
    # 这里提供基本的单个服务器配置
    MCP_SERVER_NAME: Optional[str] = Field(
        default=None,
        description="MCP服务器名称"
    )

    MCP_SERVER_COMMAND: Optional[str] = Field(
        default=None,
        description="MCP服务器启动命令"
    )

    MCP_SERVER_URL: Optional[str] = Field(
        default=None,
        description="MCP服务器URL（SSE模式）"
    )

    # 日志配置
    LOG_LEVEL: str = Field(
        default="INFO",
        description="日志级别（DEBUG, INFO, WARNING, ERROR）"
    )

    LOG_FILE: Optional[str] = Field(
        default=None,
        description="日志文件路径"
    )

    # 应用配置
    APP_NAME: str = Field(
        default="easyAgent",
        description="应用名称"
    )

    APP_VERSION: str = Field(
        default="0.1.0",
        description="应用版本"
    )

    DEBUG: bool = Field(
        default=False,
        description="调试模式"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


class AppConfig:
    """应用配置管理器"""

    def __init__(self, env_file: Optional[str] = None):
        """
        初始化配置

        Args:
            env_file: .env文件路径
        """
        self.env_file = env_file or ".env"
        self.settings = self._load_settings()

    def _load_settings(self) -> Settings:
        """加载配置"""
        # 尝试从.env文件加载
        if os.path.exists(self.env_file):
            return Settings(_env_file=self.env_file)
        else:
            # 使用默认配置
            return Settings()

    def get_mcp_configs(self) -> list:
        """
        获取MCP配置列表

        Returns:
            list: MCP服务器配置列表
        """
        # 如果配置了MCP配置文件，从文件加载
        if self.settings.MCP_CONFIG_FILE and os.path.exists(self.settings.MCP_CONFIG_FILE):
            import json
            with open(self.settings.MCP_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get("mcp_servers", [])

        # 如果启用了MCP但配置了单个服务器，创建配置
        if self.settings.MCP_ENABLED:
            config = {}

            if self.settings.MCP_SERVER_URL:
                # SSE模式
                config["url"] = self.settings.MCP_SERVER_URL
            elif self.settings.MCP_SERVER_COMMAND:
                # STDIO模式
                config["command"] = self.settings.MCP_SERVER_COMMAND
                config["args"] = []  # 可以从环境变量读取
                config["env"] = {}

            if config:
                config["name"] = self.settings.MCP_SERVER_NAME or "default_mcp"
                config["health_check"] = True
                return [config]

        return []

    def get_llm_config(self) -> dict:
        """
        获取LLM配置

        Returns:
            dict: LLM配置字典
        """
        return {
            "base_url": self.settings.LLM_BASE_URL,
            "api_key": self.settings.LLM_API_KEY,
            "model_name": self.settings.LLM_MODEL_NAME,
            "temperature": self.settings.LLM_TEMPERATURE,
            "top_p": self.settings.LLM_TOP_P,
            "top_k": self.settings.LLM_TOP_K,
            "stream_chunk_size": self.settings.LLM_STREAM_CHUNK_SIZE
        }

    def get_agent_config(self) -> dict:
        """
        获取Agent配置

        Returns:
            dict: Agent配置字典
        """
        return {
            "plugin_src": self.settings.PLUGIN_DIR,
            "start_agent_name": self.settings.START_AGENT_NAME,
            "end_agent_name": self.settings.END_AGENT_NAME,
            "max_trys": self.settings.MAX_RETRIES
        }

    def get_log_config(self) -> dict:
        """
        获取日志配置

        Returns:
            dict: 日志配置字典
        """
        return {
            "level": self.settings.LOG_LEVEL,
            "filename": self.settings.LOG_FILE,
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }

    def setup_logging(self):
        """设置日志系统"""
        import logging
        import logging.handlers

        log_config = self.get_log_config()
        logger = logging.getLogger(self.settings.APP_NAME)
        logger.setLevel(getattr(logging, log_config["level"]))

        # 清除现有handlers
        logger.handlers.clear()

        # 控制台handler
        console_handler = logging.StreamHandler()

        # 自定义Formatter以支持毫秒格式（3位，使用逗号分隔）
        class MillisecondFormatter(logging.Formatter):
            def formatTime(self, record, datefmt=None):
                import datetime
                ct = datetime.datetime.fromtimestamp(record.created)
                # 生成时间部分: YYYY-MM-DD HH:MM:SS,mmm
                s = ct.strftime("%Y-%m-%d %H:%M:%S")
                # 添加毫秒（3位，使用逗号分隔）
                milliseconds = ct.microsecond // 1000  # 转换为毫秒
                s = f"{s},{milliseconds:03d}"
                return s

        formatter = MillisecondFormatter(log_config["format"])
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 文件handler（如果配置了）
        if log_config["filename"]:
            # 确保日志目录存在
            log_dir = os.path.dirname(log_config["filename"])
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            # 使用轮转文件handler，使用相同的formatter
            file_handler = logging.handlers.RotatingFileHandler(
                log_config["filename"],
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    @property
    def llm_base_url(self) -> str:
        return self.settings.LLM_BASE_URL

    @property
    def llm_api_key(self) -> str:
        return self.settings.LLM_API_KEY

    @property
    def llm_model_name(self) -> str:
        return self.settings.LLM_MODEL_NAME

    @property
    def plugin_dir(self) -> str:
        return self.settings.PLUGIN_DIR

    @property
    def mcp_enabled(self) -> bool:
        return self.settings.MCP_ENABLED

    def __repr__(self) -> str:
        """配置信息字符串表示"""
        return f"""AppConfig(
  LLM配置:
    - Base URL: {self.settings.LLM_BASE_URL}
    - Model: {self.settings.LLM_MODEL_NAME}
    - API Key: {'*' * 10 if self.settings.LLM_API_KEY != 'None' else 'Not Set'}

  Agent配置:
    - 插件目录: {self.settings.PLUGIN_DIR}
    - 起始Agent: {self.settings.START_AGENT_NAME}
    - 结束Agent: {self.settings.END_AGENT_NAME}
    - 最大重试: {self.settings.MAX_RETRIES}

  MCP配置:
    - 启用: {self.settings.MCP_ENABLED}
    - 配置文件: {self.settings.MCP_CONFIG_FILE or 'Not Set'}

  日志配置:
    - 级别: {self.settings.LOG_LEVEL}
    - 文件: {self.settings.LOG_FILE or 'Console'}
)"""


# 全局配置实例
config = None


def get_config(env_file: Optional[str] = None) -> AppConfig:
    """
    获取配置实例（单例模式）

    Args:
        env_file: .env文件路径

    Returns:
        AppConfig: 配置实例
    """
    global config
    if config is None:
        config = AppConfig(env_file)
    return config


def reload_config(env_file: Optional[str] = None):
    """
    重新加载配置

    Args:
        env_file: .env文件路径
    """
    global config
    config = AppConfig(env_file)
    return config
