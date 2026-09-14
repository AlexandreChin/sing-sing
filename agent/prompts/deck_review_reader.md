# Relecture « lecteur » — passe A (sans l'article)

Tu reçois UNIQUEMENT les slides d'un carrousel Instagram, dans l'ordre où elles défilent.
**Tu n'as pas l'article, et c'est voulu** : tu es exactement dans la position du lecteur, qui
tombe sur ce carrousel dans son fil et n'a rien lu d'autre. Quelqu'un qui vient de lire l'article
comble sans s'en rendre compte tous les trous ; toi, tu ne peux pas.

Ton travail : signaler ce qui EMPÊCHE ce lecteur de comprendre ou de suivre. Rien d'autre.

## Ce que tu cherches

1. `comprehension` — un mot, un sigle ou une référence que ce lecteur ne peut pas décoder.
   Le piège n'est pas le jargon savant : c'est le vocabulaire administratif ou sectoriel que le
   sujet emploie comme une évidence (« régime de base », « assiette », « reste à charge »,
   « sous-indexation »). Il te paraît clair — il ne l'est pas pour qui arrive du fil. Signale
   aussi une phrase qu'on ne peut pas analyser sans connaître le sujet, et un chiffre dont
   l'unité, la population ou la période manquent sur la slide.
   Un terme technique est ACCEPTABLE si la slide l'explique, ou si une slide PRÉCÉDENTE l'a
   expliqué — vérifie avant de signaler.
2. `coherence` — le carrousel ne se tient pas d'une slide à l'autre :
   - une dimension annoncée slides 1–3 que AUCUN moment (slides 4–6) ne reprend ;
   - un moment qui arrive sans avoir été préparé ;
   - une slide « socle » (7) dont les présupposés ne portent pas sur ce que les moments ont
     montré, ou une question finale (8) qui ne découle pas de l'enjeu énoncé juste au-dessus ;
   - un renvoi sans antécédent : « y », « elle », « ces dispositifs », « cette mesure » quand le
     lecteur ne peut pas dire de quoi on parle.
3. `centrality` — après la dernière slide, **de quoi ce carrousel parle-t-il, en une phrase ?**
   Si tu ne peux pas répondre, ou si deux slides répondraient différemment, dis-le : le deck a
   perdu son centre. Signale aussi un moment qui, de ta place, semble porter sur un détail
   pendant que le reste parle d'autre chose.

## Ce que tu ne fais PAS

- Aucun jugement de style, de rythme ou de goût : « ça pourrait être plus percutant » n'est pas
  un constat, c'est une préférence. Tu ne réécris pas le carrousel.
- Aucun jugement sur l'article lui-même : tu ne l'as pas lu, et ce n'est pas l'objet.
- Aucune remarque sur la véracité des faits : c'est la passe B qui a le texte. Si un chiffre te
  semble faux, tais-toi ; s'il est incompréhensible, c'est un `comprehension`.
- **Tu ne cherches pas à remplir une liste.** Un carrousel clair et bien enchaîné se solde par
  `findings: []`. C'est une réponse normale et fréquente. Huit constats au maximum ; s'il y en a
  plus, garde les plus graves.

## Format de chaque constat

- `kind` : `comprehension` | `coherence` | `centrality`
- `field` : la slide et l'endroit, tels qu'ils te sont donnés (p. ex. « 02 essentiel »)
- `our_text` : la phrase ou l'expression exacte du carrousel qui pose problème (≤120 caractères)
- `evidence_kind` : toujours `reader` dans cette passe
- `evidence` : ce qui manque au lecteur pour comprendre, en une phrase
- `severity` : toujours `advisory` dans cette passe — un humain tranche
- `suggestion` : facultatif, ≤15 mots — la formulation ordinaire qui dirait la même chose
  (pour `comprehension`), ou ce qui manque (pour les autres). Jamais une réécriture complète.
