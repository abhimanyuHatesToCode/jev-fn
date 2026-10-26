# jev-fn

A small Python wrapper that exposes TypeSafe's [Jev](https://typesafe.ai) model as a single callable function.

```python
if jev("Is this customer angry?") > 0.9:
    flag_for_human_review()
```

Jev is a "System One" typed decision model. It takes a piece of text (the *state*) and a yes/no question and returns a calibrated probability — no prompt engineering, no JSON parsing, no scoring instructions needed.

## Install

```bash
pip install jev-fn
```

`typesafe-sdk` is the only runtime dependency.

## Quickstart

Set **one** environment variable and you're done — no `configure()` call needed:

**OpenRouter** (free tier available, no waitlist — recommended for getting started):

```bash
pip install jev-fn
export OPENROUTER_API_KEY="sk-or-..."   # get one at openrouter.ai/settings/keys
```

**TypeSafe directly** (the native backend):

```bash
pip install jev-fn
export TYPESAFE_API_KEY="your-key"      # get one at console.typesafe.ai/keys
```

Then use `jev()` immediately:

```python
from jev_fn import jev

if jev("Is this customer angry?", context="I want my money back NOW") > 0.9:
    flag_for_human_review()
```

The library detects which backend to use from whichever key is present. If both are set, `OPENROUTER_API_KEY` takes priority.

## Optional configuration

```python
from jev_fn import configure

configure(model="jev-1.13.0")          # pin to a specific version
configure(cache_enabled=True)          # avoid duplicate API calls
configure(api_key="...", base_url="...") # fully explicit override
```

## Basic usage

```python
from jev_fn import jev

score = jev("Is this customer angry?", context="I have contacted support three times.")
print(score)  # e.g. 0.91
```

`jev()` always returns a float in `[0.0, 1.0]`. Use it directly in `if`, `while`, `sorted()`, or any other Python expression:

```python
if jev("Does this mention a refund?", context=message) > 0.8:
    route_to_billing()
```

## Context manager

Evaluate multiple predicates against the same text without repeating `context=`:

```python
from jev_fn import jev, context

message = "This is the third time my order arrived broken. I want a refund."

with context(message):
    angry  = jev("Is the customer angry?")
    refund = jev("Are they asking for a refund?")
    urgent = jev("Is this urgent?")
```

The same helper is available as `jev.context(...)`:

```python
with jev.context("I cannot log in and need help immediately"):
    if jev("Is this urgent?") > 0.8:
        print("Prioritize this ticket")
```

An explicit `context=` or `ctx=` argument takes precedence over the context manager. Use one or the other, not both.

## OpenRouter

OpenRouter hosts Jev under the same System One API, so you can route requests through OpenRouter instead of TypeSafe directly — useful for development, testing, or if you already have an OpenRouter account.

The simplest path is the `OPENROUTER_API_KEY` env var (see Quickstart above) — the library auto-routes. For programmatic control:

```python
from jev_fn import configure, jev

configure(
    base_url="https://openrouter.ai/api",
    api_key="sk-or-...",      # your OpenRouter key
    model="jev-latest",       # or pin to "jev-1.13.0"
)

score = jev("Is the customer angry?", context="Charged three times this week.")
```

The request shape, response shape, and the float you get back are identical — the same `jev()` call works against either backend.

Get an OpenRouter API key at [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys). Free-tier credits cover small-volume testing.

## Caching

```python
configure(cache_enabled=True, cache_ttl=300)
```

Identical `(model, query, context)` triples return the cached score without a network call. The cache is process-local and does not persist across restarts.

## Exceptions

| Exception | When raised |
|---|---|
| `ConfigurationError` | Missing API key or invalid config value |
| `ProviderError` | HTTP or network error from the TypeSafe API |
| `ParseError` | Unexpected API response shape |
| `JevError` | Base class for all library exceptions |

## Async

```python
from jev_fn import ajev, context

async def route_ticket(message: str) -> str:
    with context(message):
        angry  = await ajev("Is the customer angry?")
        refund = await ajev("Are they asking for a refund?")
        urgent = await ajev("Is this urgent?")
    ...
```

`ajev` uses `AsyncTypeSafeClient` from the SDK — safe to `await` directly on an event loop.

## How it works

Under the hood each call uses the official `typesafe-sdk`:

```python
# sync
with TypeSafeClient(api_key=..., model="jev-latest") as client:
    response = client.system_one(
        state="<your context text>",
        questions={"q": Noul(instructions="<your query>")},
    )
score = response.nouls["q"].noul   # already a float in [0.0, 1.0]

# async
async with AsyncTypeSafeClient(api_key=..., model="jev-latest") as client:
    response = await client.system_one(
        state="<your context text>",
        questions={"q": Noul(instructions="<your query>")},
    )
score = response.nouls["q"].noul
```

Jev returns a calibrated probability directly — no prompt engineering, no JSON parsing, no clamping needed.

## Limitations

- Each uncached call makes a remote API request (latency + cost).
- `jev()` is synchronous and opens a new SDK client per call. Use `ajev()` on an event loop, or `configure(cache_enabled=True)` to reduce call volume.
- Scores are calibrated probabilities from Jev, not from a general LLM. Validate thresholds on a labeled evaluation set before using them for consequential decisions.
- Avoid unbounded retry loops such as `while jev(...) < threshold`; scores may never cross the threshold.
- Context text may contain personal data. Review TypeSafe's data handling terms.

## Development

```bash
pip install -e ".[dev]"
pytest
python -m build
python -m twine check dist/*
```
