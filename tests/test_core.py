"""Tests for jev() and ajev() — SDK calls are mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jev_fn import ajev, configure, context, jev
from jev_fn.cache import clear_cache
from jev_fn.config import get_config
from jev_fn.exceptions import ConfigurationError, ParseError, ProviderError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sdk_response(noul: float) -> MagicMock:
    """Minimal stand-in for a TypeSafe SDK response with one noul answer."""
    noul_answer = MagicMock()
    noul_answer.noul = noul
    response = MagicMock()
    response.nouls = {"q": noul_answer}
    return response


def _patch_sync(noul: float = 0.75):
    """Patch TypeSafeClient so system_one() returns a fixed score."""
    mock_client = MagicMock()
    mock_client.system_one.return_value = _sdk_response(noul)
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_cls = MagicMock(return_value=mock_client)
    return patch("jev_fn.core.TypeSafeClient", mock_cls), mock_client


def _patch_async(noul: float = 0.75):
    """Patch AsyncTypeSafeClient so system_one() returns a fixed score."""
    mock_client = AsyncMock()
    mock_client.system_one = AsyncMock(return_value=_sdk_response(noul))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_cls = MagicMock(return_value=mock_client)
    return patch("jev_fn.core.AsyncTypeSafeClient", mock_cls), mock_client


# ---------------------------------------------------------------------------
# Sync — jev()
# ---------------------------------------------------------------------------

def test_jev_returns_score(monkeypatch):
    original = get_config()
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    patch_ctx, mock_client = _patch_sync(0.91)
    with patch_ctx:
        try:
            configure(cache_enabled=False)
            score = jev("Is this customer angry?", context="I want a refund NOW")
            assert score == pytest.approx(0.91)
        finally:
            configure(**original.__dict__)
            clear_cache()


def test_jev_context_manager_sets_state(monkeypatch):
    original = get_config()
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    patch_ctx, mock_client = _patch_sync(0.75)
    with patch_ctx:
        try:
            configure(cache_enabled=False)
            with context("message from context manager"):
                jev("Is this urgent?")
                jev("Is this billing?", context="explicit overrides")

            calls = mock_client.system_one.call_args_list
            assert calls[0].kwargs["state"] == "message from context manager"
            assert calls[1].kwargs["state"] == "explicit overrides"
        finally:
            configure(**original.__dict__)
            clear_cache()


def test_jev_cache_avoids_duplicate_calls(monkeypatch):
    original = get_config()
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    patch_ctx, mock_client = _patch_sync(0.75)
    with patch_ctx:
        try:
            configure(cache_enabled=True, cache_ttl=60)
            clear_cache()
            assert jev("Is it urgent?", context="help") == pytest.approx(0.75)
            assert jev("Is it urgent?", context="help") == pytest.approx(0.75)
            assert mock_client.system_one.call_count == 1
        finally:
            configure(**original.__dict__)
            clear_cache()


def test_jev_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    original = get_config()
    try:
        configure(api_key=None)
        with pytest.raises(ConfigurationError, match="API key"):
            jev("Is this urgent?", context="hello")
    finally:
        configure(**original.__dict__)


def test_jev_sdk_exception_raises_provider_error(monkeypatch):
    original = get_config()
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_client.system_one.side_effect = RuntimeError("connection refused")
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    with patch("jev_fn.core.TypeSafeClient", MagicMock(return_value=mock_client)):
        try:
            configure(cache_enabled=False)
            with pytest.raises(ProviderError):
                jev("Is this urgent?", context="hello")
        finally:
            configure(**original.__dict__)
            clear_cache()


def test_jev_bad_response_raises_parse_error(monkeypatch):
    """SDK returning a response without .nouls should raise ParseError, not KeyError."""
    original = get_config()
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    bad_response = MagicMock()
    bad_response.nouls = {}   # "q" key missing
    mock_client = MagicMock()
    mock_client.system_one.return_value = bad_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    with patch("jev_fn.core.TypeSafeClient", MagicMock(return_value=mock_client)):
        try:
            configure(cache_enabled=False)
            with pytest.raises(ParseError):
                jev("Is this urgent?", context="hello")
        finally:
            configure(**original.__dict__)
            clear_cache()


def test_jev_openrouter_key_auto_routes(monkeypatch):
    """OPENROUTER_API_KEY should auto-set base_url to OpenRouter."""
    from jev_fn.core import _OPENROUTER_BASE_URL
    original = get_config()
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    patch_ctx, mock_client = _patch_sync(0.77)
    with patch_ctx as mock_cls:
        try:
            configure(api_key=None, base_url=None, cache_enabled=False)
            score = jev("Is this urgent?", context="help")
            assert score == pytest.approx(0.77)
            # Verify the client was constructed with OpenRouter's base URL
            _, kwargs = mock_cls.call_args
            assert kwargs.get("base_url") == _OPENROUTER_BASE_URL
        finally:
            configure(**original.__dict__)
            clear_cache()


def test_jev_ctx_alias(monkeypatch):
    original = get_config()
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    patch_ctx, _ = _patch_sync(0.6)
    with patch_ctx:
        try:
            configure(cache_enabled=False)
            assert jev("Is this a question?", ctx="some text") == pytest.approx(0.6)
        finally:
            configure(**original.__dict__)
            clear_cache()


# ---------------------------------------------------------------------------
# Async — ajev()
# ---------------------------------------------------------------------------

async def test_ajev_returns_score(monkeypatch):
    original = get_config()
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    patch_ctx, mock_client = _patch_async(0.88)
    with patch_ctx:
        try:
            configure(cache_enabled=False)
            score = await ajev("Is this billing?", context="charge me twice")
            assert score == pytest.approx(0.88)
        finally:
            configure(**original.__dict__)
            clear_cache()


async def test_ajev_context_manager_sets_state(monkeypatch):
    original = get_config()
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    patch_ctx, mock_client = _patch_async(0.75)
    with patch_ctx:
        try:
            configure(cache_enabled=False)
            with context("shared message"):
                await ajev("Is this urgent?")
                await ajev("Is this angry?", context="explicit overrides")

            calls = mock_client.system_one.call_args_list
            assert calls[0].kwargs["state"] == "shared message"
            assert calls[1].kwargs["state"] == "explicit overrides"
        finally:
            configure(**original.__dict__)
            clear_cache()


async def test_ajev_cache_avoids_duplicate_calls(monkeypatch):
    original = get_config()
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    patch_ctx, mock_client = _patch_async(0.5)
    with patch_ctx:
        try:
            configure(cache_enabled=True, cache_ttl=60)
            clear_cache()
            assert await ajev("Is it urgent?", context="help") == pytest.approx(0.5)
            assert await ajev("Is it urgent?", context="help") == pytest.approx(0.5)
            assert mock_client.system_one.call_count == 1
        finally:
            configure(**original.__dict__)
            clear_cache()


async def test_ajev_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    original = get_config()
    try:
        configure(api_key=None)
        with pytest.raises(ConfigurationError, match="API key"):
            await ajev("Is this urgent?", context="hello")
    finally:
        configure(**original.__dict__)
