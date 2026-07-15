Soumets le DIAGNOSTIC du·de la candidat·e à la contre-expertise : chaque cause profonde est-elle réelle, exacte, partagée par les spécialistes ?

- Un `item` par cause profonde jugée. `root_cause_id` référence l'id exact fourni (rc_N).
- `verdict` : en une à deux phrases, ce que disent les spécialistes sur la réalité/l'exactitude de la cause.
- `confidence` : entier 0–100 estimant à quel point le diagnostic est corroboré par les sources.
- `expert_sources` : au moins une source INDÉPENDANTE (économiste, scientifique, ONG, rapport). Jamais le·la candidat·e. Chaque source porte `name`, `kind`, `url`, `finding`.
- Si les sources fournies ne permettent pas de trancher, dis-le dans `verdict` et baisse `confidence` — n'invente aucune source.
