"""Extended memory tests — covers recall, explore, feedback, _mcp_url,
_recall_filters, persistent loop, close idempotency, resolve_memory_client."""
from __future__ import annotations

import pytest

from kagura_planner.plan import memory as memory_module
from kagura_planner.plan.memory import KaguraCloudClient, _mcp_url, _recall_filters


class _FakeSDK:
    """Async SDK stub matching kagura_memory.KaguraClient interface."""

    def __init__(self):
        self.calls: list = []
        self.closed = False

    async def recall(self, context_id, query="", k=5, filters=None, **kw):
        self.calls.append(("recall", context_id, query, k, filters))
        return {
            "results": [
                {"memory_id": "m1", "summary": "past plan A"},
                {"summary": "no-id row"},          # no memory_id → dropped from recall_detailed
                {"memory_id": "m2"},                # no summary → dropped from both
            ]
        }

    async def remember(self, context_id, summary, content, type="note", **kw):
        self.calls.append(("remember", context_id, summary, type))
        return {"memory_id": "mem-new"}

    async def feedback(self, context_id, memory_id, helpful, *, query=None, note=None):
        self.calls.append(("feedback", context_id, memory_id, helpful))
        return {"ok": True}

    async def explore(self, context_id, memory_id, depth=2, min_weight=0.05):
        self.calls.append(("explore", context_id, memory_id, depth))
        return {
            "nodes": [
                {"memory_id": "n1", "summary": "related A"},
                {"summary": "no-id node"},          # dropped
                {"memory_id": "n2"},                # no summary → dropped
            ]
        }

    async def create_edge(self, context_id, src, dst, relation, **kw):
        self.calls.append(("create_edge", context_id, src, dst, relation))
        return {"ok": True}

    async def close(self):
        self.closed = True


class _ExploreResultsSDK:
    """explore() returns 'results' key instead of 'nodes'."""

    async def explore(self, context_id, memory_id, depth=2, min_weight=0.05):
        return {
            "results": [
                {"memory_id": "r1", "summary": "result node"},
            ]
        }


# ---------------------------------------------------------------------------
# recall (plain, summary-only)
# ---------------------------------------------------------------------------


def test_recall_returns_summary_strings():
    sdk = _FakeSDK()
    out = KaguraCloudClient(sdk).recall("ctx", "plan for: add X", k=3)
    # m1 has summary + no-id row has summary → both returned; m2 has no summary → dropped
    assert out == ["past plan A", "no-id row"]


def test_recall_applies_trust_filter():
    sdk = _FakeSDK()
    KaguraCloudClient(sdk).recall("ctx", "q")
    _, _, _, _, filters = sdk.calls[-1]
    assert filters["trust_tier"] == "trusted"


def test_recall_with_tags_and_importance():
    seen = {}

    class _Sdk:
        async def recall(self, ctx, query="", k=5, filters=None, **kw):
            seen["filters"] = filters
            return {"results": []}

    KaguraCloudClient(_Sdk()).recall("ctx", "q", tags=["security"], min_importance=0.8)
    assert seen["filters"]["trust_tier"] == "trusted"
    assert seen["filters"]["tags"] == ["security"]
    assert seen["filters"]["importance"] == {"gte": 0.8}


def test_recall_no_filters_is_trust_only():
    seen = {}

    class _Sdk:
        async def recall(self, ctx, query="", k=5, filters=None, **kw):
            seen["filters"] = filters
            return {"results": []}

    KaguraCloudClient(_Sdk()).recall("ctx", "q")
    assert seen["filters"] == {"trust_tier": "trusted"}


# ---------------------------------------------------------------------------
# explore passthrough and parse
# ---------------------------------------------------------------------------


def test_explore_returns_pairs_and_drops_incomplete():
    sdk = _FakeSDK()
    out = KaguraCloudClient(sdk).explore("ctx", "m1", depth=2)
    assert out == [("n1", "related A")]
    assert sdk.calls[-1] == ("explore", "ctx", "m1", 2)


def test_explore_falls_back_to_results_key():
    out = KaguraCloudClient(_ExploreResultsSDK()).explore("ctx", "seed", depth=1)
    assert out == [("r1", "result node")]


def test_explore_empty_response():
    class _EmptySDK:
        async def explore(self, *a, **k):
            return {}

    out = KaguraCloudClient(_EmptySDK()).explore("ctx", "m1")
    assert out == []


# ---------------------------------------------------------------------------
# feedback passthrough
# ---------------------------------------------------------------------------


def test_feedback_calls_sdk_with_helpful_true_no_weight():
    """The wrapper must call the real SDK signature feedback(context_id,
    memory_id, helpful, ...) with helpful=True (reinforcement = "this memory
    was helpful") and must NOT pass a `weight` kwarg (the real SDK rejects it).
    """
    seen = {}

    class _Sdk:
        # Real SDK signature: feedback(context_id, memory_id, helpful, *, query, note).
        async def feedback(self, context_id, memory_id, helpful, *, query=None, note=None):
            seen.update(
                context_id=context_id, memory_id=memory_id, helpful=helpful,
                query=query, note=note,
            )
            return {"ok": True}

    # weight is accepted on the interface but ignored in the body.
    KaguraCloudClient(_Sdk()).feedback("ctx", "m1", weight=2.0)
    assert seen == {
        "context_id": "ctx", "memory_id": "m1", "helpful": True,
        "query": None, "note": None,
    }


def test_feedback_ignores_weight_and_passes_helpful_true():
    """Even with no weight given, the SDK is called positionally with helpful=True."""
    seen = {}

    class _Sdk:
        async def feedback(self, context_id, memory_id, helpful, *, query=None, note=None):
            seen.update(args=(context_id, memory_id, helpful))

    KaguraCloudClient(_Sdk()).feedback("ctx", "m1")
    assert seen["args"] == ("ctx", "m1", True)


# ---------------------------------------------------------------------------
# _mcp_url idempotency
# ---------------------------------------------------------------------------


def test_mcp_url_appends_mcp():
    assert _mcp_url("https://memory.example.com") == "https://memory.example.com/mcp"


def test_mcp_url_trailing_slash():
    assert _mcp_url("https://memory.example.com/") == "https://memory.example.com/mcp"


def test_mcp_url_already_has_mcp():
    assert _mcp_url("https://memory.example.com/mcp") == "https://memory.example.com/mcp"


def test_mcp_url_mcp_with_trailing_slash():
    assert _mcp_url("https://memory.example.com/mcp/") == "https://memory.example.com/mcp"


def test_mcp_url_empty_string():
    assert _mcp_url("") == ""


# ---------------------------------------------------------------------------
# _recall_filters
# ---------------------------------------------------------------------------


def test_recall_filters_base():
    f = _recall_filters(None, 0.0)
    assert f == {"trust_tier": "trusted"}


def test_recall_filters_with_tags():
    f = _recall_filters(["plan", "security"], 0.0)
    assert f["tags"] == ["plan", "security"]
    assert "importance" not in f


def test_recall_filters_with_importance():
    f = _recall_filters(None, 0.5)
    assert f["importance"] == {"gte": 0.5}
    assert "tags" not in f


def test_recall_filters_tags_and_importance():
    f = _recall_filters(["a"], 0.3)
    assert f["tags"] == ["a"]
    assert f["importance"] == {"gte": 0.3}
    assert f["trust_tier"] == "trusted"


# ---------------------------------------------------------------------------
# persistent loop — two sequential calls must work on one loop
# ---------------------------------------------------------------------------


def test_two_sequential_calls_on_one_loop():
    sdk = _FakeSDK()
    c = KaguraCloudClient(sdk)
    out1 = c.recall("ctx", "q1")
    out2 = c.recall("ctx", "q2")
    assert out1 == ["past plan A", "no-id row"]
    assert out2 == ["past plan A", "no-id row"]
    assert len([x for x in sdk.calls if x[0] == "recall"]) == 2


# ---------------------------------------------------------------------------
# close() closes sdk and loop; is idempotent
# ---------------------------------------------------------------------------


def test_close_closes_sdk_and_loop():
    sdk = _FakeSDK()
    c = KaguraCloudClient(sdk)
    c.recall("ctx", "q")
    c.close()
    assert sdk.closed is True
    assert c._loop.is_closed()


def test_close_is_idempotent():
    sdk = _FakeSDK()
    c = KaguraCloudClient(sdk)
    c.close()
    c.close()  # must not raise
    assert c._loop.is_closed()


def test_close_without_sdk_close_method():
    class _NoClose:
        async def recall(self, *a, **k):
            return {"results": []}

    c = KaguraCloudClient(_NoClose())
    c.recall("ctx", "q")
    c.close()   # SDK has no close() → still closes loop, no raise
    c.close()   # idempotent
    assert c._loop.is_closed()


# ---------------------------------------------------------------------------
# resolve_memory_client
# ---------------------------------------------------------------------------


def test_resolve_local_raises_not_implemented():
    from kagura_planner.config import Config
    cfg = Config(
        profile="t",
        memory_cloud_url="https://x.example.com",
        workspace_id="w",
        context_id="c",
        memory_backend="local",
    )
    with pytest.raises(NotImplementedError):
        memory_module.resolve_memory_client(cfg)


def test_resolve_cloud_returns_kagura_cloud_client(monkeypatch):
    from kagura_planner.config import Config
    sentinel = object()
    monkeypatch.setattr(
        memory_module.KaguraCloudClient,
        "from_config",
        classmethod(lambda cls, cfg: sentinel),
    )
    cfg = Config(
        profile="t",
        memory_cloud_url="https://x.example.com",
        workspace_id="w",
        context_id="c",
        memory_backend="cloud",
    )
    result = memory_module.resolve_memory_client(cfg)
    assert result is sentinel
