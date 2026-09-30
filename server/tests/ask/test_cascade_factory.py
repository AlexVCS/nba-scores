"""The production cascade and the release evaluation share one factory and frozen settings."""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

import pytest

from server.ask.config import FROZEN_CASCADE, AskConfig
from server.ask.interpreters.factory import build_cascade, build_policy, cascade_drift, frozen_config
from server.ask.interpreters.tiered import CASCADE_POLICY_THRESHOLDS
from server.ask.pipeline import AskPipeline

ENV = ("ASK_ENABLED", "ASK_DEV", "ASK_PARSER_MODEL", "ASK_REASONING_EFFORT", "ASK_FALLBACK_MODEL",
       "ASK_DEADLINE_SECONDS", "LAYA_BASE_URL", "ASK_JEV_MODEL", "ASK_JEV_ACCEPT_MIN", "ASK_VETO_MIN")
FAKE_OPENAI = "sk-test-openai-never-logged"
FAKE_TYPESAFE = "ts-test-typesafe-never-logged"


@pytest.fixture
def clean_env(monkeypatch):
    for name in ENV:
        monkeypatch.delenv(name, raising=False)


def test_defaults_are_the_frozen_cascade(clean_env):
    assert FROZEN_CASCADE == {
        "jev_model": "jev-1.13.0", "jev_accept_min": 0.85,
        "primary_model": "gpt-6-luna", "primary_reasoning_effort": "low",
        "veto_min": 0.5, "deadline_seconds": 20.0, "laya_base_url": None, "fallback_model": None,
    }
    assert cascade_drift(AskConfig()) == []
    config = AskConfig.from_env()
    assert cascade_drift(config) == []
    assert (config.enabled, config.dev) == (False, False)


def test_production_builds_jev_then_luna_with_frozen_settings(clean_env):
    adapter = build_cascade(frozen_config(api_key=FAKE_OPENAI, typesafe_api_key=FAKE_TYPESAFE))
    jev, luna = adapter.tiers
    assert (jev.name, jev.adapter.model, jev.accept_min) == ("jev", "jev-1.13.0", 0.85)
    assert (luna.name, luna.adapter.model, luna.accept_min) == ("luna", "gpt-6-luna", None)
    assert luna.adapter.config.reasoning_effort == "low"
    assert luna.adapter.config.timeout_s == 20.0
    assert adapter.veto_min == 0.5
    assert build_policy().thresholds == CASCADE_POLICY_THRESHOLDS
    assert build_policy().fallback is None


def test_production_never_builds_laya(clean_env, monkeypatch):
    monkeypatch.setenv("LAYA_BASE_URL", "http://127.0.0.1:8080/v1/systemone")
    config = AskConfig.from_env()
    config = AskConfig(**{**config.__dict__, "api_key": FAKE_OPENAI, "typesafe_api_key": FAKE_TYPESAFE})
    assert [t.name for t in build_cascade(config).tiers] == ["jev", "luna"]
    monkeypatch.setenv("ASK_DEV", "1")
    dev = AskConfig.from_env()
    assert dev.dev is True
    dev = AskConfig(**{**dev.__dict__, "api_key": FAKE_OPENAI, "typesafe_api_key": FAKE_TYPESAFE})
    assert [t.name for t in build_cascade(dev).tiers] == ["laya", "jev", "luna"]
    assert [t.name for t in build_cascade(dev, include_laya=False).tiers] == ["jev", "luna"]


def test_missing_jev_key_falls_through_to_luna_without_logging_keys(clean_env, caplog):
    caplog.set_level(logging.WARNING, logger="server.ask.interpreters.factory")
    adapter = build_cascade(frozen_config(api_key=FAKE_OPENAI))
    assert [t.name for t in adapter.tiers] == ["luna"]
    assert "without Jev" in caplog.text
    assert FAKE_OPENAI not in caplog.text
    with pytest.raises(RuntimeError) as error:
        build_cascade(frozen_config())
    assert "KEY" in str(error.value)


def test_drift_from_the_frozen_cascade_is_logged(caplog):
    caplog.set_level(logging.WARNING, logger="server.ask.interpreters.factory")
    build_cascade(frozen_config(api_key=FAKE_OPENAI, typesafe_api_key=FAKE_TYPESAFE, jev_accept_min=0.7))
    assert "jev_accept_min" in caplog.text
    assert FAKE_TYPESAFE not in caplog.text


def test_frozen_config_rejects_unknown_settings():
    with pytest.raises(TypeError):
        frozen_config(jev_threshold=0.9)


def test_pipeline_lazily_builds_the_shared_cascade(tmp_path):
    pipeline = AskPipeline(frozen_config(enabled=True, state_dir=tmp_path, api_key=FAKE_OPENAI,
                                         typesafe_api_key=FAKE_TYPESAFE))
    adapter = pipeline._adapter()
    assert [t.name for t in adapter.tiers] == ["jev", "luna"]
    assert pipeline.policy.thresholds == CASCADE_POLICY_THRESHOLDS


def test_release_runner_uses_the_shared_factory_and_settings():
    repo = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location("release_runner_factory", repo / "scripts/ask/release.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.CONFIG == FROZEN_CASCADE
    assert module.build_cascade is build_cascade
    assert module.build_policy is build_policy
