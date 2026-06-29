"""LLM-based simplification pass for a ArticleFullAnalysis JSON.

Shortens all text fields to make slides more readable on Instagram,
while preserving the schema, verbatim quotes, and numeric/enum fields.
"""
import json
import re
import subprocess
from pathlib import Path

import anthropic

from config import MODEL
from models.full_analysis import ArticleFullAnalysis

client = anthropic.Anthropic()

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "simplify.md").read_text(encoding="utf-8")


async def simplify_carousel(json_path: Path, no_api: bool = False) -> ArticleFullAnalysis:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    schema = ArticleFullAnalysis.model_json_schema()
    user_content = "Voici le JSON à simplifier :\n\n" + json.dumps(data, ensure_ascii=False, indent=2)

    if no_api:
        prompt = (
            f"{_SYSTEM_PROMPT}\n\n"
            "---\n\n"
            f"{user_content}\n\n"
            "---\n\n"
            "Réponds UNIQUEMENT avec un objet JSON valide correspondant exactement à ce schéma :\n"
            f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
            "N'ajoute aucun texte avant ni après le JSON. Pas de balises markdown. Pas d'explication."
        )
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            raise RuntimeError(f"claude CLI failed:\n{result.stderr}")
        text = result.stdout.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if match:
            text = match.group(1).strip()
        return ArticleFullAnalysis.model_validate(json.loads(text))

    with client.messages.stream(
        model=MODEL,
        max_tokens=8192,
        thinking={"type": "adaptive"},
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": schema,
            }
        },
    ) as stream:
        response = stream.get_final_message()

    text = next(b.text for b in response.content if b.type == "text")
    return ArticleFullAnalysis.model_validate(json.loads(text))
