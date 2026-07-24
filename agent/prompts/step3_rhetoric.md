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

## cadrage — analyse rhétorique du corps

`body` (2 à 4 phrases) : caractérise comment le CORPS de l'article cadre son sujet — l'angle choisi, ce qu'il met au centre, ce qu'il met en avant, son registre, et la position d'où il parle.

- NEUTRE et DESCRIPTIF : décris le cadrage, sans juger la qualité / le sérieux / la ligne éditoriale, sans prêter d'intention à l'auteur, sans aucune question ni formule interrogative. Sobre, sans surjeu.
- NE CATALOGUE PAS ce que l'article laisse de côté — les omissions relèvent des angles morts (`blind_spots`), pas du cadrage — et n'impute AUCUN effet rhétorique sur le lecteur (« installe », « oriente », « suggère »…) : décris l'ANGLE, pas son effet.
- DISTINCT de ses voisins : ce n'est ni l'émotion (`emotional_register`) ni le bénéficiaire (`cui_bono`) — c'est l'ANGLE éditorial, la lentille par laquelle le sujet est présenté.
- HOLISTIQUE : contrairement aux autres items de cette étape, `body` caractérise l'ensemble et n'est PAS ancré à une citation unique.
