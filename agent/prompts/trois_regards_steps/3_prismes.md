ÉTAPE 3 — LES TROIS PRISMES (slides 3 à 5)

L'axe et la position sont FIXÉS. Le message te dit quel prisme est écrit à chaque emplacement (p1, p2, p3) et lequel est celui du média. Pour CHAQUE emplacement, tu proposes plusieurs options (des thèses et des jeux de cartes différents DE CE prisme, jamais un autre prisme), chacune avec son `slot`. Ces slides sont **hors cadre** : tes connaissances générales, pas l'article ; aucun chiffre (une année ou une date est permise), des sources réelles. Elles disent ce que la discipline éclaire, jamais ce que l'article n'a pas fait : pas de reproche. Sur ces slides, le regard **répond** à la question du carrousel : chaque carte donne une cause et la façon dont elle agit. La question du carrousel n'y est jamais recopiée.

- `title` (**au plus {{cap:prismes.title}} caractères**, deux lignes au plus) : la THÈSE du prisme, sa réponse à la question de l'axe dans ses propres termes, en groupe nominal ou en phrase courte (pour « D'où viennent les déserts médicaux ? », l'économie répond « Une installation qui **suit les revenus** »). Un passage en or `**…**` permis. Une thèse, pas une question ; ce que ce regard voit, pas un verdict sur les deux autres.
- `lead` (**au plus {{cap:prismes.lead}} caractères**, UNE ligne) : ce que ce regard examine, dans les mots du sujet (« Ce que gagne, dépense et risque un médecin libéral »). Jamais une question, jamais la question du carrousel, aucun chiffre. Sur l'emplacement du prisme du média : chaîne vide `""` (sa `media_note` tient lieu d'introduction).
- Quatre cartes, toutes obligatoires, chacune un MÉCANISME différent que ce prisme met en avant (voir LES CARTES dans le cadre commun) :
  - `head1`, `head2`, `head3`, `head4` (**au plus {{cap:prismes.head}} caractères**) : la CAUSE, un mécanisme dans les termes du prisme, sans « ? », jamais un simple fait.
  - `answer1`, `answer2`, `answer3`, `answer4` (**au plus {{cap:prismes.answer}} caractères**, deux lignes) : UNE phrase simple qui dit comment cette cause agit et ce qu'elle explique dans ce cas, avec un lien de cause (quand, si, dès que, faute de, parce que, donc, ce qui…). Dans la voix du regard, jamais comme un fait établi ; jamais une question ; aucun chiffre ; elle ne reformule pas la tête.
  - `indice1`, `indice2`, `indice3`, `indice4` : `source | ce qu'on y lit` (la source au plus {{cap:prismes.indice.source}} caractères, ce qu'on y lit au plus {{cap:prismes.indice.find}}) : la série ou le document précis qui permettrait de vérifier ce mécanisme, et ce qu'on y lit ; une source réelle par carte, jamais une URL ni un chiffre.
  Chaque carte garde un mot clé de la question de l'axe (le sujet, ou son verbe), dans sa tête ou sa réponse : c'est la même question, lue autrement. Les quatre têtes commencent par des mots différents et n'ont pas le même verbe ; les quatre réponses commencent par des mots différents, et pas par les ouvertures déjà prises sur les autres prismes. Les quatre cartes ne se répètent pas entre elles, et ne reprennent pas celles d'un autre prisme.
- `media_note` (**au plus {{cap:prismes.media_note}} caractères**, UNE ligne) : UNIQUEMENT sur l'emplacement du prisme du média, une phrase **dans le cadre** qui dit ce que l'article fait avec ce prisme (ce qu'il suit, ce qu'il rapporte), avec ses éléments, sans jugement, sans « ce que l'article oublie ». Mot pour mot entre « » si tu cites. Sur les deux autres emplacements : chaîne vide `""`.
- `reason` : l'angle de l'option, et ce qu'elle apporte que les autres de l'emplacement n'apportent pas.

La réponse d'une carte, le bon puis le mauvais (le mauvais nomme son défaut) :
- BON `prismes.p2.answer2` : « Si l'aide pèse peu face au revenu espéré en ville, elle ne retient pas le désert. »
- MAUVAIS (une question) `prismes.p2.answer2` : « L'aide compte-t-elle face au revenu espéré en ville ? »
- MAUVAIS (reprise de la tête) `prismes.p2.answer2` : « Les zones fragiles ont donc des aides. »
- MAUVAIS (un chiffre) `prismes.p2.answer2` : « L'aide vaut 50 000 euros, donc elle pèse peu face au revenu d'un désert. »

`recommended` : trois indices, un par emplacement. Recommande, pour chaque prisme, l'option dont la thèse répond le plus nettement à la question de l'axe et dont les quatre mécanismes sont les plus distincts entre eux et de ceux des deux autres prismes.

Exemple, emplacement p1 = `sociologique`, prisme du média (un reportage sur un village qui perd son dernier médecin, hors cadre sauf la phrase du média) :
- `title` : « Des déserts nés des **choix de vie** »
- `lead` : `""`
- `head1` : « Le travail en groupe attire »
- `answer1` : « Faute d'associés, le cabinet isolé d'un désert médical ne trouve plus de repreneur. »
- `indice1` : « DREES | les façons d'exercer des généralistes, selon la commune »
- `head2` : « Deux carrières, une seule ville »
- `answer2` : « Si le conjoint ne trouve pas d'emploi sur place, le médecin fuit le désert médical. »
- `indice2` : « Insee | l'emploi des couples selon le type de commune »
- `head3` : « Les patients âgés moins mobiles »
- `answer3` : « Quand les patients âgés ne conduisent plus, chaque désert médical les isole davantage. »
- `indice3` : « Irdes | l'accès aux soins des personnes âgées, par territoire »
- `head4` : « Écoles et postes qui ferment »
- `answer4` : « Un village qui perd son école attire moins un médecin, ce qui creuse le désert. »
- `indice4` : « Observatoire des territoires | la carte des services de proximité »
- `media_note` : « Le reportage suit les patients du village et leur médecin. »
- `reason` : « Quatre choix de vie : exercer à plusieurs, le métier du conjoint, l'âge des patients, les services alentour. »

Exemple, emplacement p2 = `economique` (même reportage) :
- `title` : « Une installation qui **suit les revenus** »
- `lead` : « Ce que gagne, dépense et risque un médecin libéral »
- `head1` : « Le médecin libéral choisit son lieu »
- `answer1` : « Libre de son lieu, le médecin suit la clientèle solvable, donc s'éloigne des déserts. »
- `indice1` : « Assurance maladie | la densité de médecins, territoire par territoire »
- `head2` : « Des aides pour les zones fragiles »
- `answer2` : « L'aide compte peu car le revenu espéré en ville reste plus fort que dans un désert. »
- `indice2` : « Cour des comptes | ses rapports sur les aides à l'installation »
- `head3` : « Un même tarif, des coûts inégaux »
- `answer3` : « Dès que le cabinet rural coûte plus cher, exercer dans un désert médical rapporte moins. »
- `indice3` : « DREES | les revenus des médecins libéraux selon la zone »
- `head4` : « Les gardes alourdissent la charge »
- `answer4` : « Parce que les gardes pèsent sur peu de médecins, chaque départ aggrave le désert. »
- `indice4` : « Ordre des médecins | l'atlas de la démographie médicale »
- `media_note` : `""`
- `reason` : « Quatre mécanismes de marché : la liberté d'installation, les aides, les coûts, la charge de travail. »
