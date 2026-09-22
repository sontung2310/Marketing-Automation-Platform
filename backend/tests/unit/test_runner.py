import json
from types import SimpleNamespace
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


class _FakeClientGetter:
    def __init__(self) -> None:
        self.closed = False
        self.cleared = False
        self.client = object()

    def __call__(self) -> object:
        return self.client

    def cache_info(self) -> SimpleNamespace:
        return SimpleNamespace(currsize=1)

    def cache_clear(self) -> None:
        self.cleared = True


class _FakeClient:
    def __init__(self) -> None:
        self.closed = False

    def __getitem__(self, _name: str) -> object:
        return object()

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_cli_run_writes_success_json_and_closes_client(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from scripts import run_pipelines as cli

    fake_client = _FakeClient()
    getter = _FakeClientGetter()
    getter.client = fake_client
    monkeypatch.setattr(cli.db, "get_client", getter)
    monkeypatch.setattr(
        cli,
        "get_settings",
        lambda: SimpleNamespace(
            mongodb_database="owned",
            competitorscope_database="competitors",
            dct_database="dct",
            pace_database="pace",
        ),
    )

    async def fake_run_pipelines(**kwargs: object) -> dict[str, object]:
        assert kwargs["only"] == "trends"
        return {"trends": {"inserted": 1}}

    monkeypatch.setattr(cli, "run_pipelines", fake_run_pipelines)

    result = await cli.run(["--only", "trends"])

    assert result == 0
    assert json.loads(capsys.readouterr().out) == {
        "pipelines": {"trends": {"inserted": 1}},
        "status": "ok",
    }
    assert fake_client.closed is True
    assert getter.cleared is True


@pytest.mark.asyncio
async def test_cli_run_writes_upstream_error_json_and_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from scripts import run_pipelines as cli

    fake_client = _FakeClient()
    getter = _FakeClientGetter()
    getter.client = fake_client
    monkeypatch.setattr(cli.db, "get_client", getter)
    monkeypatch.setattr(
        cli,
        "get_settings",
        lambda: SimpleNamespace(
            mongodb_database="owned",
            competitorscope_database="competitors",
            dct_database="dct",
            pace_database="pace",
        ),
    )

    async def fail_run_pipelines(**_kwargs: object) -> dict[str, object]:
        raise RuntimeError("source unavailable")

    monkeypatch.setattr(cli, "run_pipelines", fail_run_pipelines)

    result = await cli.run([])

    assert result == 1
    assert json.loads(capsys.readouterr().err) == {
        "error": {"code": "UPSTREAM_UNAVAILABLE", "message": "source unavailable"},
        "status": "error",
    }
    assert fake_client.closed is True
    assert getter.cleared is True
