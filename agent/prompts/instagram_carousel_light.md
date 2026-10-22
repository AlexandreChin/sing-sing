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
- `reperes_fact` : UN seul repère (`label` 1–2 mots, `text` ≤10 mots, écrit « affirmation : détail » comme les idées clés), celui sans lequel le lecteur se tromperait sur la source ou le contexte. Un repère sur la source elle-même dit sa nature et sa ligne (ce qu'elle couvre, et comment) — jamais une fiche d'identité ni une étiquette politique non sourcée.
- `moments` : un objet par moment SÉLECTIONNÉ de la version complète, avec son `index` dans `reading_beats` :
  - `moment` : le titre, ≤45 caractères — ce que le passage fait, lisible seul.
  - `quote` / `quote_original` : un extrait du même passage, ≤90 caractères (trois lignes), qui dit DE QUOI il parle (« une sorte de première mondiale » seul ne dit pas quoi). N'ouvre pas sur « […] » si la phrase entière tient. `quote_original` reste MOT POUR MOT celui de l'article (élision « […] » permise) ; `quote` en est la traduction française fidèle si l'article n'est pas en français (sinon `quote_original` vide).
  - `lens_question` : la question du réflexe, ≤70 caractères — et les trois questions ensemble ≤120 caractères : la slide 3 n'en tient qu'UNE sur deux lignes, les autres courtes — compréhensible sur la slide 3 AVANT d'avoir vu le moment — jamais un pronom sans antécédent (« Pourquoi eux ? » ne dit pas qui).
  - **UN MOMENT ENTRAÎNE UN JUGEMENT (impératif)** : la question vaut pour n'importe quel article (« La casse annule-t-elle les demandes ? » se pose devant toute mobilisation), et la réponse s'écrit « **méthode** : où l'appliquer » — l'affirmation donne le TEST (compter, comparer des cas semblables, remonter l'historique, séparer le fait de l'interprétation, appliquer la même règle ailleurs), le détail gris la source où le faire. Modèles : « **Comptez**, puis séparez les actes de la cause : 400 000 manifestants, 1 500 dossiers, selon l'article » ; « **Un témoignage indique, une comparaison prouve** : l'enquête de 2017 du Défenseur des droits en offre une ». Interdit : une réponse qui donne seulement une information (une date, une source) sans dire quoi en faire.
  - `answer` : écrite « constat : où regarder » — la slide affiche le constat en blanc (≤70 caractères) et la source en gris dessous (≤55). **ELLE DIT OÙ REGARDER (impératif)** : une institution, un document, un chiffre, une personne citée dans l'article — « **Des déclarations** : à relire au compte rendu de l'Assemblée », « **L'Union étudiante** compare Sciences Po et la Seine-Saint-Denis : vérifiez auprès des préfectures ». Jamais une consigne nue (« **Comparez** les arrestations d'un lycée à l'autre » dit quoi faire, pas où).
- `headline` : la thèse du socle, ≤45 caractères (deux lignes).
- `presupposes` : les 3 présupposés, ≤10 mots chacun, chacun commençant par « que ».
- `objection` : ≤100 caractères (trois lignes), concrète et appuyée sur l'article — jamais une hypothèse en « si ». Lue sous le présupposé qu'elle vise, elle dit « non, parce que… » (« n'a fait que **proposer** »), pas deux faits côte à côte ; sans « : » — la slide affiche la conclusion de la version complète en gris dessous.
- `root_issue` : l'enjeu de fond, écrit « affirmation : détail » (affirmation ≤70 caractères, détail gris ≤55) — il garde le mot doré qu'il partage avec la question.
- `question` : « La question » de la version complète, reprise MOT POUR MOT si elle tient en ≤70 caractères ; sinon CONDENSÉE et non remplacée : même sens — une préposition suffit à le changer (« dans le pouvoir » ≠ « au pouvoir ») —, même mot doré (contrôlé), ouverte, neutre.
- `where_to_look` : 1 ou 2 sources de la version complète, chacune nommée (qui la publie, quel document), ≤48 caractères (une ligne).
