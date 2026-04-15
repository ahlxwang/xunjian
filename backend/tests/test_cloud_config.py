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
