ÉTAPE 1 — L'AXE (jamais affiché)

Avant toute autre chose, tu fixes la question du carrousel, la question plus étroite que l'article traite, le sujet, les trois prismes et lequel est celui du média. L'axe n'est écrit sur aucune slide : il est le contexte fixe de toutes les étapes suivantes, qui l'écrivent POUR lui. Tu proposes 3 ou 4 options ; elles sont des JEUX DE PRISMES différents (deux options ne partagent pas les mêmes trois prismes ; le prisme du média, lui, peut revenir : il fait toujours partie du jeu).

- `question` (**≤{{cap:axe.question}} caractères**, finit par « ? ») : la question large du carrousel, qui sera le titre de l'accroche. Chacun des trois prismes doit pouvoir y répondre à sa façon : « D'où vient … ? », « Qu'est-ce qui explique … ? ». Elle nomme le sujet, jamais une réponse, et n'est PAS la question de l'article, plus étroite. Pas de « » (ce n'est pas une citation). Aucun chiffre, sauf une année ou une date. Elle n'est écrite que sur l'accroche : les slides suivantes ne la répètent pas, elles y répondent.
- `article_question` : la question, plus étroite, à laquelle l'article répond réellement (« Comment un village vit-il le départ de son dernier médecin ? »). C'est ce que la slide de la position dira ; elle sert à ce que le lecteur voie ce que l'article couvre de la grande question.
- `subject` (**≤{{cap:axe.subject}} caractères**) : le sujet en groupe nominal court, avec son article (« les déserts médicaux »), tel qu'il se lira dans « Trois regards sur <sujet> ; à vous d'en juger. ». Pas de point final, pas de question.
- `prism1`, `prism2`, `prism3` : trois identifiants DISTINCTS pris dans le CATALOGUE DES PRISMES (économique s'écrit `economique`, sans accent). Choisis des prismes dont les réponses à la question diffèrent vraiment ; ne prends pas trois façons de dire la même chose.
- `media` : l'identifiant du prisme que l'article emploie lui-même (celui qui organise son récit et ses causes), obligatoirement l'un des trois.
- `media_grounding` (**≤{{cap:axe.media_grounding}} caractères**) : UNE phrase qui ancre ce choix dans l'article, avec ses éléments (qui est cité, ce qu'il décrit). Si aucun prisme ne domine nettement, prends le plus proche ET dis-le dans cette phrase (« Aucun prisme ne domine ; le plus proche est … »).
- `closing` (**≤{{cap:axe.closing}} caractères**) : la question finale, voir le cadre commun : minuscules après « Commentez — », elle invite le lecteur à dire ce qui manque encore pour comprendre le sujet (« que manque-t-il pour comprendre … ? »), nomme les trois prismes, garde un mot clé de la question, reste ouverte, finit par « ? ». Jamais « quel regard éclaire le mieux … ? » : le carrousel ne classe pas les regards.
- `reason` : pourquoi ce jeu de prismes éclaire la question, et pourquoi le prisme du média est celui-là.

Recommande le jeu dont les trois prismes donnent les réponses les plus différentes à la question ET dont le prisme du média est le mieux ancré dans l'article.

Exemple (un reportage sur un village qui perd son dernier médecin généraliste) :
- `question` : « D'où viennent les déserts médicaux en France ? »
- `article_question` : « Comment un village vit-il le départ de son dernier médecin ? »
- `subject` : « les déserts médicaux »
- `prism1` : `sociologique`
- `prism2` : `economique`
- `prism3` : `historique`
- `media` : `sociologique`
- `media_grounding` : « Le reportage suit les patients du village et leur médecin, leurs trajets et leurs choix de vie. »
- `closing` : « entre le sociologique, l'économique et l'historique, que manque-t-il pour comprendre les déserts médicaux ? »
- `reason` : « Le récit est sociologique ; l'économie (revenus, coûts) et l'histoire (la formation des médecins) répondent autrement. »
