ÉTAPE 3 — LES TROIS PRISMES (slides 3 à 5)

L'axe et la position sont FIXÉS. Le message te dit quel prisme est écrit à chaque emplacement (p1, p2, p3) et lequel est celui du média. Pour CHAQUE emplacement, tu proposes plusieurs options (des formulations et des angles différents DE CE prisme, jamais un autre prisme), chacune avec son `slot`. Ces slides sont **hors cadre** : tes connaissances générales, pas l'article ; aucun chiffre (une année ou une date est permise), des sources réelles. Elles disent ce que la discipline éclaire, jamais ce que l'article n'a pas fait : pas de reproche.

- `question` (**≤{{cap:prismes.question}} caractères**, deux lignes au plus sur la slide, finit par « ? ») : la question de l'axe, vue par ce prisme. Elle garde un mot clé de la question de l'axe et la pose dans les termes de la discipline (pour « D'où viennent les déserts médicaux ? », l'économie demande « Les déserts médicaux suivent-ils les revenus ? »). C'est LA MÊME question, lue autrement : jamais une autre question sur le sujet (« Qui décide … ? », « Qui est touché … ? » quand l'axe demande d'où vient le phénomène). Elle ne contient aucune réponse.
- `line1`, `line2`, `line3` (**≤{{cap:prismes.line1}} caractères chacune**) : trois énoncés courts sur ce que cette discipline éclaire dans le sujet : ce qu'elle regarde, ce qu'elle fait voir de la question. Des phrases simples, qui nomment l'objet, sans chiffre (une année ou une date est permise), sans verdict (« la vraie cause »). Au moins une ligne nomme le sujet de l'axe. Les trois lignes disent trois choses différentes, et ne reprennent pas celles d'un autre prisme.
- `line4` (**≤{{cap:prismes.line4}} caractères**) : une quatrième ligne, FACULTATIVE (chaîne vide `""` sinon), seulement si elle apporte une idée de plus.
- `sources` : DEUX ou TROIS sources séparées par « ; », que le lecteur peut consulter pour creuser ce prisme. Des organisations ou des séries RÉELLES, nommées telles quelles (≤{{cap:prismes.source}} caractères chacune), sans URL ni nom de domaine, sans chiffre. Si tu n'es pas certain qu'une source existe, tu la remplaces par une plus connue.
- `media_note` (**≤{{cap:prismes.media_note}} caractères**) : UNIQUEMENT sur l'emplacement du prisme du média, une phrase **dans le cadre** qui dit ce que l'article fait avec ce prisme (ce qu'il suit, ce qu'il rapporte), avec ses éléments, sans jugement, sans « ce que l'article oublie ». Mot pour mot entre « » si tu cites. Sur les deux autres emplacements : chaîne vide `""`.
- `reason` : l'angle de l'option, et ce qu'elle apporte que les autres de l'emplacement n'apportent pas.

`recommended` : trois indices, un par emplacement. Recommande, pour chaque prisme, l'option dont la question reprend le mieux le mot clé de l'axe et dont les lignes sont les plus distinctes de celles des deux autres prismes.

Exemple, emplacement p2 = `economique` (un reportage sur un village qui perd son dernier médecin, hors cadre) :
- `question` : « Les déserts médicaux suivent-ils les revenus ? »
- `line1` : « Un médecin libéral s'installe là où son activité lui semble la plus sûre. »
- `line2` : « Les aides à l'installation visent les zones jugées peu rentables. »
- `line3` : « Dans un désert médical, gardes et trajets pèsent sur chaque médecin. »
- `line4` : `""`
- `sources` : « Assurance maladie ; Cour des comptes »
- `media_note` : `""`
- `reason` : « L'angle des revenus et des coûts de l'installation. »

Exemple, emplacement p1 = `sociologique`, prisme du média (même reportage) :
- `question` : « Quels choix de vie font les déserts médicaux ? »
- `line1` : « Les jeunes médecins préfèrent souvent exercer en groupe plutôt que seuls. »
- `line2` : « Un couple où chacun travaille cherche une ville qui offre deux emplois. »
- `line3` : « Les patients âgés, moins mobiles, vivent le plus durement un désert médical. »
- `line4` : `""`
- `sources` : « DREES (statistique santé) ; Insee »
- `media_note` : « Le reportage suit les patients du village et leur médecin, ses gardes et son départ. »
- `reason` : « L'angle des modes de vie, des médecins comme des patients. »
