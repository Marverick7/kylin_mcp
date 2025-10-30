"""
配置管理模块
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """应用配置"""
    
    # 服务器配置
    HOST: str = "127.0.0.1"
    PORT: int = 8765
    
    # CORS配置
    CORS_ORIGINS: list = ["http://localhost:*", "http://127.0.0.1:*"]
    
    # API密钥
    DEEPSEEK_API_KEY: Optional[str] = None
    QWEN_API_KEY: Optional[str] = None
    
    # API端点
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    QWEN_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    # 数据存储路径
    DATA_DIR: str = "./data"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 全局配置实例
settings = Settings()

# 确保数据目录存在
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.DATA_DIR, "conversations"), exist_ok=True)
os.makedirs(os.path.join(settings.DATA_DIR, "mcp_servers"), exist_ok=True)

