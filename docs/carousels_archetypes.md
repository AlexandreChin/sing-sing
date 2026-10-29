# Archétypes de carrousels — singsing.media

Six archétypes, un même contrat. Le carrousel optimisé (`instagram_carousel_optimized`, le « Grand dossier ») est la référence : les autres ne diffèrent de lui que par leurs slides intermédiaires.

## 1. Posture éditoriale

- **Outillage, pas verdict.** Chaque slide donne au lecteur un outil et un éclairage, jamais un rapport de fautes, une note ou un jugement. Ne critique jamais l'article, le journaliste ou le média.
- **Bonne foi.** Le média est une tentative rationnelle d'expliquer le monde. Pas de procès d'intention, pas de condescendance. Aucun terme accusateur (_biais_, _manipulation_, _mensonge_, _trompeur_) hors d'une citation entre « ».
- **Pas de conclusion fermée.** Des ouvertures réflexives et des mises en perspective équilibrées. Les questions posées au lecteur sont neutres et non binaires.
- **Sobriété.** Pas de superlatifs ni d'éloges (« cas d'école »). On décrit, les faits portent.
- **Deck autonome.** Aucun nom nu, acronymes développés (INSEE, IFOP, GIEC…) : un lecteur qui ne connaît pas la source comprend.
- **Indices.** Chaque réponse ou source dit où vérifier : une institution, un document, un chiffre, une personne citée.

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
- **Réalisé :** `instagram_carousel_optimized`, décrit dans le `CLAUDE.md`. Hook → En bref (chapeau et 3 idées-clés) → À savoir, à se demander (repères et réflexes) → 3 moments (un réflexe chacun) → Le socle de l'argument (thèse, présupposés, objection) → Prise de recul (enjeu de fond, « La question », où chercher) → CTA.
- **Principe :** la slide « Prise de recul » est écrite en premier et tout y mène (rétro-ingénierie : de l'enjeu systémique vers l'accroche).
- **Promesse :** « Comprendre … ».
- **Perchoirs :** carte des idées-clés, carte des réflexes, la question de chaque moment, le pilier visé, la carte de l'enjeu.

### Archétype 2 : `le_dilemme` (6 slides)

- **Sujet :** arbitrages où deux exigences légitimes s'opposent (liberté et sécurité…), sans thèse d'auteur.
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
- **Slide 1 :** Hook, titre = le fait brut daté. L'écume (la réaction médiatique) y est absorbée : le hook la nomme déjà. Promesse « Prendre du recul sur … ».
- **Slide 2 :** Le palier décennal — un tournant sur 10 à 15 ans, en **repères datés** (lois, ruptures, séries à consulter), jamais une tendance chiffrée. Hors cadre.
- **Slide 3 :** La vague de fond — une mutation de 50 ans (démographique, technique, culturelle), en repères datés. Hors cadre.
- **Slide 4 :** Le raccordement — comment l'actualité du jour découle de ces mouvements. Formulé comme une lecture possible, non comme une explication établie.
- **Slide 5 :** CTA.
- **Étapes :** vague de fond (noyau), palier, raccordement, hook.
- **Visuel :** une frise verticale fine, dates en or ; l'oiseau se perche sur les dates.
- **Risque nommé :** les chiffres de long terme sont ceux que le modèle invente le plus volontiers ; sans donnée fournie par l'auteur, on s'en tient aux repères datés.

### Archétype 5 : `trois_regards` (6 slides)

- **Sujet :** phénomènes de société globaux abordés sous un seul prisme.
- **Slide 1 :** Hook, titre = l'objet d'étude en termes neutres. Promesse « Trois façons de regarder … ».
- **Slides 2–4 :** trois prismes — économique (incitations, rareté, coûts cachés), sociologique (normes, statut, lien social), juridique ou historique (cadre légal, précédents, institutions). Chacun : ce que ce prisme éclaire (jamais « ce que l'article oublie »), avec ses sources à consulter. Hors cadre. Un prisme porte l'icône de sa lentille, sans nouvelle couleur.
- **Slide 5 :** La matrice croisée — la réponse change selon le prisme priorisé : trois colonnes côte à côte.
- **Slide 6 :** CTA, la relance porte sur la pondération entre les prismes.
- **Étapes :** matrice (noyau), prismes, hook.
- **Perchoirs :** le titre de chaque prisme.

### Archétype 6 : `cadrage_logique` (7 slides) — réalisé

- **Sujet :** tribunes, essais, éditoriaux, grands entretiens d'idées.
- **Slide 1 :** Hook ; titre = l'affirmation centrale du média entre « » ; promesse « Décryptage d'une prise de position sur … ».
- **Slide 2 :** Le constat — les chiffres ou faits courts du média, en monospace, et ce qu'ils établissent. Dans le cadre.
- **Slide 3 :** La thèse — ce que le média conclut, la solution proposée, une remarque ou une source dessous. Dans le cadre.
- **Slide 4 :** L'angle mort — ce que la solution risque, en une formule percutante : une première carte pour la régularité et une seconde pour un autre angle mort (jamais une reformulation). Hors cadre.
- **Slide 5 :** Le dépassement — trois leviers qui atténuent le risque (« atténuer », jamais « sans ») et ont un coût ; au moins un agit sur le comment de la décision. Hors cadre.
- **Slide 6 :** La boussole — jauge, deux questions, pour et contre de chacune.
- **Slide 7 :** CTA.
- **Étapes :** axe (l'arbitrage vers lequel tout est écrit, jamais affiché), constat, thèse, angle mort, dépassement, boussole, hook ; légende ensuite. `check` ne couvre pas ce format.
- **Perchoirs :** slides 2–5 (le fil les traverse) et le curseur de la boussole (sans fil).

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
   └─ Une enquête d'envergure, dense, multi-dimensionnelle ──> grand_dossier
```

### Signaux par format

| Format | Indices dans le texte | Matière première | Test mental |
|---|---|---|---|
| `anatomie_chiffre` | Titre contenant un pourcentage, une somme, un classement (« 64 % des Français… ») | Étude, sondage IFOP/OpinionWay, rapport de l'Insee | Sans le chiffre, l'article perd-il sa raison d'être ? |
| `temps_long` | Vocabulaire de l'urgence ou du choc (« historique », « inédit ») ; fait divers ou déclaration de la veille | Dépêche AFP, couverture à chaud, réactions en chaîne | Aura-t-on oublié les détails dans six mois si l'on ne comprend pas la tendance de fond ? |
| `cadrage_logique` | Verbes prescriptifs (« il faut », « nous devons »), première personne, signature d'un essayiste | Tribune, billet d'opinion, éditorial, chronique, grand entretien | L'auteur recommande-t-il une solution dont on peut nommer le risque ? |
| `le_dilemme` | « D'un côté / de l'autre », « sécurité ou liberté », controverses éthiques | Arbitrages de politique publique, bioéthique, régulation | Les deux camps ont-ils des arguments parfaitement défendables ? |
| `trois_regards` | Sujet systémique massif (logement, IA, natalité) traité sous un angle émotionnel ou anecdotique | Témoignages, articles « tendances », dossiers généralistes | Une seule discipline est-elle convoquée pour un problème complexe ? |
| `grand_dossier` | Plus de 2 000 mots, multiples sources, documents, calendrier long | Enquête d'investigation, rapport de la Cour des comptes ou du GIEC, livre-enquête | Le document est-il trop dense pour tenir dans une citation ou un graphique ? |

### En cas d'hésitation

Quand un article coche plusieurs cases (une tribune qui s'appuie sur une statistique) : si le chiffre n'est qu'un moyen au service d'une vision du monde, `cadrage_logique` ; si le chiffre fait lui-même débat (représentativité, mode de calcul), `anatomie_chiffre`.
