ÉTAPE 3 — LES TROIS PRISMES (slides 3 à 5)

L'axe et la position sont FIXÉS. Le message te dit quel prisme est écrit à chaque emplacement (p1, p2, p3) et lequel est celui du média. Pour CHAQUE emplacement, tu proposes plusieurs options (des thèses et des jeux de cartes différents DE CE prisme, jamais un autre prisme), chacune avec son `slot`. Ces slides sont **hors cadre** : tes connaissances générales, pas l'article ; aucun chiffre (une année ou une date est permise), des sources réelles. Elles disent ce que la discipline éclaire, jamais ce que l'article n'a pas fait : pas de reproche. Sous le titre, la slide affiche d'elle-même la question de l'axe : tu ne la recopies pas.

- `title` (**au plus {{cap:prismes.title}} caractères**, deux lignes au plus) : la THÈSE du prisme, sa réponse à la question de l'axe dans ses propres termes, en groupe nominal ou en phrase courte (pour « D'où viennent les déserts médicaux ? », l'économie répond « Une installation qui **suit les revenus** »). Un passage en or `**…**` permis. Une thèse, pas une question ; ce que ce regard voit, pas un verdict sur les deux autres.
- Quatre cartes, toutes obligatoires, chacune un MÉCANISME différent que ce prisme met en avant (voir LA CARTE dans le cadre commun) :
  - `head1`, `head2`, `head3`, `head4` (**au plus {{cap:prismes.head}} caractères**) : l'assertion, une cause ou un mécanisme, dans les termes du prisme, sans « ? ».
  - `claim1`, `claim2`, `claim3`, `claim4` (**au plus {{cap:prismes.claim}} caractères**, finit par « ? ») : le même point posé en question.
  - `indice1`, `indice2`, `indice3`, `indice4` : `source | ce qu'on y cherche` (la source au plus {{cap:prismes.indice.source}} caractères, ce qu'on y cherche au plus {{cap:prismes.indice.find}}), une source réelle par carte, jamais une URL ni un chiffre.
  Chaque carte garde un mot clé de la question de l'axe (le sujet, ou son verbe), dans son `head` ou son `claim` : c'est la même question, lue autrement. Les quatre cartes ne se répètent pas entre elles, et ne reprennent pas celles d'un autre prisme.
- `media_note` (**au plus {{cap:prismes.media_note}} caractères**) : UNIQUEMENT sur l'emplacement du prisme du média, une phrase **dans le cadre** qui dit ce que l'article fait avec ce prisme (ce qu'il suit, ce qu'il rapporte), avec ses éléments, sans jugement, sans « ce que l'article oublie ». Mot pour mot entre « » si tu cites. Sur les deux autres emplacements : chaîne vide `""`.
- `reason` : l'angle de l'option, et ce qu'elle apporte que les autres de l'emplacement n'apportent pas.

`recommended` : trois indices, un par emplacement. Recommande, pour chaque prisme, l'option dont la thèse répond le plus nettement à la question de l'axe et dont les quatre mécanismes sont les plus distincts entre eux et de ceux des deux autres prismes.

Exemple, emplacement p1 = `sociologique`, prisme du média (un reportage sur un village qui perd son dernier médecin, hors cadre sauf la phrase du média) :
- `title` : « Des déserts nés des **choix de vie** »
- `head1` : « Le travail en groupe attire »
- `claim1` : « Le désert vient-il de l'exercice isolé ? »
- `indice1` : « DREES | les enquêtes sur les façons d'exercer des généralistes »
- `head2` : « Deux carrières, une seule ville »
- `claim2` : « Le conjoint pèse-t-il sur les déserts ? »
- `indice2` : « Insee | l'emploi des couples selon le type de commune »
- `head3` : « Les patients âgés moins mobiles »
- `claim3` : « Qui vit le plus durement un désert médical ? »
- `indice3` : « Irdes | l'accès aux soins des personnes âgées »
- `head4` : « Les services publics se retirent »
- `claim4` : « Le désert suit-il le départ des services ? »
- `indice4` : « Observatoire des territoires | la carte des services de proximité »
- `media_note` : « Le reportage suit les patients du village et leur médecin, ses gardes et son départ. »
- `reason` : « Quatre choix de vie : exercer à plusieurs, le métier du conjoint, l'âge des patients, les services alentour. »

Exemple, emplacement p2 = `economique` (même reportage) :
- `title` : « Une installation qui **suit les revenus** »
- `head1` : « Le médecin libéral choisit son lieu »
- `claim1` : « Le libre choix fait-il les déserts médicaux ? »
- `indice1` : « Assurance maladie | la densité de médecins, territoire par territoire »
- `head2` : « Des aides pour les zones fragiles »
- `claim2` : « Les aides suffisent-elles contre les déserts ? »
- `indice2` : « Cour des comptes | ses rapports sur les aides à l'installation »
- `head3` : « Un même tarif, des coûts inégaux »
- `claim3` : « Exercer en désert médical coûte-t-il plus ? »
- `indice3` : « DREES | les revenus des médecins libéraux selon la zone »
- `head4` : « Les gardes alourdissent la charge »
- `claim4` : « La charge de travail vide-t-elle les déserts ? »
- `indice4` : « Ordre des médecins | l'atlas de la démographie médicale »
- `media_note` : `""`
- `reason` : « Quatre mécanismes de marché : la liberté d'installation, les aides, les coûts, la charge de travail. »
