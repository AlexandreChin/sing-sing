"""Step files on disk: one `<n>_<name>.json` per step with its stamp beside it
(`.sha256`), the stale/legacy moves, and the append-only choice log. File I/O
only — no model calls."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from agent.carousel_steps.steps import STEP_BY_NAME, STEPS, Option, Step, StepName
from models.instagram_carousel_presentation import ThesisFrame

_LEGACY = ("1_axis", "2_selection", "3_writing")


class StepFile(BaseModel):
    step: StepName
    thesis_frame: ThesisFrame | None = None
    options: list[Option] = Field(default_factory=list)
    rejected: list[Option] = Field(default_factory=list)
    recommended: list[str] = Field(default_factory=list)
    picked: list[str] = Field(default_factory=list)   # empty = awaiting a choice
    fragment: dict = Field(default_factory=dict)
    remarks: list[str] = Field(default_factory=list)


def digest(*parts: str) -> str:
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()


def step_path(steps_dir: Path, step: Step) -> Path:
    return steps_dir / f"{step.n}_{step.name}.json"


def _stamp_path(steps_dir: Path, step: Step) -> Path:
    return step_path(steps_dir, step).with_suffix(".sha256")


def load(steps_dir: Path, step: Step) -> tuple[StepFile | None, str]:
    path = step_path(steps_dir, step)
    if not path.exists():
        return None, ""
    stamp = _stamp_path(steps_dir, step)
    return (
        StepFile.model_validate_json(path.read_text(encoding="utf-8")),
        stamp.read_text().strip() if stamp.exists() else "",
    )


def save(steps_dir: Path, sf: StepFile, stamp: str) -> None:
    step = STEP_BY_NAME[sf.step]
    steps_dir.mkdir(parents=True, exist_ok=True)
    step_path(steps_dir, step).write_text(sf.model_dump_json(indent=2), encoding="utf-8")
    _stamp_path(steps_dir, step).write_text(stamp)


def _move_to(steps_dir: Path, folder: str, paths: list[Path]) -> bool:
    """Move the existing `paths` into `steps_dir/folder`; True when any moved."""
    dest = steps_dir / folder
    moved = False
    for p in paths:
        if p.exists():
            dest.mkdir(parents=True, exist_ok=True)
            p.replace(dest / p.name)
            moved = True
    return moved


def retire(steps_dir: Path, step: Step, stamp: str) -> None:
    _move_to(steps_dir, f"stale_{(stamp or 'unstamped')[:8]}",
             [step_path(steps_dir, step), _stamp_path(steps_dir, step)])


def retire_legacy(steps_dir: Path) -> bool:
    return _move_to(steps_dir, "stale_legacy",
             [steps_dir / f"{n}{ext}" for n in _LEGACY for ext in (".json", ".sha256")])


def stamp_for(base: str, fragments_before: list[dict]) -> str:
    """A step's stamp depends on the earlier steps' fragments only."""
    return digest(base, *(json.dumps(f, sort_keys=True, ensure_ascii=False) for f in fragments_before))


def restamp_after(steps_dir: Path, step: Step, base: str) -> None:
    """Rewrite the stamp of every later step that has a file, from the saved
    fragments before it. Stops at the first missing file; never touches `step`'s."""
    fragments: list[dict] = []
    for s in STEPS:
        if s.n > step.n:
            if not step_path(steps_dir, s).exists():
                return
            _stamp_path(steps_dir, s).write_text(stamp_for(base, fragments))
        sf, _ = load(steps_dir, s)
        if sf is None:
            return
        fragments.append(sf.fragment)


def log_choice(fmt_dir: Path, event: dict) -> None:
    fmt_dir.mkdir(parents=True, exist_ok=True)
    line = {"ts": datetime.now().isoformat(timespec="seconds"), **event}
    with (fmt_dir / "choices.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
