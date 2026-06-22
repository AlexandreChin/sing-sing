STEP 4/9 — PROBE

Ancre dans le texte les items de l'analyse globale (étapes 2 et 3). Chaque annotation doit prouver quelque chose de posé dans Logic ou Rhetoric — aucun item isolé sans racine dans l'analyse.

Contrainte `proves` : objet `{type, label}`. `type` ∈ `"observation"` / `"emotional_register"` / `"cui_bono"`. `label` doit correspondre exactement à un `aspect` / `emotion` / `beneficiary` de l'analyse globale. Pour `focus`, `type` doit être `"observation"`.

Citations verbatim : toujours mot pour mot depuis l'article — jamais paraphrasées.

---

## facts_vs_opinions — exactement 4 items

Montre ce qui sépare un fait sourcé et vérifiable d'une opinion de l'auteur.

Pour chaque item :
- `quote` : citation verbatim de l'article
- `presentation` : comment l'affirmation est présentée dans l'article, indépendamment de sa véracité :
  - `presented_as_established_fact` — affirmation factuelle sans attribution, présentée comme évidente ou certaine ; inclut les formules de blanchiment de crédibilité ("selon des experts", "des sources indiquent", "on sait que")
  - `attributed_to_source` — créditée à une source nommée et identifiable
  - `opinion_stated_as_fact` — jugement de valeur ou interprétation présenté syntaxiquement comme un constat ; repérable aux adverbes évaluatifs ("clairement", "évidemment"), aux adjectifs chargés glissés dans une phrase factuelle, ou aux verbes qui impliquent une intention sans la démontrer ("il cherche à", "il prétend que")
- `proves` : objet `{type, label}` — voir contrainte ci-dessus
- `explanation` : une phrase courte. Pas "c'est faux" mais "ce chiffre diffère du rapport officiel de X"
- `external_sources` (1 à 3 items) : `name` (nom précis), `supports` (`validates` / `contradicts` / `neutral`), `evidence_type` (`official_data` / `testimony` / `academic` / `media` / `party_statement`)
- `confidence` : probabilité estimée que l'affirmation soit factuellement vraie. `null` = invérifiable. Entier : 0–20 faux, 20–40 douteux, 40–60 disputé, 60–80 vraisemblablement vrai, 80–90 vrai, 90+ consensuel.

### Méthodologie confidence — facteurs par ordre décroissant

1. **Tangibilité des preuves** (le plus important) : données brutes, documents officiels, mesures, enregistrements auditables. Une affirmation reposant uniquement sur des assertions — même d'une source crédible — doit rester sous 60 sans corroboration.
2. **Témoignages désintéressés convergents** : plusieurs témoignages concordants de personnes sans intérêt matériel à mentir. Critères : indépendance entre les témoins, absence d'incitation à fabriquer. Peuvent pousser dans la zone 60–80 même sans documents.
3. **Crédibilité de la source** (le moins déterminant seul) : institutions internationales > ONG reconnues > parties prenantes directes. La crédibilité seule ne peut pas dépasser 50.
4. **Corroboration partielle adversariale** (poids très élevé) : quand une partie dont les intérêts s'opposent à l'affirmation la confirme partiellement. Fait monter le score significativement.
5. **Indépendance réelle de la chaîne probatoire** : deux sources apparemment indépendantes peuvent puiser dans le même gisement amont. La convergence depuis des chaînes vraiment séparées est bien plus forte.
6. **Spécificité de l'affirmation** : affirmations spécifiques et falsifiables ("100 décès entre la date X et la date Y") → score plus haut.
7. **Historique de la source** : cette source a-t-elle été prouvée juste ou fausse sur des affirmations comparables ?
8. **Vérifiabilité physique ou géographique** : lieux ou quantités mesurables → plus vérifiable. Intentions ou états internes → moins vérifiable.
9. **Taux de base** : à quelle fréquence des affirmations similaires s'avèrent-elles vraies dans des contextes comparables ?
10. **Documentation contemporaine** : documentée au moment des faits ou reconstituée rétrospectivement ?

**Règle d'asymétrie :** Un déni sans contre-méthodologie publiée, sans contre-données, sans décompte alternatif auditable ne compense pas symétriquement une source documentée.

**Bonus de convergence :** Deux sources aux méthodologies indépendantes arrivant à la même conclusion est matériellement plus fort qu'une seule source répétée.

---

## biases_and_focus — exactement 3 biais + 1 focus

### biases_and_rhetoric — exactement 3 items

Deux types d'items, à distinguer via `item_type` :

**`"bias"` — Procédés rhétoriques** : techniques d'écriture qui agissent sur l'émotion ou la perception — langage chargé, accumulation de détails, mise sur le même plan, sélection des faits, appel à l'autorité, fausse symétrie entre sources.

**`"fallacy"` — Glissements logiques** : endroits où la conclusion ne suit pas strictement des prémisses — fausse équivalence, généralisation abusive, pente glissante, argument circulaire, non sequitur, homme de paille. Décris ce qui se passe dans le texte — pas de noms latins.

Pour chaque item :
- `quote` : citation verbatim de l'article
- `item_type` : `"bias"` ou `"fallacy"`
- `label` : étiquette en langage courant. Identifie le procédé, jamais le contenu traité. "langage émotionnel" = correct. "hausse d'un taux d'intérêt" = incorrect — c'est le sujet, pas le procédé.
- `effect` : 1 phrase formulée comme une observation ("remarquez comment cela fait paraître X inévitable") — jamais un verdict
- `proves` : objet `{type, label}` — voir contrainte ci-dessus

Produis au moins 1 `bias` et 1 `fallacy` si l'article en contient — ne force pas si l'un des deux est absent.

### focus — exactement 1 item

La citation la plus importante ou révélatrice de l'article — celle qui concentre le mieux l'intention de l'auteur, une affirmation centrale, ou une formulation frappante.

- `quote` : citation verbatim
- `proves` : objet `{type, label}` — `type` doit être `"observation"`
- `analysis` : 3 phrases courtes maximum. Ce qu'elle dit, ce qu'elle sous-entend, ce qu'elle tait. Termine sur une question ouverte ou une observation suspendue — jamais un verdict. Le texte doit se tenir seul, sans référence aux autres parties.
