ÉTAPE 3 — LES TROIS PRISMES (slides 3 à 5)

L'axe et la position sont FIXÉS. Le message te dit quel prisme est écrit à chaque emplacement (p1, p2, p3) et lequel est celui du média. Pour CHAQUE emplacement, tu proposes plusieurs options (des formulations et des angles différents DE CE prisme, jamais un autre prisme), chacune avec son `slot`. Ces slides sont **hors cadre** : tes connaissances générales, pas l'article ; aucun chiffre (une année est permise), des sources réelles. Elles disent ce que la discipline éclaire, jamais ce que l'article n'a pas fait : pas de reproche.

- `question` (**≤{{cap:prismes.question}} caractères**, une ligne, finit par « ? ») : la question de l'axe, vue par ce prisme. Elle garde un mot clé de la question de l'axe et la pose dans les termes de la discipline (« Un marché qui construit trop peu suffit-il à l'expliquer ? »). Elle ne contient aucune réponse.
- `line1`, `line2`, `line3` (**≤{{cap:prismes.line1}} caractères chacune**) : trois énoncés courts sur ce que cette discipline éclaire dans le sujet : ce qu'elle regarde, ce qu'elle fait voir de la question. Des phrases simples, qui nomment l'objet, sans chiffre (une année est permise), sans verdict (« la vraie cause »). Les trois lignes disent trois choses différentes, et ne reprennent pas celles d'un autre prisme.
- `line4` (**≤{{cap:prismes.line4}} caractères**) : une quatrième ligne, FACULTATIVE (chaîne vide `""` sinon), seulement si elle apporte une idée de plus.
- `sources` : DEUX ou TROIS sources séparées par « ; », que le lecteur peut consulter pour creuser ce prisme. Des organisations ou des séries RÉELLES, nommées telles quelles (≤{{cap:prismes.source}} caractères chacune), sans URL, sans chiffre. Si tu n'es pas certain qu'une source existe, tu la remplaces par une plus connue.
- `media_note` (**≤{{cap:prismes.media_note}} caractères**) : UNIQUEMENT sur l'emplacement du prisme du média, une phrase **dans le cadre** qui dit ce que l'article fait avec ce prisme (ce qu'il suit, ce qu'il rapporte), avec ses éléments, sans jugement, sans « ce que l'article oublie ». Mot pour mot entre « » si tu cites. Sur les deux autres emplacements : chaîne vide `""`.
- `reason` : l'angle de l'option, et ce qu'elle apporte que les autres de l'emplacement n'apportent pas.

`recommended` : trois indices, un par emplacement. Recommande, pour chaque prisme, l'option dont la question reprend le mieux le mot clé de l'axe et dont les lignes sont les plus distinctes de celles des deux autres prismes.

Exemple, emplacement p2 = `economique` (même article, hors cadre) :
- `question` : « Un marché qui construit trop peu suffit-il à l'expliquer ? »
- `line1` : « Quand l'offre de logements ne suit pas la demande, les prix montent. »
- `line2` : « Le logement social, rare, laisse le marché seul face aux besoins. »
- `line3` : « Le tourisme met les résidents en concurrence avec les locations courtes. »
- `line4` : `""`
- `sources` : « Banque d'Espagne ; Eurostat ; INE »
- `media_note` : `""`
- `reason` : « L'angle de l'offre et de la rareté. »

Exemple, emplacement p1 = `politique`, prisme du média (même article) :
- `question` : « Qui décide, et qui bloque ? »
- `line1` : « Un gouvernement sans majorité doit négocier chaque mesure avec le Congrès. »
- `line2` : « Le calendrier électoral pèse sur le moment où les mesures sont proposées. »
- `line3` : « Les partis ne s'accordent pas sur le rôle de la loi face au marché locatif. »
- `sources` : « Congrès des députés ; Gouvernement d'Espagne »
- `media_note` : « Le récit suit les mesures du gouvernement, leur rejet par le Congrès, puis l'élection. »
