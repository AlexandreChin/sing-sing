"""Canonical critical-reading lenses for the carousel 'lens to read with' arc.

The adapt step selects 2–3 per article; Act 3 reading beats reference them by id.
Shared vocabulary that recurs across every carousel so readers build a toolkit.
"""

# Each lens carries both an emoji (newsletter, incl. email where SVG can't render)
# and an SVG line-icon of the SAME concept (carousel + any SVG surface), so the
# lens is recognizable across formats. `icon_svg` = inner paths for a
# viewBox="0 0 24 24" stroke icon (feather-style).
CANONICAL_LENSES: dict[str, dict] = {
    "sources":      {"name": "Sources",   "icon": "🔎", "question": "Qui l'affirme, et comment le sait-on ?",
                     "icon_svg": '<circle cx="10.5" cy="10.5" r="6.5"/><line x1="21" y1="21" x2="15.8" y2="15.8"/>'},
    "chiffres":     {"name": "Chiffres",   "icon": "📊", "question": "Ce chiffre, rapporté à quoi ?",
                     "icon_svg": '<line x1="6" y1="20" x2="6" y2="14"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="18" y1="20" x2="18" y2="10"/>'},
    "causalite":    {"name": "Causalité",  "icon": "🔗", "question": "Vraie cause, ou simple corrélation ?",
                     "icon_svg": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>'},
    "cadrage":      {"name": "Cadrage",    "icon": "🖼️", "question": "Qu'est-ce qu'on met en avant, et hors champ ?",
                     "icon_svg": '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/>'},
    "equilibre":    {"name": "Équilibre",  "icon": "⚖️", "question": "L'autre partie a-t-elle voix au chapitre ?",
                     "icon_svg": '<path d="M12 3v18"/><path d="M4 21h16"/><path d="M5 7h14"/><path d="M5 7l-3 6h6z"/><path d="M19 7l-3 6h6z"/>'},
    "sophismes":    {"name": "Sophismes",  "icon": "🧩", "question": "Le raisonnement tient-il logiquement ?",
                     "icon_svg": '<path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>'},
    "angles_morts": {"name": "Angles morts", "icon": "🕳️", "question": "Qu'est-ce qui manque au tableau ?",
                     "icon_svg": '<path d="M17.9 17.9A10 10 0 0 1 12 20c-7 0-11-8-11-8a18.4 18.4 0 0 1 5-5.9M9.9 4.2A9 9 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.2 3.2m-6.7-1.1a3 3 0 1 1-4.2-4.2"/><line x1="1" y1="1" x2="23" y2="23"/>'},
}

LENS_IDS = frozenset(CANONICAL_LENSES)
