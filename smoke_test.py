# smoke_test.py
from jev_fn import jev, ajev, context, configure
import asyncio

# Basic call
score = jev("Is this customer angry?", context="I want my money back NOW")
print(f"angry: {score:.3f}")
assert 0.0 <= score <= 1.0, "score out of range"

# Context manager
with context("I was charged twice and need a refund urgently"):
    angry  = jev("Is the customer angry?")
    refund = jev("Are they asking for a refund?")
    urgent = jev("Is this urgent?")
print(f"angry={angry:.3f}  refund={refund:.3f}  urgent={urgent:.3f}")

# Async
async def test_async():
    score = await ajev("Is this a complaint?", context="Your service is terrible")
    print(f"async complaint: {score:.3f}")
    assert 0.0 <= score <= 1.0

asyncio.run(test_async())

# Caching — second call should not hit the network
configure(cache_enabled=True)
s1 = jev("Is this urgent?", context="help me")
s2 = jev("Is this urgent?", context="help me")
assert s1 == s2, "cache mismatch"
print("cache: OK")

print("All checks passed.")