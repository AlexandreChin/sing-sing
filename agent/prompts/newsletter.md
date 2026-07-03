ADAPTATION NEWSLETTER

L'analyse complète de l'article est fournie ci-dessus. Produis la couche de présentation pour une **newsletter** en français — de la PROSE détaillée qui se lit d'une traite. La newsletter suit les MÊMES temps que le carousel « optimized », mais en paragraphes développés (pas des fragments), plus une section « Pour aller plus loin ».

**Cohérence (impératif).** Toute la newsletter déroule une SEULE thèse : celle du `verdict` ci-dessus. Le `subject` et l'`intro` l'annoncent ; chaque section y revient.

**Fidélité aux nuances (impératif).** Quand l'analyse signale un contre-poids à une faiblesse, conserve-le. Inspecte `context.important_facts`, `analysis.fond.observations` et `guide.perspective` avant de rédiger.

**Voix.** Ton éditorial, direct, un peu incisif — celui d'un décryptage qui aide à mieux lire. Développé mais sans remplissage. JAMAIS de score de confiance, d'identifiant de nœud (`claim_3`, `cui_bono`…). Tu PEUX citer les mots de l'article entre guillemets « … » dans les failles.

**Mise en gras (lisibilité).** Dans les champs en PROSE (`intro`, `why_selected`, `payoff`, `context`, `reflexes`, `fact_check.reading`, `failles.body`, `strengths.body`, `angles_morts`, `verdict_line`, `go_further.why`), mets en gras avec `**…**` la ou les formulations décisives de chaque paragraphe — un chiffre-clé, un mot de l'article, ou l'idée qui porte le jugement — pour qu'on saisisse l'essentiel en survolant. Reste sobre : **au plus ~2 passages en gras par paragraphe**, jamais une phrase entière. N'en mets PAS dans `subject`, `preheader`, ni dans les `heading` / `title` / `claim` / `presentation` / `source`.

Champs à produire :

- `subject` : ≤12 mots — objet de l'e-mail. Accroche curieuse qui capte la tension, PAS le verdict.
- `preheader` : ≤15 mots — texte d'aperçu (boîte de réception), complète l'objet sans le répéter.
- `intro` : 3–4 phrases — l'accroche : le sujet, la tension éditoriale (ce qu'il a d'instructif), ce que la newsletter va décrypter.
- `why_selected` : 2–3 phrases — **Pourquoi cet article** : la raison éditoriale de l'avoir retenu à décrypter (cas d'école, révélateur…), PAS un éloge.
- `payoff` : 2–3 phrases — ce que le lecteur gagne concrètement à lire l'article.
- `context` : 3–4 phrases — **Avant de lire** : le contexte / la toile de fond nécessaire pour évaluer l'article. (depuis `context.contexts`)
- `reflexes` : exactement 2 items, 1 phrase chacun — les réflexes à garder en tête avant de lire. (depuis `guide.pre_reading`). Les 2 `reflexes` et les 2 `failles` forment des PAIRES indice → révélation : le réflexe `i` amorce ce que la faille `i` démontrera. Garde le même ordre.
- `fact_check` : 2 à 3 items — **Vérification des faits**, chacun `{claim, presentation, reading}` :
  - `claim` : l'affirmation, citée ou paraphrasée fidèlement
  - `presentation` : comment l'article la présente (« présenté comme un fait », « attribué à une source », « opinion présentée comme un fait »)
  - `reading` : 2–3 phrases — notre lecture critique : ce qui tient, ce qu'il faut recouper. (depuis `annotations.facts_vs_opinions`)
- `failles` : exactement 2 items `{heading, body, clue}` — **Les failles** (les 2 faiblesses décisives), appariées aux `reflexes` (même ordre) :
  - `heading` : titre court (ex. « Une source unique, sans contradiction »)
  - `body` : 3–5 phrases — explique le mécanisme de la faille ET pourquoi elle compte, en t'appuyant sur les mots de l'article (guillemets). (depuis `guide.watch_out` / `review.dimensions` les plus faibles)
  - `clue` : ≤12 mots — un rappel du réflexe apparié (`reflexes[i]`), formulé comme la question que le lecteur devait garder en tête (ex. « le constat tient-il à une seule institution ? »). Sans gras.
- `strengths` : 1 à 2 items `{heading, body}` — **Ce qui tient** : les forces réelles, `body` de 2–3 phrases. (depuis `review.dimensions` les mieux notées)
- `angles_morts` : 2 à 3 items, 1 phrase chacun — **Angles morts & nuances** : ce que l'article laisse de côté + la calibration honnête. (depuis `guide.perspective.blind_spots` et `balance`)
- `verdict_line` : 2–3 phrases — **Notre verdict** en prose : la recommandation (à lire / à lire avec réserves / à éviter) et pour qui. (depuis `review.verdict`)
- `go_further` : 2 à 3 items `{title, source, why, type}` — **Pour aller plus loin** : des ressources qui complètent l'article (comblent un angle mort, éclairent un chiffre). `why` = 1–2 phrases. `type` = la nature de la ressource, en un ou deux mots (ex. « étude », « rapport », « documentaire », « livre », « podcast », « article », « données »). Inspire-toi de `review.verdict.further_resource` et des angles morts.
- `signoff` : 1 phrase — clôture qui invite à réagir ou partager (CTA léger).
