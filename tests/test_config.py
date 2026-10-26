import pytest

from jev_fn.config import configure, get_config
from jev_fn.exceptions import ConfigurationError


def test_configure_model_and_timeout():
    original = get_config()
    try:
        configure(model="jev-1.13.0", timeout=15.0)
        assert get_config().model == "jev-1.13.0"
        assert get_config().timeout == 15.0
    finally:
        configure(**original.__dict__)


def test_configure_rejects_unknown_key():
    with pytest.raises(ConfigurationError):
        configure(not_a_setting=True)


def test_configure_rejects_empty_model():
    with pytest.raises(ConfigurationError):
        configure(model="")


def test_configure_rejects_negative_timeout():
    with pytest.raises(ConfigurationError):
        configure(timeout=-1.0)


def test_configure_rejects_zero_cache_ttl():
    with pytest.raises(ConfigurationError):
        configure(cache_ttl=0)


def test_default_model_is_jev_latest():
    original = get_config()
    try:
        configure(model="jev-latest")
        assert get_config().model == "jev-latest"
    finally:
        configure(**original.__dict__)


def test_configure_base_url():
    original = get_config()
    try:
        configure(base_url="https://openrouter.ai/api")
        assert get_config().base_url == "https://openrouter.ai/api"
        configure(base_url=None)
        assert get_config().base_url is None
    finally:
        configure(**original.__dict__)


def test_configure_rejects_empty_base_url():
    with pytest.raises(ConfigurationError):
        configure(base_url="")
