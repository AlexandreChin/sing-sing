"""Canonical critical-reading lenses for the carousel 'lens to read with' arc.

The adapt step selects 2–3 per article; Act 3 reading beats reference them by id.
Shared vocabulary that recurs across every carousel so readers build a toolkit.
"""

CANONICAL_LENSES: dict[str, dict] = {
    "sources":      {"name": "Sources",             "icon": "🔎", "question": "Qui l'affirme, et comment le sait-on ?"},
    "chiffres":     {"name": "Chiffres",             "icon": "📊", "question": "Ce chiffre, rapporté à quoi ?"},
    "causalite":    {"name": "Causalité",           "icon": "🔗", "question": "Vraie cause, ou simple corrélation ?"},
    "cadrage":      {"name": "Cadrage",             "icon": "🖼️", "question": "Qu'est-ce qu'on met en avant, et hors champ ?"},
    "equilibre":    {"name": "Équilibre",           "icon": "⚖️", "question": "L'autre partie a-t-elle voix au chapitre ?"},
    "sophismes":    {"name": "Sophismes",           "icon": "🧩", "question": "Le raisonnement tient-il logiquement ?"},
    "angles_morts": {"name": "Angles morts",        "icon": "🕳️", "question": "Qu'est-ce qui manque au tableau ?"},
}

LENS_IDS = frozenset(CANONICAL_LENSES)
