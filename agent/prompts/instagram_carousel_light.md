VERSION LÉGÈRE DU CARROUSEL

Le carrousel complet est fourni ci-dessus (JSON). Produis sa VERSION LÉGÈRE : les mêmes 9 slides, le même angle, les mêmes trois moments, le même enjeu et la même question — seuls les mots changent. Chaque slide doit se lire en 3 à 5 secondes dans un fil. Tu ne choisis rien de neuf : tu CONDENSES. Ce qui disparaît reste dans la légende et la newsletter.

**Règles générales (impératif)**
- Même sens, même force, même attribution : condenser n'est pas trancher. Pas de mot plus fort que la version complète, pas de verdict ; les moments restent des OUTILS de lecture.
- Phrases ordinaires, en français courant ; une idée par ligne. Pas de sigle non développé.
- Garde le **gras** (doré) sur 1 mot clé par champ, comme dans la version complète.
- **L'axe** : l'accroche, chacune des 3 idées, le titre du socle, et la question OU la réponse de chaque moment reprennent au moins un mot-clé (même racine) de l'enjeu ou de la question de la slide 8.

**Champs et plafonds**
- `hook_sub_topic` : l'accroche, ≤40 caractères. Elle nomme le sujet ; pas de « Derrière… ».
- `hook_subtitle` : « Comprendre … », ≤38 caractères (la slide ajoute « En juger soi-même. »).
- `essentiel` : les 3 idées de la version complète, dans le même ordre, chacune écrite « affirmation : détail » — la slide affiche l'affirmation en blanc (≤30 caractères, une ligne, le mot doré dedans) et le détail en gris dessous (≤45 caractères). Ex. « On montre des **casseurs** : quelques violences pour toute la révolte ». Chacune se comprend seule (pas de « Ce récit » qui renvoie à la précédente).
- `reperes_fact` : UN seul repère (`label` 1–2 mots, `text` ≤10 mots), celui sans lequel le lecteur se tromperait sur la source ou le contexte.
- `moments` : un objet par moment SÉLECTIONNÉ de la version complète, avec son `index` dans `reading_beats` :
  - `moment` : le titre, ≤45 caractères — ce que le passage fait, lisible seul.
  - `quote` / `quote_original` : un extrait PLUS COURT du même passage, ≤12 mots. `quote_original` reste MOT POUR MOT celui de l'article (élision « […] » permise) ; `quote` en est la traduction française fidèle si l'article n'est pas en français (sinon `quote_original` vide).
  - `lens_question` : la question du réflexe, ≤70 caractères — et les trois questions ensemble ≤120 caractères : la slide 3 n'en tient qu'UNE sur deux lignes, les autres courtes — compréhensible sur la slide 3 AVANT d'avoir vu le moment — jamais un pronom sans antécédent (« Pourquoi eux ? » ne dit pas qui).
  - `answer` : ≤110 caractères. **ELLE DIT OÙ REGARDER (impératif)** : une institution, un document, un chiffre, une personne citée dans l'article — « **Des déclarations** : à relire au compte rendu de l'Assemblée », « **L'Union étudiante** compare Sciences Po et la Seine-Saint-Denis : vérifiez auprès des préfectures ». Jamais une consigne nue (« **Comparez** les arrestations d'un lycée à l'autre » dit quoi faire, pas où).
- `headline` : la thèse du socle, ≤45 caractères (deux lignes).
- `presupposes` : les 3 présupposés, ≤10 mots chacun, chacun commençant par « que ».
- `objection` : ≤100 caractères (trois lignes), concrète et appuyée sur l'article — jamais une hypothèse en « si ».
- `root_issue` : l'enjeu de fond, ≤60 caractères — il garde le mot doré qu'il partage avec la question.
- `question` : « La question » de la version complète, CONDENSÉE et non remplacée : même sens, même mot doré (contrôlé), ≤60 caractères, ouverte, neutre.
- `where_to_look` : 1 ou 2 sources de la version complète, chacune nommée (qui la publie, quel document), ≤48 caractères (une ligne).
