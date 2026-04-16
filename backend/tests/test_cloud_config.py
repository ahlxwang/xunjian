from pydantic import SecretStr

from app.config import Settings


def test_cloud_config_fields_present():
    settings = Settings.model_construct(
        database_url="postgresql+asyncpg://u:p@localhost:5432/db",
        redis_url="redis://localhost:6379/0",
        jwt_secret="x" * 32,
    )
    assert hasattr(settings, "aliyun_region")
    assert hasattr(settings, "tencent_region")
    assert hasattr(settings, "huawei_region")
    assert hasattr(settings, "k8s_config_mode")


def test_cloud_config_defaults():
    settings = Settings.model_construct(
        database_url="postgresql+asyncpg://u:p@localhost:5432/db",
        redis_url="redis://localhost:6379/0",
        jwt_secret="x" * 32,
    )
    assert settings.aliyun_region == "cn-hangzhou"
    assert settings.tencent_region == "ap-guangzhou"
    assert settings.huawei_region == "cn-north-4"
    assert settings.k8s_config_mode == "kubeconfig"


def test_cloud_config_credentials_default_none():
    settings = Settings.model_construct(
        database_url="postgresql+asyncpg://u:p@localhost:5432/db",
        redis_url="redis://localhost:6379/0",
        jwt_secret="x" * 32,
    )
    assert settings.aliyun_access_key_id is None
    assert settings.aliyun_access_key_secret is None
    assert settings.tencent_secret_id is None
    assert settings.tencent_secret_key is None
    assert settings.huawei_access_key is None
    assert settings.huawei_secret_key is None
    assert settings.k8s_kubeconfig_path is None


def test_jwt_secret_is_secret_str():
    settings = Settings.model_construct(
        database_url="postgresql+asyncpg://u:p@localhost:5432/db",
        redis_url="redis://localhost:6379/0",
        jwt_secret=SecretStr("x" * 32),
    )
    assert isinstance(settings.jwt_secret, SecretStr)
