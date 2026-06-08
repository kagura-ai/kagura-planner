from kagura_planner.plan.memory import KaguraCloudClient, MemoryClient


class _FakeSDK:
    def __init__(self):
        self.calls = []

    async def recall(self, context_id, query="", k=5, filters=None, **kw):
        self.calls.append(("recall", context_id, query, k, filters))
        return {"results": [
            {"memory_id": "m1", "summary": "past plan A"},
            {"summary": "no-id row"},
        ]}

    async def remember(self, context_id, summary, content, type="note", **kw):
        self.calls.append(("remember", context_id, summary, type))
        return {"memory_id": "mem-new"}

    async def create_edge(self, context_id, src, dst, relation, **kw):
        self.calls.append(("create_edge", context_id, src, dst, relation))
        return {"ok": True}

    async def close(self):
        pass


def test_recall_detailed_returns_pairs_and_trust_filter():
    sdk = _FakeSDK()
    out = KaguraCloudClient(sdk).recall_detailed("ctx", "q", k=3)
    assert out == [("m1", "past plan A")]
    assert sdk.calls[-1] == ("recall", "ctx", "q", 3, {"trust_tier": "trusted"})


def test_remember_returns_id():
    sdk = _FakeSDK()
    mid = KaguraCloudClient(sdk).remember("ctx", summary="s", content="c", type="decision")
    assert mid == "mem-new"


def test_create_edge_passthrough():
    sdk = _FakeSDK()
    KaguraCloudClient(sdk).create_edge("ctx", "mem-new", "m1", "refines")
    assert sdk.calls[-1] == ("create_edge", "ctx", "mem-new", "m1", "refines")


def test_satisfies_protocol():
    assert isinstance(KaguraCloudClient(_FakeSDK()), MemoryClient)
