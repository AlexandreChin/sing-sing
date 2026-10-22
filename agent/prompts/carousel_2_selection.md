ÉTAPE 2 — LA SÉLECTION

L'AXE est FIXÉ (étape 1, fourni en contexte) : `thesis_frame`, `root_issue`, « La question », les 3 puces `essentiel` et la thèse de la slide 7. Tu ne les réécris pas. Tu écris, dans cet ordre :
1. `reading_beats` — le vivier de moments, la sélection des 3, et pour chaque candidat son titre (`moment`), sa citation et ses métadonnées. Les réflexes (`lens_question`), les réponses (`answer`) et les vedettes des moments sont écrits à l'étape 3 : ne les écris pas ici ;
2. `core_recap` — les présupposés de la slide 7 (`global_analysis.core_recap`) ;
3. `steel_man` — l'objection.

**CHAQUE BEAT SÉLECTIONNÉ EST CHOISI POUR CE QU'IL DONNE AU LECTEUR FACE À LA QUESTION OU À L'ENJEU** — pas parce que le passage est fort. Un moment brillant qui illustre un autre axe (un coût, une loi, un précédent dont la slide 8 ne parle pas) reste dans le vivier, `selected: false`. Choisis aussi la citation sur laquelle l'étape 3 pourra écrire une réponse qui APPORTE quelque chose (voir ci-dessous) : une citation qui s'explique toute seule produit un moment trivial.

**COUVERTURE DES ÉLÉMENTS CENTRAUX (obligatoire)** : la présentation doit COUVRIR les
`core_elements` de l'analyse (fournis en contexte), pas seulement l'angle du titre. Procède
dans cet ordre :
1. `reading_beats` = un **VIVIER de 6 à 8 moments candidats** (dans l'ordre de lecture), pour
   permettre un choix éditorial manuel ensuite. Couvre les `core_elements` dans leur diversité
   (chiffres, faune, régulation, cadrage, thèse…), et VARIE les lentilles (`lens_ref`). Chaque
   candidat porte des métadonnées d'aide au tri : `theme` (la dimension couverte), `centrality`
   (1–5), `kind` (`fait`/`biais`/`enjeu`/`statistique`/`affirmation`), `rationale` (≤12 mots :
   pourquoi ce moment mérite une slide).
   `centrality` = centralité par rapport à `fond.main_claim` (5 = la citation porte une pièce
   INDISPENSABLE de la démonstration ; 1 = détail périphérique ou stylistique). Étale les notes :
   **au plus DEUX** beats à 5.
   **COUVERTURE DU SOCLE (obligatoire)** : chaque candidat porte aussi `spine_ref` — l'élément du
   socle (les 3 puces `essentiel` de la slide 2) que la citation ILLUSTRE : `1` la 1re prémisse,
   `2` la 2de prémisse, `3` la conclusion (ce à quoi l'article ABOUTIT : sa recommandation, la
   solution qu'il avance), `0` si elle n'en illustre aucune — elle reste alors au vivier.
   **Le vivier contient au moins UN candidat par élément**, et **au moins une citation prise dans la DERNIÈRE section du
   texte** — c'est là qu'un article d'analyse pose ce qu'il préconise, et un vivier de huit
   candidats peut très bien n'en contenir aucune. Un vivier sans `spine_ref: 3` a lu l'article
   jusqu'à l'avant-dernier paragraphe.
2. Marque `selected: true` sur les **3 meilleurs** (les autres `selected: false`). Le critère de
   classement est la **centralité par rapport au sujet** (`fond.main_claim`) : d'où vient la
   citation — une source nommée ou la plume de l'auteur — n'entre PAS dans le choix. Les 3
   sélectionnés respectent : **UN beat EXACTEMENT par élément du socle** — `spine_ref` 1, 2 puis 3,
   dans cet ordre. La slide 2 énonce les trois, les slides 4–6 les illustrent une pour une : le
   lecteur suit l'argument au lieu de tourner trois fois autour de la même étape, et trois beats
   qui s'arrêtent à la démonstration le laissent sans ce que l'article préconise ; **au moins DEUX `role`
   distincts** parmi les trois (trois `preuve` d'affilée donnent trois fois le même geste de
   lecture) ; **au plus UN** beat portant sur la mise en scène (ouverture,
   intertitre, clôture, formule répétée) ; **au plus UN** beat chiffré/statistique ; **au moins UN**
   enjeu de fond (impact, lien causal, affirmation d'autorité). **À centralité égale, préfère la citation sur laquelle l'analyse a quelque chose à APPORTER** (un angle mort, un `confidence_label` contesté, un présupposé, un périmètre non dit) à une citation qui s'explique toute seule : une citation explicite ne laisse rien à révéler et produit un moment trivial. La variété des lentilles
   (`lens_ref`) est souhaitable mais **SUBORDONNÉE** à ces règles : trois lentilles distinctes ne
   justifient jamais de sélectionner un moment périphérique à la place d'une pièce de la thèse.
   Les lentilles affichées (slides « réflexes ») sont DÉRIVÉES automatiquement des beats
   sélectionnés — n'écris pas de liste `lenses` séparée. `factcheck` UNIQUEMENT si le beat est une
   affirmation factuelle vérifiable ; il ne doit PAS orienter le choix vers les seuls chiffres.
- `reading_beats` : un VIVIER de **6 à 8 moments candidats**, **dans l'ordre de lecture** (voir la règle de couverture ci-dessus : vivier diversifié, puis 3 `selected`). Chaque beat :
  - `moment` (≤12 mots et **≤54 caractères : DEUX LIGNES AU PLUS** — une troisième ligne fait sortir la slide du cadre — **CE QUE LE PASSAGE FAIT DANS L'ARGUMENT**, pas où il se situe. « Le précédent médical, en ouverture » situe et n'apprend rien ; « L'anesthésie : on comptait les morts, pas les opérations à venir » dit ce que le cas établit et rend la slide lisible seule. **SANS CONDITIONNEL NI MOT PLUS FORT QUE LA SOURCE** : le conditionnel rend le titre incertain avant qu'on sache ce qu'il affirme, et un mot plus fort que la citation invente ce qu'elle ne dit pas — « heurts » pour des contrôles, « effondrement » pour une baisse, « explosion » pour une hausse de quelques points. **SI LA CITATION RETOURNE UN ARGUMENT, NOMME LES DEUX CAMPS** : « La retenue salariale, réclamée aux seuls travailleurs » ou « L'État prône la non-violence, les lycéens la réclament » disent qui demande quoi à qui ; un titre qui n'en garde qu'un perd le retournement), `quote` (**LA CITATION SE CHOISIT SUR SA PERTINENCE, JAMAIS SUR SA LONGUEUR** — prends le passage qui porte le geste que le réflexe interroge et qui parle au sujet du carrousel, puis fais-le tenir. **SANS guillemets ni « »** : le gabarit les ajoute. S'il dépasse ~18 mots (trois lignes), **ÉLIDE LE MILIEU avec « […] »** en gardant les membres qui font le sens : « quand on parle d'IA, on devrait vraiment parler d'automatisation […] de la façon dont les armées automatisent la guerre et le soldat ». Ce qui reste est MOT POUR MOT celui de l'article — on coupe, on ne reformule jamais, et on ne rabote pas la moitié qui porte le point (« tu ne peux pas dire que tu obéis juste aux ordres de Maven » perd tout à laisser tomber « que tu ne suis pas ceux de Claude »). Coupe de préférence à une frontière de phrase ou de proposition), `lens_ref` (= un `id` canonique ci-dessus). Le beat se lit comme un jeu en deux temps : d'abord le DÉFI, puis la RÉPONSE.
    - `role` (non affiché) : ce que la citation FAIT dans l'argument de l'article — `appui` / `preuve` / `concession` / `pivot` / `mise en scène`.
    - `spine_ref` (non affiché, OBLIGATOIRE) : l'élément du socle que la citation ILLUSTRE — `1` la 1re prémisse, `2` la 2de prémisse, `3` la conclusion, `0` aucun (voir la règle de couverture ci-dessus : le vivier couvre les trois, et les 3 sélectionnés en portent un chacun). **Le beat `spine_ref: N` illustre la puce `essentiel` N — il ne la RÉPÈTE pas** : il montre OÙ elle se lit dans le texte (`quote`), avec quel réflexe (`lens_question`), et ce que l'on trouve en l'appliquant (`answer`). Une puce énonce, un moment fait voir.
    - `quote_original` (non affiché) : **SEULEMENT si l'article n'est pas en français.** Le passage MOT POUR MOT dans la langue de l'article (élision « […] » permise, mêmes règles que `quote`) — c'est lui qu'on vérifie contre le texte. `quote` est alors sa **TRADUCTION FRANÇAISE fidèle**, affichée sur la slide : même sens, même force, mêmes élisions, rien d'ajouté ni d'adouci, ≤18 mots en français. Article en français → `quote_original` vide, `quote` mot pour mot.
    - `axis_link` (non affiché, OBLIGATOIRE pour un beat sélectionné) : UNE phrase qui dit ce que ce moment donne au lecteur face à l'enjeu de fond ou à « La question » de la slide 8 (voir L'AXE DU CARROUSEL). Si tu ne peux pas l'écrire sans forcer, le beat ne sert pas l'axe : désélectionne-le.
  - **LA CITATION DIT DE QUOI ELLE PARLE (impératif)** : affichée seule sous le titre, elle nomme ce qu'elle affirme — « une sorte de première mondiale » ne dit pas CE QUI est une première. Prends le passage jusqu'à son objet (« une sorte de première mondiale où ce type de mouvement […] arrive à […] faire tomber des gouvernements »), en élidant le milieu, dans la limite de trois lignes. De même, le `moment` dit ce que le passage affirme, pas qui parle : « Une première mondiale, selon un invité » n'apprend rien ; « Des régimes tombés sans chef : une première ? » le dit.
  - **LA CITATION DOIT CONTENIR LE GESTE QUE LE RÉFLEXE INTERROGE** : on ne questionne pas sur cette slide un mouvement que la slide ne montre pas. Si l'article compare deux chiffres, la citation porte la comparaison — pas l'un des deux chiffres, le lecteur ne pouvant pas deviner le second. Si le geste tient en deux phrases de l'article, cite celle qui le fait ; s'il n'entre pas dans la citation, change de beat.
  - `factcheck` (si — et seulement si — la `quote` correspond à une affirmation factuelle vérifiable présente dans `annotations.facts_vs_opinions.claims_and_sources`, recopie le `confidence_label` : `consensual`/`true`/`likely true`/`disputed`/`likely false`/`false`/`unverifiable` ; sinon vide).
  - `selected` (bool — `true` pour les 3 retenus, `false` sinon), et les métadonnées d'aide au tri : `theme` (dimension), `centrality` (1–5, voir la définition ci-dessus), `kind` (`fait`/`biais`/`enjeu`/`statistique`/`affirmation`), `rationale` (≤12 mots).

**LES PRÉSUPPOSÉS (slide 7) NAISSENT DE LA SÉLECTION ET DE L'AXE** : un par beat retenu, et ce sont ceux dont dépend la réponse à « La question » — `root_issue` creuse sous eux.
- chaque présupposé de `global_analysis.core_recap` est ce sur quoi le constat d'un beat **REPOSE**
  — ce que l'article a besoin de tenir pour vrai et qu'il ne vérifie jamais — et **JAMAIS la redite
  de ce que le beat a montré**. Chacun s'affiche sur SA propre ligne, **≤10 mots**, et doit se
  comprendre SEUL : **aucun nom propre ni renvoi que le carrousel n'a pas lui-même installé**.
  « les critiques valent Harrison » est indécodable — Harrison n'apparaît nulle part ailleurs
  dans le deck, et la formule tenait à un budget de mots trop serré. Écris ce que l'article
  tient pour acquis en mots ordinaires : « Une étude fragile peut représenter tout le camp
  adverse ». **LE SUJET EST NOMMÉ, JAMAIS UN PRONOM** : « Ils parlent d'une voix » ou « Elles
  suivent la même logique » ne disent ni qui (quand la slide vient de nommer trois groupes) ni
  quoi ; « Les 180 lycées bloqués partagent les mêmes revendications », « Les
  entreprises répercutent toutes leurs coûts » disent les deux. Les slides 5–7 font le travail local ; la slide 8 descend d'un
  cran, elle ne résume pas.
  **TROIS TESTS, UN PAR UN, AVANT DE VALIDER UN PRÉSUPPOSÉ (impératif)** — les trois échouent
  souvent sans se voir, et le même geste les corrige : descendre d'un cran sous ce que le
  texte dit.
  1. **EST-CE NON DIT ?** Si l'article ARGUMENTE ce point, ce n'est pas un présupposé, c'est un
     résumé de sa démonstration. Un texte qui explique longuement qu'une mesure rapporte trop peu
     ne « tient pas pour acquis » qu'elle rapporte trop peu : il le soutient. Cherche l'étage en
     dessous — ce qu'il faut déjà accepter pour que cet argument compte (ici : que le prélèvement
     lui-même n'est pas en question, seul son destinataire).
  2. **LE TEXTE DIT-IL LE CONTRAIRE QUELQUE PART ?** Relis la DERNIÈRE section avant de valider :
     un présupposé démenti par la clôture est simplement faux (« qu'un patrimoine se taxe
     facilement », quand l'article termine en rappelant le débat politique que cela ouvrirait).
  3. **DE QUI EST-CE LE PRÉSUPPOSÉ ?** La slide dit ce que l'ARTICLE laisse inexaminé, jamais ce
     que suppose la position qu'il COMBAT. La prémisse de l'adversaire — celle que le texte passe
     sa longueur à démonter — appartient à un beat, pas au socle.
  **CORRESPONDANCE UN POUR UN (impératif)** : il y a EXACTEMENT autant de présupposés que de
  beats `selected`, dans le MÊME ORDRE — un par slide 5, 6, 7. Le vivier compte 6 à 8 candidats
  mais **seuls les beats retenus sont montrés au lecteur** : un présupposé fondé sur un beat
  NON sélectionné arrive sans le constat qui le porte, et la slide 8 devient un raisonnement
  sur un carrousel que personne n'a vu. Vérifie chaque présupposé un par un : sous quel beat
  RETENU se range-t-il ? Si la réponse est « aucun » ou « un candidat écarté », remplace-le
  par le présupposé du beat retenu qui n'en a pas encore. Et si un beat retenu se retrouve
  sans présupposé, c'est là qu'il en manque un.
  **TEST ANTI-RÉCAPITULATIF (impératif)** : si un présupposé peut se lire comme le résumé d'une
  slide 5–7, ce n'est pas un socle — réécris-le. Ex. de ce qu'il NE faut PAS écrire : un beat
  établit que « la moitié de la baisse ne vient d'aucune décision » → présupposé « une baisse non
  décidée ne vaut pas politique » : c'est le constat du beat, reformulé. Le vrai présupposé est
  EN DESSOUS : « l'État détient les leviers qui font baisser les émissions » — nécessaire à
  l'argument, jamais examiné par le texte. Demande-toi, pour chaque constat de beat : *pour que ce
  constat compte comme un reproche, qu'est-ce qu'il faut admettre par ailleurs ?* La réponse est
  le présupposé.
- **NON-DUPLICATION DES AXES (impératif)** : `core_recap`, `cta.engagement_sentence` et `root_issue`
  portent sur TROIS choses différentes, pas sur une même idée en trois formulations. Avant de
  valider, énonce l'axe de chacun en trois mots : si deux se ressemblent (p. ex. « engagements vs
  moyens » pour la question ET pour le `root_issue`), réécris-en un. La règle porte sur l'**AXE**,
  pas sur les mots : changer de vocabulaire ne suffit pas.
- `global_analysis` (slide 7 : la thèse `headline` est fixée à l'étape 1 ; tu écris ses présupposés) : `core_recap` (1 seul point, ≤16 mots **étiquette non comprise — compte-les avant de valider, c'est une ligne de slide, pas un paragraphe**, PRÉFIXÉ de son étiquette « Ses présupposés : » = les prémisses IMPLICITES que la thèse doit tenir pour acquises sans jamais les démontrer (`fond.implicit_assumptions`) — un présupposé PAR BEAT SÉLECTIONNÉ (voir la CORRESPONDANCE UN POUR UN ci-dessus), séparés par « ; », énoncés NEUTREMENT et de façon COMPACTE (pas de préambule « trois hypothèses… » : l'étiquette le dit déjà), qui COUVRENT les différentes dimensions de la thèse (ne ramène pas tout à un seul angle). **Chaque présupposé s'écrit comme une AFFIRMATION, SANS « que » — la slide l'introduit par « Implicitement, l'article admet : » —, en mots ordinaires, et se vérifie sur ce que le lecteur a vu** : « 54 participants suffisent à juger toutes ces études » se comprend seul et renvoie au beat 3 ; « une étude fragile peut représenter tout le camp adverse » nomme un collectif que le carrousel n'a jamais présenté, et ne veut rien dire pour qui n'a pas lu l'article. Reprends les mots déjà employés sur la slide du beat correspondant. Aucun présupposé ne doit pouvoir se lire comme le résumé d'un moment (slides 5–7) — voir le TEST ANTI-RÉCAPITULATIF ci-dessus. `core_recap` ne contient AUCUNE question : celle qui prolonge ces présupposés est `cta.engagement_sentence`, affichée une slide plus loin (slide 8, « Prise de recul »).
- `steel_man` : à partir de `analysis.fond.steel_man`, choisis l'objection qui remet le plus en cause la **thèse/conclusion** de l'article et apporte une **perspective nouvelle** que le lecteur n'a pas encore vue — PAS celle qui répète une faille statistique ou factuelle déjà pointée dans `reading_beats` (ex. « effet de base », « chiffre sans total »). Préfère un contre-argument sur les conséquences ou les valeurs (bénéfice ignoré, arbitrage négligé). Reformule-le pour le lecteur : `argument` (≤18 mots — la meilleure objection à la thèse) et `alternative` (≤14 mots — la conclusion qui suivrait si l'objection tenait). C'est le contre-argument le plus solide que l'article n'affronte pas, pas notre avis. **Les tests 2 et 3 des présupposés valent ici aussi** : une objection que le texte réfute lui-même (souvent dans sa dernière section) n'en est pas une, et une objection qui repose sur la prémisse que l'article démonte tombe à côté.
  - `steel_man.targets` : le NUMÉRO (1 à 3, dans l'ordre de la slide 7) du présupposé de `core_recap` que l'objection affaiblit — la slide relie l'objection à ce pilier par un trait. Choisis celui que l'objection rend réellement douteux (« les inégalités sont le terreau ; l'étincelle date de cette semaine » vise « Un manque ancien explique l'explosion »). 0 seulement si l'objection ne touche aucun présupposé en particulier.
  - `alternative` s'écrit **sans gras** : la ligne grise ne porte pas d'or, le doré reste sur l'objection.
  - **UNE OBJECTION RÉPOND « NON, PARCE QUE… » (impératif)** : lue sous le pilier qu'elle vise, elle doit le contredire visiblement. Deux faits juxtaposés n'en sont pas une : « Au Népal, le vote en ligne a proposé une Première ministre ; des élections sont annoncées » ne dit pas ce qu'il conteste. Écris le mot qui oppose (« n'a fait que **proposer** ») et laisse `alternative` tirer la conclusion (« la place des citoyens passe encore par **les urnes** ») — la slide l'affiche en gris sous l'argument. Si la matière est celle d'un moment, l'objection apporte la conclusion que le moment ne tire pas. **Pas de « : » dans `argument`** : la slide en ferait une ligne grise à la place d'`alternative`.
