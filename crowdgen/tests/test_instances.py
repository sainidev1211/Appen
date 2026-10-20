"""Tests for crowdgen instances loader and validation."""

from pathlib import Path

import pytest

from crowdgen_automation.instances import InstanceConfig, load_instances


def test_instance_validation_success() -> None:
    """Verify valid instance passes validation."""
    inst = InstanceConfig(
        email="user@example.com",
        password="secret_password",
        task_url="https://app.crowdgen.com/dashboard",
    )
    inst.validate()
    cfg = inst.to_settings()
    assert cfg.max_tasks == 50
    assert cfg.aht_min_wait_sec == 30
    assert cfg.target_remaining_sec == 0


def test_instance_validation_empty_credentials() -> None:
    """Verify empty credentials raise ValueError."""
    with pytest.raises(ValueError, match="email and password"):
        InstanceConfig(email="", password="pwd").validate()

    with pytest.raises(ValueError, match="email and password"):
        InstanceConfig(email="user@test.com", password="").validate()


def test_instance_validation_invalid_url() -> None:
    """Verify invalid task_url raises ValueError."""
    with pytest.raises(ValueError, match="Invalid task_url"):
        InstanceConfig(email="u@test.com", password="pwd", task_url="invalid").validate()


def test_load_instances(tmp_path: Path) -> None:
    """Verify dynamic instance file loading."""
    inst_file = tmp_path / "instances.py"
    inst_file.write_text(
        "from crowdgen_automation.instances import InstanceConfig\n"
        "INSTANCES = [InstanceConfig(email='a@b.com', password='p')]\n"
    )
    loaded = load_instances(str(inst_file))
    assert len(loaded) == 1
    assert loaded[0].email == "a@b.com"
