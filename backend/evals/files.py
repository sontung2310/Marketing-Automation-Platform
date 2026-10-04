"""JSONL files of Pydantic models: the harness's one reader and writer."""

from collections.abc import Iterable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

ModelT = TypeVar("ModelT", bound=BaseModel)


def write_jsonl(path: Path, items: Iterable[BaseModel]) -> None:
    path.write_text("".join(item.model_dump_json() + "\n" for item in items), encoding="utf-8")


def read_jsonl(
    path: Path, model: type[ModelT], error: type[ValueError] = ValueError
) -> list[ModelT]:
    """Validated lines (blank ones skipped); a bad line raises `error` naming file and line."""
    if not path.is_file():
        raise error(f"{path} does not exist")
    items: list[ModelT] = []
    for number, line in enumerate(path.read_text("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            items.append(model.model_validate_json(line))
        except ValidationError as exc:
            raise error(f"{path.name}:{number}: {exc}") from exc
    return items
