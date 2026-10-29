# Archétypes de carrousels — singsing.media

Sept archétypes, un même contrat. Le carrousel optimisé (`instagram_carousel_optimized`, le « Grand dossier ») est la référence : les autres ne diffèrent de lui que par leurs slides intermédiaires.

## 1. Posture éditoriale

- **Outillage, pas verdict.** Chaque slide donne au lecteur un outil et un éclairage, jamais un rapport de fautes, une note ou un jugement. Ne critique jamais l'article, le journaliste ou le média.
- **Bonne foi.** Le média est une tentative rationnelle d'expliquer le monde. Pas de procès d'intention, pas de condescendance. Aucun terme accusateur (_biais_, _manipulation_, _mensonge_, _trompeur_) hors d'une citation entre « ».
- **Pas de conclusion fermée.** Des ouvertures réflexives et des mises en perspective équilibrées. Les questions posées au lecteur sont neutres et non binaires.
- **Sobriété.** Pas de superlatifs ni d'éloges (« cas d'école »). On décrit, les faits portent.
- **Deck autonome.** Aucun nom nu, acronymes développés (INSEE, IFOP, GIEC…) : un lecteur qui ne connaît pas la source comprend.
- **Indices.** Chaque réponse ou source dit où vérifier : une institution, un document, un chiffre, une personne citée.
- **Un outil de pensée critique.** C'est ce qui distingue Sing Sing. Chaque archétype nomme la question qu'il apprend au lecteur à poser (champ « Outil de pensée critique » au §3). Test : le lecteur repart-il avec une question qu'il peut vérifier, et un endroit où le faire ? Un deck qui ne fait que replacer l'article dans un contexte, sans outil de vérification, n'est pas réussi.
- **Une lentille, du contexte d'abord.** Chaque archétype lit l'article à travers une lentille (le temps, la mesure, le prisme disciplinaire, l'arbitrage…). Les premières slides après le hook fournissent le contexte dont la lentille a besoin (repères datés, méthode, positions) ; les slides suivantes, celles de pensée critique, s'en servent. Une slide critique ne doit jamais s'appuyer sur un élément que les slides précédentes n'ont pas posé.

## 2. Contrat commun

### Slide 1 — le Hook (identique pour tous, avec image de fond)

Le gabarit du carrousel optimisé (`01_hook.html`), sans variante par archétype, **ni badge** :

1. **Pastille source** or : support · durée · source · date (▶ pour un podcast ou une vidéo).
2. **Image de fond** : une photo `background.*` pleine largeur, sous une bande noire, qui s'efface vers le noir derrière le texte. À défaut, une capture `cover.*` en carte sous la pastille. Elle revient sur la dernière slide.
3. **Titre** : `sub_topic`, la formule d'accroche propre à l'archétype (voir §3), entre « » quand c'est une affirmation du média.
4. **Promesse** : une ligne de promesse, suivie de « En juger soi-même. » en or, puis « Glissez → ».

Seule la formule de la promesse varie : « Comprendre … » (Grand dossier), « Décryptage d'une prise de position sur … » (Cadrage & logique), etc.

### Dernière slide — le CTA (identique pour tous, avec image de fond)

Le gabarit `10_cta.html`, repris tel quel :

- L'image de fond de la slide 1, qui s'efface vers le noir derrière la signature : le carrousel se ferme sur l'image qui l'a ouvert.
- « On **sélectionne**. On **éclaire**. **Vous jugez.** »
- **Sauvegardez & partagez** — à relire, et à transmettre.
- **Commentez** — une relance propre au carrousel (`cta_comment`), la seule ligne qui change.
- **La newsletter** — commentez « NEWSLETTER » : nos analyses, chaque semaine.
- Signature « Sing, little bird, sing ».

### Charte visuelle

Une seule : celle du carrousel optimisé (fond noir, cartes arrondies, or `#d4aa00`, filet doré, l'oiseau sur son fil). Les archétypes ne changent ni fond ni palette ; ils se distinguent par leurs mises en page intermédiaires et leur composant signature (jauge, frise, chiffres en monospace, pastilles de prisme).

- **Trois niveaux de texte dans une carte** : le titre, la phrase qui porte l'idée (grasse), son explication (une taille en dessous). Les sources et remarques forment un quatrième niveau, petit et terne.
- **L'oiseau et le fil.** Chaque type de slide désigne son élément-clé (`data-perch`) ; `shoot.py` mesure les perchoirs et trace un fil d'or à travers le carrousel. Sur les slides 1 et N l'oiseau reste à la maison, près du logo, sans fil. Chaque archétype nomme le perchoir de ses slides.
- **Lentilles.** Les icônes et le vocabulaire des réflexes viennent de `CANONICAL_LENSES` ; aucune nouvelle couleur.

### Cadre de la source et connaissances générales

Chaque slide intermédiaire est de l'un de deux types :

- **Dans le cadre** : fidèle à la source. Chiffres tels que donnés, citations vérifiées au mot près (`quote` en français et `quote_original` pour une source étrangère).
- **Hors cadre** : repose sur les connaissances générales du modèle, formulé comme un risque ou une ouverture. Les sources y sont des organismes ou des séries à consulter, nommés, jamais une URL ni un chiffre, et marquées non vérifiées.

### Règles dures et signaux

- Règles dures (réparent une option générée, reviennent en ⚠ sur le choix de l'auteur) : plafonds de mots, format des champs (repère `valeur | libellé | comparaison` — un chiffre ou un fait court, valeur ≤9 caractères — note `source | texte` ou `remarque | texte`, levier `titre | détail`), aucun terme accusateur hors « », 4 hashtags.
- Signaux éditoriaux (conseils) : un chiffre absent du texte source en chiffres, une réponse sans indice de vérification.
- La légende : 150 mots environ, sans parti pris, une relance vers le débat, 4 hashtags neutres. Les sources de la dernière slide sont ajoutées à la légende (`caption_with_sources()`). Elle suit la dernière étape sans pause.

### Chaîne technique

Tous les formats partent de la même `analyze` (`ArticleFullAnalysis`) ; chaque adapt n'en lit que sa tranche. Chaque archétype ajoute :

- une entrée dans `FORMATS` (`extractors/registry.py`) : agent d'adaptation, extracteur, rendu ;
- un modèle de présentation, et son module d'étapes guidées (`agent/carousel_steps` est lié au carrousel de 9 slides) ;
- des étapes **dans l'ordre des slides**, le hook en dernier, la légende ensuite sans pause ; chaque étape propose plusieurs options avec une raison (↳) et une recommandée (★) ; `choose --pick/--edit/--more` et `fix` ;
- le dossier de sortie `<stem>/<format>/` avec `choices.jsonl`.

## 3. Répertoire des archétypes

À chaque média source, choisis **LE format le plus adapté** (en évitant de répéter le même d'un carrousel à l'autre). Aujourd'hui le choix est manuel (`produce --format …`).

### Archétype 1 : `grand_dossier` — le carrousel optimisé (9 slides)

- **Sujet :** enquêtes, documentaires, rapports de fond, dossiers complets.
- **Lentille :** les lentilles canoniques (`CANONICAL_LENSES`).
- **Contexte :** En bref, À savoir. **Critique :** les 3 moments, le socle, la prise de recul.
- **Outil de pensée critique :** à travers quelle lentille chaque affirmation est-elle lue ? (les réflexes)
- **Réalisé :** `instagram_carousel_optimized`, décrit dans le `CLAUDE.md`. Hook → En bref (chapeau et 3 idées-clés) → À savoir, à se demander (repères et réflexes) → 3 moments (un réflexe chacun) → Le socle de l'argument (thèse, présupposés, objection) → Prise de recul (enjeu de fond, « La question », où chercher) → CTA.
- **Principe :** la slide « Prise de recul » est écrite en premier et tout y mène (rétro-ingénierie : de l'enjeu systémique vers l'accroche).
- **Promesse :** « Comprendre … ».
- **Perchoirs :** carte des idées-clés, carte des réflexes, la question de chaque moment, le pilier visé, la carte de l'enjeu.

### Archétype 2 : `le_dilemme` (6 slides)

- **Sujet :** arbitrages où deux exigences légitimes s'opposent (liberté et sécurité…), sans thèse d'auteur.
- **Lentille :** l'arbitrage.
- **Contexte :** slides 2–3 (le cas de chaque exigence). **Critique :** slides 4–5.
- **Outil de pensée critique :** quelle variable unique les deux camps règlent-ils différemment ?
- **Slide 1 :** Hook, titre = le dilemme en une phrase. Promesse « Un arbitrage à comprendre : … ».
- **Slide 2 :** L'exigence A — arguments et légitimité (dans le cadre si le média les expose).
- **Slide 3 :** L'exigence B — idem.
- **Slide 4 :** Le nœud — pourquoi maximiser A et B en même temps est impossible : une seule variable, dont les deux réglages défendables s'opposent. Hors cadre.
- **Slide 5 :** La boussole — le composant de Cadrage & logique : une jauge à curseur et deux questions côte à côte, deux positions **d'une même variable** (jamais deux valeurs), chacune avec un pour ✓ et un contre ✕. Question finale neutre, non binaire, jamais « quel sacrifice assumer ».
- **Slide 6 :** CTA.
- **Étapes :** nœud, exigence A, exigence B, boussole, hook.
- **Perchoirs :** le point de tension du nœud, le curseur de la boussole (sans fil).
- **Distinction avec Cadrage :** pas de thèse portée par un auteur, une tension symétrique.

### Archétype 3 : `anatomie_chiffre` (5 slides)

- **Sujet :** sondages, statistiques, classements, pourcentages marquants.
- **Lentille :** la mesure.
- **Contexte :** slides 2–3 (la boîte noire, ce que le chiffre établit). **Critique :** slide 4.
- **Outil de pensée critique :** comment ce chiffre a-t-il été mesuré, et que laisse-t-il de côté ?
- **Slide 1 :** Hook, titre = le chiffre brut entre « ». Il ne peut pas être isolé en grand : la slide 1 reste identique pour tous.
- **Slide 2 :** La boîte noire — méthode, échantillon, questions posées, seuils, en monospace (`valeur | libellé | comparaison`). Dans le cadre : si le texte ne le dit pas, on écrit « non précisé » plutôt que d'inventer.
- **Slide 3 :** La zone d'éclairage — ce que le chiffre établit solidement et son utilité.
- **Slide 4 :** Le périmètre exclu — ce que cette mesure ne peut pas capter (effet de moyenne, déclaratif…), avec les organismes ou séries à consulter pour une mesure complémentaire. Hors cadre : aucun chiffre ajouté.
- **Slide 5 :** CTA.
- **Étapes :** périmètre exclu (noyau), boîte noire, zone d'éclairage, hook.
- **Signal :** un chiffre cité qui n'apparaît pas en chiffres dans la source est signalé.
- **Lentille :** l'exigence quantitative de `CANONICAL_LENSES` ; perchoir : la carte du chiffre.

### Archétype 4 : `temps_long` (5 slides)

- **Sujet :** faits divers, polémiques à chaud, déclarations politiques de la veille.
- **Lentille :** le temps.
- **Outil de pensée critique :** rupture, continuité ou cycle ? Une affirmation sur l'actualité (« inédit », « glissement », « dérive ») suppose une hypothèse temporelle, et chaque hypothèse prédit autre chose dans les données ; les repères datés des slides 2–3 disent où regarder pour savoir laquelle elles soutiennent.
- **Slide 1 :** Hook, titre = le fait brut daté. L'écume (la réaction médiatique) y est absorbée : le hook la nomme déjà. Promesse « Prendre du recul sur … ».
- **Slide 2 :** Le palier décennal — un tournant sur 10 à 15 ans, en **repères datés** (lois, ruptures, séries à consulter), jamais une tendance chiffrée. Présentés comme des épisodes candidats à la comparaison, sans affirmer qu'ils sont de même nature que l'actualité. Contexte de la slide 4. Hors cadre.
- **Slide 3 :** La vague de fond — une mutation de 50 ans (démographique, technique, culturelle), en repères datés, même statut. Contexte de la slide 4. Hors cadre.
- **Slide 4 :** Rupture, continuité ou cycle ? — la slide de pensée critique, qui s'appuie sur les repères des slides 2–3. Un même constat se lit de trois façons, et chacune prédit autre chose dans les séries : **rupture** (une cassure nette par rapport aux épisodes précédents sur la même mesure), **continuité** (une évolution progressive, dans le même sens, d'un repère au suivant), **cycle** (des pics à chaque mobilisation, puis un retour au niveau antérieur). Un tableau « lecture / ce qu'elle donnerait dans les séries / où regarder », la dernière colonne renvoyant aux repères des slides 2–3 et à des organismes ou séries à consulter. Une ligne place le vocabulaire du média (« inédit » suppose la rupture, « glissement » la continuité) sans le juger : les trois lectures restent à tester. Méthode générale, hors cadre ; les mots cités sont dans le cadre, entre « ». Aucun chiffre sur le cas traité. Clôture par une question neutre : quelle lecture les séries que vous trouverez soutiennent-elles ?
- **Slide 5 :** CTA, la relance reprend cette question.
- **Étapes :** vague de fond (noyau), palier, lecture temporelle (rupture, continuité, cycle), hook.
- **Visuel :** une frise verticale fine, dates en or ; l'oiseau se perche sur les dates. La slide 4 est un tableau à trois lignes, une par lecture.
- **Risques nommés :** les chiffres de long terme sont ceux que le modèle invente le plus volontiers ; sans donnée fournie par l'auteur, on s'en tient aux repères datés. Et un rapprochement n'est pas une explication : aucune formule du type « c'est la suite de … » ; le deck propose des comparaisons à vérifier, pas un récit. Si le média ne formule aucune affirmation temporelle, `temps_long` est un mauvais choix.

### Archétype 5 : `trois_regards` (6 slides)

- **Sujet :** phénomènes de société globaux abordés sous un seul prisme.
- **Lentille :** la discipline.
- **Contexte :** le regard du média (le prisme qu'il emploie, repéré sur l'un des prismes) et la question à laquelle il répond (ouverture de la matrice). **Critique :** les prismes et la matrice.
- **Outil de pensée critique :** la réponse change-t-elle selon la discipline qu'on convoque ?
- **Slide 1 :** Hook, titre = l'objet d'étude en termes neutres. Promesse « Trois façons de regarder … ».
- **Slides 2–4 :** trois prismes — économique (incitations, rareté, coûts cachés), sociologique (normes, statut, lien social), juridique ou historique (cadre légal, précédents, institutions). Chacun : ce que ce prisme éclaire (jamais « ce que l'article oublie »), avec ses sources à consulter. Hors cadre. Celui que le média emploie lui-même porte un repère « Le regard du média » (une phrase, dans le cadre). Un prisme porte l'icône de sa lentille, sans nouvelle couleur.
- **Slide 5 :** La matrice croisée — ouverte par la question à laquelle le média répond (dans le cadre) ; la réponse change selon le prisme priorisé : trois colonnes côte à côte.
- **Slide 6 :** CTA, la relance porte sur la pondération entre les prismes.
- **Étapes :** matrice (noyau, avec la question à laquelle le média répond), prismes (dont le repère « Le regard du média »), hook.
- **Perchoirs :** le titre de chaque prisme.

### Archétype 6 : `cadrage_logique` (7 slides) — réalisé

- **Sujet :** tribunes, essais, éditoriaux, grands entretiens d'idées.
- **Lentille :** le risque d'une solution.
- **Contexte :** slides 2–3 (le constat, la thèse, dans le cadre). **Critique :** slides 4–6.
- **Outil de pensée critique :** que risque la solution proposée, et quel arbitrage reste à faire ?
- **Slide 1 :** Hook ; titre = l'affirmation centrale du média entre « » ; promesse « Décryptage d'une prise de position sur … ».
- **Slide 2 :** Le constat — les chiffres ou faits courts du média, en monospace, et ce qu'ils établissent. Dans le cadre.
- **Slide 3 :** La thèse — ce que le média conclut, la solution proposée, une remarque ou une source dessous. Dans le cadre.
- **Slide 4 :** L'angle mort — ce que la solution risque, en une formule percutante : une première carte pour la régularité et une seconde pour un autre angle mort (jamais une reformulation). Hors cadre.
- **Slide 5 :** Le dépassement — trois leviers qui atténuent le risque (« atténuer », jamais « sans ») et ont un coût ; au moins un agit sur le comment de la décision. Hors cadre.
- **Slide 6 :** La boussole — jauge, deux questions, pour et contre de chacune.
- **Slide 7 :** CTA.
- **Étapes :** axe (l'arbitrage vers lequel tout est écrit, jamais affiché), constat, thèse, angle mort, dépassement, boussole, hook ; légende ensuite. `check` ne couvre pas ce format.
- **Perchoirs :** slides 2–5 (le fil les traverse) et le curseur de la boussole (sans fil).

### Archétype 7 : `la_causalite` (6 slides) — à réaliser

- **Sujet :** études, enquêtes, articles de santé, d'éducation ou de société qui affirment un lien de cause à effet (« provoque », « à cause de », « responsable de », « grâce à »).
- **Lentille :** la causalité.
- **Contexte :** slides 2–3 (le lien affirmé, la preuve avancée, dans le cadre). **Critique :** slides 4–5.
- **Outil de pensée critique :** corrélation ou cause ? Quelles autres explications sont possibles, dans quel sens va le lien, et qu'est-ce qui l'établirait ?
- **Slide 1 :** Hook, titre = le lien affirmé par le média, entre « ». Promesse « Examiner un lien de cause à effet : … ».
- **Slide 2 :** Le lien affirmé — ce que le média relie à quoi (X, Y), le mécanisme qu'il propose, les chiffres tels que donnés. Dans le cadre.
- **Slide 3 :** La preuve avancée — ce sur quoi repose le lien : type de preuve (observation, comparaison, essai, témoignage), échantillon, groupe de comparaison, durée, en monospace (`valeur | libellé | comparaison`). Dans le cadre : si le texte ne le dit pas, on écrit « non précisé » plutôt que d'inventer.
- **Slide 4 :** Les autres explications — trois lectures possibles d'une même corrélation : le sens inverse (Y précède X), un facteur commun (Z agit sur les deux), le hasard ou la sélection de l'échantillon. Chacune formulée comme une possibilité à écarter, jamais comme un reproche fait à l'étude ; avec, pour chacune, où regarder. Hors cadre : aucun chiffre ajouté.
- **Slide 5 :** Ce qui établirait le lien — les preuves qui renforcent une conclusion causale (groupe témoin, avant/après une intervention, effet qui croît avec la dose, expérience naturelle, essai randomisé), avec celles que la source fournit (renvoi à la slide 3) et les organismes ou séries où les chercher. Hors cadre. Clôture par une question neutre : quelle preuve vous ferait changer d'avis, dans un sens ou dans l'autre ?
- **Slide 6 :** CTA, la relance reprend cette question.
- **Étapes :** autres explications (noyau), lien, preuve, ce qui établirait le lien, hook.
- **Visuel :** un petit schéma de flèches. La slide 4 montre X → Y et, en regard, les trois lectures (Y → X, Z → X et Y, hasard) ; l'oiseau se perche sur la flèche de la lecture lue. Slide 3 en monospace, comme `anatomie_chiffre`.
- **Distinction avec `anatomie_chiffre` :** celui-ci interroge la mesure (comment le chiffre a-t-il été obtenu ?), celui-là le lien (le chiffre prouve-t-il une cause ?).
- **Risques nommés :** (1) jamais « l'étude est faible » ni « le média confond » : le deck dit ce qu'il faudrait pour établir le lien, pas que la source échoue ; (2) il ne conclut ni à la cause ni à son absence ; (3) le modèle invente volontiers des détails d'étude (échantillon, méthode) : sans donnée dans la source, « non précisé » ; (4) si la source est elle-même un essai randomisé, les slides 4–5 changent de ton (limites de généralisation) et le choix de l'archétype est à revoir.

## 4. Arbre de décision

Ne regarde pas le sujet (écologie, économie, justice) mais la nature de la matière première : où est la friction principale du texte ?

```
1. L'article repose-t-il sur une mesure chiffrée, un sondage ou un classement ?
   ├─ OUI ──> anatomie_chiffre
   └─ NON ──> Question 2

2. Le média réagit-il à un fait immédiat, une polémique à chaud, une émotion vive ?
   ├─ OUI ──> temps_long
   └─ NON ──> Question 3

3. Quelle est la structure de l'argumentation ?
   ├─ Une thèse d'auteur, avec une recommandation forte ──> cadrage_logique
   ├─ Un arbitrage entre deux exigences respectables, sans thèse ──> le_dilemme
   ├─ Un phénomène de société complexe réduit à un seul prisme ──> trois_regards
   ├─ Un lien de cause à effet affirmé (« provoque », « à cause de ») ──> la_causalite
   └─ Une enquête d'envergure, dense, multi-dimensionnelle ──> grand_dossier
```

### Signaux par format

| Format | Indices dans le texte | Matière première | Test mental |
|---|---|---|---|
| `anatomie_chiffre` | Titre contenant un pourcentage, une somme, un classement (« 64 % des Français… ») | Étude, sondage IFOP/OpinionWay, rapport de l'Insee | Sans le chiffre, l'article perd-il sa raison d'être ? |
| `temps_long` | Vocabulaire de l'urgence ou du choc (« historique », « inédit ») ; affirmation de nouveauté, de tendance ou de retour (« glissement », « dérive ») sans série à l'appui ; fait divers ou déclaration de la veille | Dépêche AFP, couverture à chaud, réactions en chaîne | L'article affirme-t-il une nouveauté, une tendance ou un retour sans le montrer ? |
| `cadrage_logique` | Verbes prescriptifs (« il faut », « nous devons »), première personne, signature d'un essayiste | Tribune, billet d'opinion, éditorial, chronique, grand entretien | L'auteur recommande-t-il une solution dont on peut nommer le risque ? |
| `le_dilemme` | « D'un côté / de l'autre », « sécurité ou liberté », controverses éthiques | Arbitrages de politique publique, bioéthique, régulation | Les deux camps ont-ils des arguments parfaitement défendables ? |
| `trois_regards` | Sujet systémique massif (logement, IA, natalité) traité sous un angle émotionnel ou anecdotique | Témoignages, articles « tendances », dossiers généralistes | Une seule discipline est-elle convoquée pour un problème complexe ? |
| `la_causalite` | « Provoque », « à cause de », « responsable de », « grâce à », « conduit à » ; titre qui promet un effet | Étude observationnelle, rapport, article de santé, d'éducation ou de société | Le lien de cause à effet est-il affirmé plus fort que la preuve fournie ? |
| `grand_dossier` | Plus de 2 000 mots, multiples sources, documents, calendrier long | Enquête d'investigation, rapport de la Cour des comptes ou du GIEC, livre-enquête | Le document est-il trop dense pour tenir dans une citation ou un graphique ? |

### En cas d'hésitation

Quand un article coche plusieurs cases (une tribune qui s'appuie sur une statistique) : si le chiffre n'est qu'un moyen au service d'une vision du monde, `cadrage_logique` ; si le chiffre fait lui-même débat (représentativité, mode de calcul), `anatomie_chiffre` ; si le débat porte sur ce que le chiffre prouverait (une corrélation présentée comme une cause), `la_causalite`.
