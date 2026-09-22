import json
from typing import cast

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.repositories.base import Document
from app.pipelines import runner
from app.pipelines.runner import selected_pipelines


def test_selected_pipelines_are_deterministic() -> None:
    assert selected_pipelines() == ("competitor_activity", "influencers", "trends")
    assert selected_pipelines("trends") == ("trends",)
    with pytest.raises(ValueError, match="unsupported pipeline"):
        selected_pipelines("unknown")


@pytest.mark.asyncio
async def test_dispatch_runs_only_selected_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    order: list[str] = []

    async def fake_indexes(_database: AsyncDatabase[Document]) -> None:
        return None

    async def fake_trends(*_args: object, **_kwargs: object) -> dict[str, int]:
        order.append("trends")
        return {"inserted": 1}

    async def fail_competitors(*_args: object, **_kwargs: object) -> dict[str, int]:
        raise AssertionError("competitor pipeline should not run")

    async def fail_influencers(*_args: object, **_kwargs: object) -> dict[str, int]:
        raise AssertionError("influencer pipeline should not run")

    monkeypatch.setattr(runner, "ensure_indexes", fake_indexes)
    monkeypatch.setattr(runner, "run_trend_pipeline", fake_trends)
    monkeypatch.setattr(runner, "run_competitor_activity_pipeline", fail_competitors)
    monkeypatch.setattr(runner, "run_influencer_pipeline", fail_influencers)

    result = await runner.run_pipelines(
        owned_database=cast(AsyncDatabase[Document], object()),
        competitorscope_database=cast(AsyncDatabase[Document], object()),
        dct_database=cast(AsyncDatabase[Document], object()),
        pace_database=cast(AsyncDatabase[Document], object()),
        only="trends",
    )

    assert order == ["trends"]
    assert result == {"trends": {"inserted": 1}}


def test_cli_rejects_unknown_pipeline_as_json(capsys: pytest.CaptureFixture[str]) -> None:
    from scripts.run_pipelines import parse_args

    with pytest.raises(SystemExit) as raised:
        parse_args(["--only", "unknown"])

    assert raised.value.code == 2
    error = json.loads(capsys.readouterr().err)
    assert error["error"]["code"] == "VALIDATION_ERROR"


def test_cli_parses_valid_selection() -> None:
    from scripts.run_pipelines import parse_args

    assert parse_args(["--only", "influencers"]).only == "influencers"
