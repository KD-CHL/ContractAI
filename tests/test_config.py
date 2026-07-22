from __future__ import annotations

from typing import Any

from contract_guard.config import Settings, clear_settings_cache, get_settings


def test_security_and_packaged_knowledge_defaults() -> None:
    settings = Settings.from_env({})

    assert settings.auth_required is True
    assert settings.legacy_tenant_headers_enabled is False
    assert settings.database_path is not None
    assert settings.knowledge_path.endswith("demo_knowledge_base.json")


def test_local_env_file_loads_without_overriding_process_environment(
    tmp_path: Any, monkeypatch: Any
) -> None:
    env_file = tmp_path / "test.env"
    env_file.write_text(
        "APP_MODE=hybrid\nOPENAI_MODEL=file-model\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CONTRACT_GUARD_ENV_FILE", str(env_file))
    monkeypatch.setenv("OPENAI_MODEL", "process-model")
    monkeypatch.delenv("APP_MODE", raising=False)
    clear_settings_cache()

    settings = get_settings()

    assert settings.app_mode == "hybrid"
    assert settings.llm_enabled is True
    assert settings.openai_model == "process-model"
    clear_settings_cache()
