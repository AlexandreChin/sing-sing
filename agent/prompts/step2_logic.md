STEP 2/9 — LOGIC

Produis `analysis_fond`. Donne une vision d'ensemble de la façon dont l'auteur traite son sujet.

Style : observations neutres, pas de jugements. "Le texte s'ouvre et se referme sur la même image de X" plutôt que "l'auteur manipule le lecteur avec X".

---

## Champs

### main_claim
1 phrase, ≤ 15 mots. La thèse centrale en une ligne. Si tu dépasses 15 mots, coupe.

### premisses — 1 à 4 items
Les prémisses explicites, ou implicites mais évidentes et acceptées.
- `statement` : la prémisse en une phrase
- `quality` : si elle repose sur des données solides, ou si elle est fragilisée par : une analogie faible, un cas isolé généralisé (anecdote), un biais de confirmation, un biais de survivant, ou une simple assertion non étayée

### implicit_assumptions — 1 à 4 items
Les hypothèses implicites et discutables que l'auteur doit poser pour que son argument tienne — ce qui doit être vrai, mais n'est jamais dit ni justifié.
- `statement` : la supposition en une phrase. Arrête-toi à l'observation, ne dis pas si elle est juste ou fausse.
- `impact` : ce qui s'effondre si cette hypothèse est fausse (1 phrase)

### blind_spots — 1 à 4 items
Les points de vue importants absents ou minimisés. Couvre deux cas distincts :
1. Ce qui est totalement absent du texte
2. Ce qui est mentionné mais traité en un mot, relégué en fin de paragraphe, ou noyé dans une concession

Pour chaque item :
- `topic` : ce qui est absent ou minimisé (1 phrase courte)
- `significance` : pourquoi sa présence aurait changé la conclusion (1 phrase)

### emphasis — 1 à 3 items
Ce que l'auteur met en avant de façon disproportionnée. Formule comme une observation de proportion : "Le texte consacre X paragraphes à Y alors que Z n'est évoqué qu'une fois."

### logical_reasoning — 1 à 4 items
Les étapes inférentielles qui conduisent des prémisses à la conclusion.
- `step` : description de l'étape inférentielle
- `problem_type` :
  - `"validity"` — la conclusion ne suit pas logiquement des prémisses (saut dans le raisonnement)
  - `"soundness"` — la structure logique tient, mais la prémisse elle-même est fausse ou mal étayée
  - `null` — l'étape ne présente pas de problème
- `diagnosis` : description du problème identifié, ou `null`

Un argument peut être valide et non solide, ou solide sans être valide.

### observations — 1 à 5 items
- `aspect` (1 mot) : dimension analytique observée. Identifie la catégorie, jamais le sujet traité. "Sourçage" = correct. "Pauvreté" = incorrect.
- `summary` (1 phrase, 2 maximum, sans citation)
- `seeds` : objet pointant vers l'élément de l'étape 1 qui ancre cette observation.
  - `source` ∈ `"context"` / `"important_fact"`
  - `index` : position 0-based de l'item dans la liste source
  - `excerpt` : extrait court de l'item source pour lisibilité

### steel_man — 1 à 3 items
Les contre-arguments les plus forts à l'encontre du raisonnement de l'auteur — ce qui, si vrai, ferait s'effondrer l'argument central.
- `counterargument` : la réfutation la plus solide possible
- `seeds` : objet pointant vers le point de fragilité exploité.
  - `source` ∈ `"premisse"` / `"implicit_assumption"` / `"blind_spot"` / `"logical_reasoning"`
  - `index` : position 0-based de l'item dans la liste source
  - `excerpt` : extrait court pour lisibilité
- `alternative_conclusion` : la conclusion qui découlerait naturellement si le contre-argument tient

---

## Contrainte de cohérence

- Chaque `context` et `important_fact` de l'étape 1 doit être adressé par au moins une observation.
- Chaque observation doit être ancrée dans un `context` ou `important_fact` de l'étape 1.
