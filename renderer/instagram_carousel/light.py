"""The light carousel: the optimized deck's templates in their light variant —
larger type, the bird on each moment's question, no lede on slide 2."""
from pathlib import Path

from .optimized import generate_html_from_json as _generate, render_from_json as _render


def generate_html_from_json(json_path: Path, out_dir: Path) -> list[Path]:
    return _generate(json_path, out_dir, light=True)


def render_from_json(json_path: Path, out_dir: Path, pdf: bool = False) -> list[Path]:
    return _render(json_path, out_dir, pdf, light=True)
