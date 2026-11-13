"""The seven prisms of the TROIS REGARDS carousel: a name, a one-line definition (what the prism looks at, in French)
and a lens icon (inner markup of a viewBox="0 0 24 24" stroke icon, no colour)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Prism:
    name: str
    definition: str
    icon_svg: str


PRISMS: dict[str, Prism] = {
    "economique": Prism(
        "Économique", "les incitations, la rareté, les prix, les coûts et qui les supporte",
        '<line x1="12" y1="3" x2="12" y2="20"/><line x1="5" y1="7" x2="19" y2="7"/>'
        '<path d="M5 7l-3 7a3 3 0 0 0 6 0z"/><path d="M19 7l-3 7a3 3 0 0 0 6 0z"/><line x1="8" y1="20" x2="16" y2="20"/>'),
    "sociologique": Prism(
        "Sociologique", "les normes, les statuts, les groupes, les liens sociaux, qui est concerné",
        '<circle cx="8" cy="7" r="3"/><path d="M2 20v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/>'
        '<circle cx="17" cy="8" r="2.5"/><path d="M17 14a4 4 0 0 1 5 4v2"/>'),
    "juridique": Prism(
        "Juridique", "le cadre légal, les droits, les institutions, l'application des règles",
        '<path d="M3 9l9-6 9 6z"/><line x1="6" y1="11" x2="6" y2="18"/><line x1="12" y1="11" x2="12" y2="18"/>'
        '<line x1="18" y1="11" x2="18" y2="18"/><line x1="3" y1="21" x2="21" y2="21"/>'),
    "historique": Prism(
        "Historique", "les précédents et la trajectoire longue — des repères datés seulement, jamais un chiffre de tendance",
        '<line x1="6" y1="3" x2="18" y2="3"/><line x1="6" y1="21" x2="18" y2="21"/>'
        '<path d="M7 3v4l5 5-5 5v4"/><path d="M17 3v4l-5 5 5 5v4"/>'),
    "politique": Prism(
        "Politique", "les rapports de force, les mandats, les coalitions, le calendrier électoral",
        '<rect x="9" y="4" width="6" height="16"/><rect x="2" y="12" width="7" height="8"/>'
        '<rect x="15" y="9" width="7" height="11"/>'),
    "ecologique": Prism(
        "Écologique", "les ressources, les milieux, les contraintes physiques",
        '<path d="M5 19C5 9 11 4 20 4c0 9-5 15-15 15z"/><path d="M5 19c2-5 5-8 9-10"/>'),
    "technologique": Prism(
        "Technologique", "les outils, les infrastructures, les données, l'automatisation",
        '<rect x="6" y="6" width="12" height="12" rx="1"/><rect x="9.5" y="9.5" width="5" height="5"/>'
        '<path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>'),
}

PRISM_IDS: tuple[str, ...] = tuple(PRISMS)


def catalogue_text() -> str:
    """The block the prompts receive: one line per prism, id, name, definition."""
    return "\n".join(f"- {pid} ({p.name}) : {p.definition}" for pid, p in PRISMS.items())
