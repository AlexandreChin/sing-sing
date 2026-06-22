STEP 1/9 — SCAN + CONTEXT

Lis l'article et extrais sans interpréter. Ne conclus pas. Ne juge pas.

---

## article_type

Identifie le type parmi :
- `editorial` — position officielle du journal, sans byline individuel
- `news_report` — reportage factuel
- `opinion` — tribune signée
- `investigation` — journalisme d'enquête
- `interview`
- `other`

---

## Extraction brute

- `key_quotes` : citations verbatim les plus importantes ou révélatrices de l'article
- `authority_anchors` : entités (personnes, organisations, institutions) citées pour conférer de la crédibilité à une affirmation spécifique. Pour chacune : `entity` (nom) + `used_for` (quelle affirmation elle est invoquée à légitimer)
- `notable_omissions` : éléments attendus dans ce type de contenu qui sont absents — sources non consultées, angles ignorés, données manquantes
- `rhetorical_patterns` : patterns dans la structure, le vocabulaire, la mise en scène — ce qui revient, ce qui est mis en avant, la façon dont l'auteur construit son propos

---

## context — ancre les étapes suivantes

Produis 2 à 4 items par liste, 1 phrase courte par item. Présente les faits comme des observations que le lecteur peut vérifier lui-même.

- `contexts` : situation générale dans laquelle s'inscrit l'article — ce qui s'est passé avant, le contexte institutionnel ou géographique, les événements qui expliquent pourquoi cet article paraît maintenant

- `who_is_speaking` : qui produit ce contenu — positionnement du média, financement connu, ligne éditoriale sur ce sujet. Si l'article est signé : parcours de l'auteur, positions connues, historique sur ce sujet. Pour un éditorial non signé : l'institution, sa ligne, ce que signer collectivement implique.

- `important_facts` : faits saillants que le lecteur doit connaître pour bien évaluer l'article — peuvent être mentionnés dans l'article ou totalement absents de celui-ci. Ces faits servent d'ancrage aux étapes suivantes.

- `key_terms` : termes techniques, acronymes ou concepts spécifiques que le lecteur non spécialiste pourrait ne pas connaître. Chaque item : `term` (le mot ou sigle) + `definition` (1 phrase, sans jargon, en langage courant).
