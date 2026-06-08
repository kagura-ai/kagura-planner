"""Stable JSON envelope for kagura-agent consumption.

Contract (schema_version 1):
    {schema_version, status, plan_doc_path, memory_id, edges[], summary}

Agents read this JSON only — never scrape the rich table. Mirrors the
engineer<->reviewer JSON discipline.
"""
from __future__ import annotations

import json

from .result import PlanReport

SCHEMA_VERSION = 1


def to_envelope(report: PlanReport) -> str:
    return json.dumps(
        {
            "schema_version": SCHEMA_VERSION,
            "status": report.status.value,
            "plan_doc_path": report.plan_doc_path,
            "memory_id": report.memory_id,
            "edges": report.edges,
            "summary": f"plan: {report.idea}",
        },
        ensure_ascii=False,
    )
