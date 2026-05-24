"""应用配置"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # 遗留 OpenAI 变量（Phase 2），Phase 3 以 Qwen 为主
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    # 通义千问 / DashScope（OpenAI 兼容模式）
    qwen_api_key: str = ""
    dashscope_api_key: str = ""
    qwen_model: str = "qwen-turbo"
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # Coze Integration（OpenAI 兼容，狼人杀 AI 默认）
    coze_integration_api_key: str = ""
    coze_integration_base_url: str = "https://integration.coze.cn/api/v3"
    coze_integration_model: str = "doubao-seed-2-0-mini-260215"

    # 火山方舟（Doubao / Seed 系列，备用）
    ark_api_key: str = ""
    ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    ark_model: str = "doubao-seed-2-0-mini-260215"

    # 本地 vLLM / 任意 OpenAI 兼容端点（优先于云厂商 Key）
    llm_base_url: str = ""
    llm_api_key: str = ""

    llm_timeout_seconds: float = 25.0
    llm_speech_max_chars: int = 350
    llm_speech_min_chars: int = 80
    # 夜晚 AI：本地加权选策略 + 单次决策 LLM（默认开启，显著缩短夜晚）
    llm_night_fast_mode: bool = True
    llm_night_max_tokens: int = 128
    # 白天投票：本地选策略 + 单次决策 LLM（与夜晚分开配置）
    llm_vote_fast_mode: bool = True
    llm_vote_max_tokens: int = 128
    # 投票前信念链：规则基线 + 单次 LLM 刷新
    llm_belief_fast_mode: bool = True
    llm_belief_max_tokens: int = 256
    llm_memory_compress_max_tokens: int = 256

    game_speech_max_seconds: int = 60
    game_night_action_timeout_seconds: float = 30.0
    game_max_duration_seconds: int = 1800
    cors_origins: str = "http://localhost:5173"
    replays_dir: str = ""
    serve_frontend_dist: bool = True

    @field_validator(
        "coze_integration_api_key",
        "ark_api_key",
        "qwen_api_key",
        "dashscope_api_key",
        "openai_api_key",
        "llm_api_key",
        "llm_base_url",
        "coze_integration_base_url",
        "ark_base_url",
        mode="before",
    )
    @classmethod
    def _strip_strings(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def has_llm_configured(self) -> bool:
        if self.llm_base_url.strip():
            return True
        return bool(
            self.coze_integration_api_key
            or self.ark_api_key
            or self.dashscope_api_key
            or self.qwen_api_key
            or self.openai_api_key
        )

    @property
    def has_qwen_key(self) -> bool:
        """兼容旧名：任一 LLM 来源已配置即启用 Pipeline。"""
        return self.has_llm_configured


settings = Settings()
