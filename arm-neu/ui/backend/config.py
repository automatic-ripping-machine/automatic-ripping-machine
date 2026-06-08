from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    themes_path: str = "/data/themes"
    image_cache_path: str = "/data/cache/images"
    arm_url: str = "http://localhost:8080"
    transcoder_url: str = "http://localhost:5000"
    transcoder_api_key: str = ""
    transcoder_enabled: bool = True
    transcoder_webhook_secret: str = ""
    port: int = 8888
    demo_mode: bool = False

    model_config = {"env_prefix": "ARM_UI_"}


settings = Settings()
