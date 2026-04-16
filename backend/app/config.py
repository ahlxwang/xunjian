from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    redis_url: str
    jwt_secret: SecretStr
    jwt_expire_minutes: int = 480
    prometheus_url: str = "http://localhost:9090"

    # Aliyun
    aliyun_access_key_id: str | None = None
    aliyun_access_key_secret: SecretStr | None = None
    aliyun_region: str = "cn-hangzhou"

    # Tencent
    tencent_secret_id: str | None = None
    tencent_secret_key: SecretStr | None = None
    tencent_region: str = "ap-guangzhou"

    # Huawei
    huawei_access_key: str | None = None
    huawei_secret_key: SecretStr | None = None
    huawei_region: str = "cn-north-4"

    # K8s
    k8s_config_mode: Literal["kubeconfig", "incluster"] = "kubeconfig"
    k8s_kubeconfig_path: str | None = None


settings = Settings()
