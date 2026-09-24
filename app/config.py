from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    demo_mode: str = "simulation"

    vllm_endpoint: str = "http://localhost:8080/v1"
    vllm_model: str = "meta-llama/Llama-3.3-70B-Instruct"
    vllm_api_key: str = ""

    mcp_server_url: str = "http://localhost:9000"

    mlflow_tracking_uri: str = "http://localhost:5000"
    mlflow_experiment_name: str = "zero-trust-agents"

    openshift_ai_endpoint: str = ""
    openshift_ai_token: str = ""

    @property
    def is_simulation(self) -> bool:
        return self.demo_mode == "simulation"


settings = Settings()
