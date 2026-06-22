STEP 3/9 — RHETORIC

Produis `analysis_forme` : identifie comment l'article agit sur le lecteur — émotionnellement et structurellement.

Ces items devront être ancrés dans le texte à l'étape suivante (Probe) — anticipe.

---

## emotional_register — 1 à 2 items

Identifie les émotions que l'article est conçu pour produire. Pas un jugement — une description.

- `emotion` : le sentiment dominant ciblé. Désigne le sentiment visé, jamais le sujet qui le provoque. "indignation" = correct. "inégalités" = incorrect.
- `how` : 1 phrase — la technique qui produit cette émotion (mots chargés, images, structure, contraste, accumulation de détails…)
- `effect` : 1 phrase — ce que l'émotion prépare le lecteur à conclure ou à faire
- `seeds` : objet pointant vers l'élément de l'étape 1 qui ancre cet item.
  - `source` ∈ `"context"` / `"important_fact"`
  - `index` : position 0-based de l'item dans la liste source
  - `excerpt` : extrait court pour lisibilité

---

## cui_bono — 1 à 2 items

Identifie qui bénéficie du cadrage adopté. Pas une lecture complotiste — une observation structurelle. Formule de façon neutre.

- `beneficiary` : qui bénéficie (acteur politique, institution, camp, argument)
- `explanation` : 1 à 2 phrases — pourquoi ce cadrage les sert, et comment
- `seeds` : même structure que pour `emotional_register` (source, index, excerpt)

---

## cadrage — analyse rhétorique du titre

`title_analysis` (1 à 3 items) : analyse post-lecture du titre — ce qu'il promet, comment il cadre le contenu, l'écart éventuel avec le corps de l'article.

Pour chaque item :
- `label` (1–2 mots) : identifie le procédé rhétorique ou technique de cadrage, jamais le contenu traité. "Présupposé" = correct. "Hausse des taux" = incorrect — c'est le sujet, pas le procédé. Exemples : "Attribution", "Présupposé", "Vocabulaire", "Omission", "Cadrage", "Ellipse".
- `observation` (1 phrase analytique, ≤ 20 mots) : le constat ancré dans le texte. Ex. : "Le titre désigne un responsable sans nommer les victimes."

N'en produis que si le titre contient un vrai signal de cadrage — pas de remarque générique.
