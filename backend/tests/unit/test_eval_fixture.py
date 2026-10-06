"""Eval fixtures: v2 (pinned by the golden cases) loads with every adversarial record; the
latest, v3, is reproducible from the seed."""

import json

from scripts.snapshot_fixture import build

from evals.fixture import fixture_path, load_fixture

ADVERSARIAL_IDS = {
    "act_fx_inject_01",
    "act_fx_inject_02",
    "act_fx_stale_01",
    "trd_fx_stale_01",
    "inf_fx_inject_01",
}


def test_fixture_loads_with_every_adversarial_record() -> None:
    fixture = load_fixture("intelligence_v2")
    assert fixture.ids() >= ADVERSARIAL_IDS
    assert fixture.record("act_fx_inject_01") is not None
    assert fixture.record("act_missing") is None


def test_committed_fixture_matches_a_fresh_build() -> None:
    committed = json.loads(fixture_path("intelligence_v3").read_text("utf-8"))
    rebuilt = json.loads(build("intelligence_v3").model_dump_json(by_alias=True))
    assert committed == rebuilt
