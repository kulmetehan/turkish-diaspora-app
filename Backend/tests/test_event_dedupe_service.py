from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from services import event_dedupe_service
from services.event_dedupe_service import CandidateContext


def _ctx(
    *,
    candidate_id: int,
    title: str,
    city_key: str = "rotterdam",
    start_offset_hours: int = 0,
    location_text: str | None = "Community Hall",
) -> CandidateContext:
    base_start = datetime(2025, 1, 1, 12, tzinfo=timezone.utc)
    return CandidateContext(
        id=candidate_id,
        event_source_id=1,
        source_key=f"source_{candidate_id}",
        city_key=city_key,
        title=title,
        description="Desc",
        location_text=location_text,
        start_time_utc=base_start + timedelta(hours=start_offset_hours),
        end_time_utc=None,
    )


@pytest.mark.asyncio
async def test_run_dedupe_marks_duplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = _ctx(candidate_id=1, title="Community Meetup")
    other = _ctx(candidate_id=2, title="Community Meetup")

    async def fake_fetch_candidate_context(candidate_id: int):
        return ctx

    async def fake_fetch_potential_duplicates(context: CandidateContext):
        return [other]

    recorded = {}

    async def fake_mark_duplicate(candidate_id: int, canonical_id: int, score: float):
        recorded["duplicate"] = (candidate_id, canonical_id, score)

    async def fake_mark_canonical(candidate_id: int):
        recorded["canonical"] = candidate_id

    monkeypatch.setattr(event_dedupe_service, "_fetch_candidate_context", fake_fetch_candidate_context)
    monkeypatch.setattr(event_dedupe_service, "_fetch_potential_duplicates", fake_fetch_potential_duplicates)
    monkeypatch.setattr(event_dedupe_service, "_mark_duplicate", fake_mark_duplicate)
    monkeypatch.setattr(event_dedupe_service, "_mark_canonical", fake_mark_canonical)

    result = await event_dedupe_service.run_dedupe(1)

    assert result.duplicate_of_id == 2
    assert "duplicate" in recorded
    assert recorded["duplicate"][0] == 1
    assert recorded["duplicate"][1] == 2
    assert recorded["duplicate"][2] >= event_dedupe_service.DUPLICATE_SCORE_THRESHOLD
    assert "canonical" not in recorded


@pytest.mark.asyncio
async def test_run_dedupe_keeps_canonical(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = _ctx(candidate_id=5, title="Community Meetup")
    other = _ctx(candidate_id=6, title="Completely Different Title", location_text="Different Venue")

    async def fake_fetch_candidate_context(candidate_id: int):
        return ctx

    async def fake_fetch_potential_duplicates(context: CandidateContext):
        return [other]

    recorded = {"canonical": None}

    async def fake_mark_duplicate(candidate_id: int, canonical_id: int, score: float):
        recorded["duplicate"] = (candidate_id, canonical_id, score)

    async def fake_mark_canonical(candidate_id: int):
        recorded["canonical"] = candidate_id

    monkeypatch.setattr(event_dedupe_service, "_fetch_candidate_context", fake_fetch_candidate_context)
    monkeypatch.setattr(event_dedupe_service, "_fetch_potential_duplicates", fake_fetch_potential_duplicates)
    monkeypatch.setattr(event_dedupe_service, "_mark_duplicate", fake_mark_duplicate)
    monkeypatch.setattr(event_dedupe_service, "_mark_canonical", fake_mark_canonical)

    result = await event_dedupe_service.run_dedupe(5)

    assert result.duplicate_of_id is None
    assert recorded["canonical"] == 5
    assert "duplicate" not in recorded




