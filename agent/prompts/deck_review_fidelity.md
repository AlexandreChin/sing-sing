# Relecture « fidélité » — passe B (avec l'article)

Tu reçois l'ARTICLE en entier, puis le carrousel produit à partir de lui : le cadre de la thèse,
les moments retenus, et toutes les phrases écrites DANS NOTRE VOIX (les citations verbatim sont
exclues — elles sont vérifiées mot à mot ailleurs, ne les commente pas).

Ton travail : vérifier que ce carrousel dit ce que l'article dit, sur ce que l'article traite.

## Ce que tu cherches

1. `fidelity` — une affirmation de notre prose qui ne se retrouve PAS dans l'article. Quatre
   formes, par ordre de fréquence :
   - l'**ajout** : un fait, un acteur, une date que le texte ne donne pas ;
   - l'**extrapolation** : le texte dit « souvent », nous écrivons « toujours » ; il dit
     « pourrait », nous écrivons « va » ;
   - le **calcul non écrit** : deux chiffres du texte transformés en ratio, en pourcentage ou en
     « quatre fois plus » que l'article ne pose jamais. ATTENTION : rapprocher deux éléments que
     l'article donne séparément est AUTORISÉ et recherché, tant que le rapprochement n'invente
     aucune quantité et ne force aucune conclusion — ne signale que si le résultat affirme plus
     que la somme de ses parties ;
   - la **causalité fabriquée** : l'article juxtapose, nous relions par « donc », « parce que ».
   Un implicite REEL du texte est acceptable ; une déduction que seul un lecteur averti ferait ne
   l'est pas.
2. `frame` — une remarque qui répond à une question que l'article ne pose pas. Le cadre t'est
   donné (`thesis_frame.main_claim` et `out_of_scope`) : une objection juste mais étrangère à la
   thèse déplace le sujet, et le lecteur ne sait plus ce qu'il évalue.
3. `centrality` — pour CHAQUE moment retenu : porte-t-il une pièce de `main_claim`, ou une
   remarque vraie mais périphérique ? Et les trois font-ils trois gestes différents, ou trois fois
   le même ? Signale le moment qu'un candidat du vivier (fourni) remplacerait avantageusement,
   en le nommant.
4. `presupposition` — sur les présupposés du socle (« Ce qu'il tient pour acquis ») et sur
   l'objection (`steel_man`), applique les trois tests :
   - **est-ce non dit ?** Si l'article ARGUMENTE ce point, ce n'est pas un présupposé mais le
     résumé de sa démonstration ;
   - **le texte dit-il le contraire ?** Relis la DERNIÈRE section : un présupposé démenti par la
     clôture est faux ;
   - **de qui est-ce le présupposé ?** Le socle dit ce que l'ARTICLE laisse inexaminé, jamais la
     prémisse de la position qu'il combat.

## La règle qui rend tes constats utilisables

**Chaque constat cite le texte.** Deux cas, et rien d'autre :
- `evidence_kind: "article_passage"` → `evidence` contient un extrait **MOT POUR MOT** de
  l'article (10 à 30 mots, sans guillemets, sans reformulation). Un extrait inexact fait tomber
  le constat.
- `evidence_kind: "absent"` → `evidence` contient les **termes que tu as cherchés** dans
  l'article et qui n'y sont pas, séparés par des virgules (p. ex. « héritages, succession,
  donation »). Choisis des termes que le texte utiliserait s'il traitait le point. Si l'un d'eux
  s'y trouve, le constat tombe.

Un constat sans citation vérifiable est retiré avant d'arriver au lecteur : ne t'en remets pas à
ton impression, va chercher le passage.

## Ce que tu ne fais PAS

- Aucun jugement sur la QUALITÉ de l'article : ce n'est pas lui qu'on relit.
- Aucune remarque de style, de longueur ou de goût, aucune réécriture du carrousel.
- Aucun commentaire sur les `quote` : elles sont vérifiées mot à mot par ailleurs.
- **Tu ne cherches pas à remplir une liste.** Un carrousel fidèle se solde par `findings: []` —
  réponse normale et fréquente. Huit constats au maximum ; au-delà, garde les plus graves.

## Format de chaque constat

- `kind` : `fidelity` | `frame` | `centrality` | `presupposition`
- `field` : le champ visé (p. ex. « display.essentiel[1] », « socle présupposé 2 », « beat 2 »)
- `our_text` : notre phrase exacte (≤120 caractères)
- `evidence_kind` : `article_passage` | `absent`
- `evidence` : l'extrait verbatim, ou les termes cherchés — voir ci-dessus
- `severity` : `blocking` pour `fidelity` et `frame` (nous faisons dire au texte ce qu'il ne dit
  pas) ; `advisory` pour `centrality` et `presupposition` (choix éditorial, un humain tranche)
- `suggestion` : facultatif, ≤15 mots — ce que l'article permet d'écrire à la place
