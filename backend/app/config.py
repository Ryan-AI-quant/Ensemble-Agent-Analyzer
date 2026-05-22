"""
配置管理 - 支持多种后端服务配置
"""

import os
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class BackendType(str, Enum):
    """后端服务类型"""
    OPENCLAW = "openclaw"
    HERMES = "hermes"
    LOCAL = "local"


class OpenClawConfig(BaseModel):
    """OpenClaw 配置"""
    api_url: str = "http://localhost:8080"
    api_key: Optional[str] = None
    model: str = "default"
    max_tokens: int = 2000
    temperature: float = 0.7


class HermesConfig(BaseModel):
    """Hermes (Ollama) 配置"""
    api_url: str = "http://localhost:11434"  # Ollama 默认端口
    model: str = "llama3"
    api_key: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.7
    # API 格式: "openai" (兼容格式) 或 "ollama" (原生格式)
    api_format: str = "ollama"


class LocalConfig(BaseModel):
    """本地分析配置"""
    enable: bool = True
    confidence: float = 0.75


class SystemConfig(BaseModel):
    """系统配置"""
    backend_type: BackendType = BackendType.HERMES
    openclaw: OpenClawConfig = OpenClawConfig()
    hermes: HermesConfig = HermesConfig()
    local: LocalConfig = LocalConfig()

    @classmethod
    def from_env(cls) -> "SystemConfig":
        """从环境变量加载配置"""
        backend_type_str = os.getenv("BACKEND_TYPE", "hermes").lower()
        
        # 验证后端类型
        try:
            backend_type = BackendType(backend_type_str)
        except ValueError:
            print(f"⚠️ 警告: 无效的后端类型 '{backend_type_str}'，使用默认值 'hermes'")
            backend_type = BackendType.HERMES

        config = cls(
            backend_type=backend_type,
            openclaw=OpenClawConfig(
                api_url=os.getenv("OPENCLAW_API_URL", "http://localhost:18789"),
                api_key=os.getenv("OPENCLAW_API_KEY"),
                model=os.getenv("OPENCLAW_MODEL", "gpt-4"),
            ),
            hermes=HermesConfig(
                api_url=os.getenv("HERMES_API_URL", "http://localhost:11434"),
                api_key=os.getenv("HERMES_API_KEY"),
                model=os.getenv("HERMES_MODEL", "llama3"),
                api_format=os.getenv("HERMES_API_FORMAT", "ollama"),
            )
        )
        
        # 打印配置信息用于调试
        print(f"[Config] 后端类型: {backend_type.value}")
        print(f"[Config] Hermes API URL: {config.hermes.api_url}")
        print(f"[Config] Hermes Model: {config.hermes.model}")
        print(f"[Config] Hermes API Format: {config.hermes.api_format}")
        print(f"[Config] OpenClaw API URL: {config.openclaw.api_url}")
        print(f"[Config] OpenClaw Model: {config.openclaw.model}")

        return config


def _create_config() -> SystemConfig:
    """创建配置实例（延迟加载）"""
    return SystemConfig.from_env()


# 全局配置实例（延迟初始化）
_config_instance: SystemConfig = None


def get_config() -> SystemConfig:
    """获取当前配置"""
    global _config_instance
    if _config_instance is None:
        _config_instance = _create_config()
    return _config_instance


def reload_config() -> SystemConfig:
    """重新加载配置（用于动态更新）"""
    global _config_instance
    _config_instance = _create_config()
    print("[Config] 配置已重新加载")
    return _config_instance


def update_backend_type(backend_type: BackendType) -> None:
    """更新后端类型"""
    get_config().backend_type = backend_type


def update_llm_model(model_name: str) -> None:
    """更新LLM模型名称（同时更新OpenClaw和Hermes的模型配置）"""
    if model_name:
        cfg = get_config()
        cfg.openclaw.model = model_name
        cfg.hermes.model = model_name


def get_backend_display_name() -> str:
    """获取后端显示名称"""
    names = {
        BackendType.OPENCLAW: "OpenClaw",
        BackendType.HERMES: "Hermes (Ollama)",
        BackendType.LOCAL: "本地分析"
    }
    return names.get(get_config().backend_type, "未知")
