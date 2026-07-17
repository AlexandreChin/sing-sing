# Étape 10 — Éléments centraux de l'article

À partir de l'ARTICLE et du matériel factuel extrait (citations clés, faits, observations,
affirmations, biais), identifie les **3 à 5 éléments les plus centraux** de l'article :
ce dont l'article **parle fondamentalement**, ce qu'il **défend** ou ce qui l'**inquiète**.

Règles :
- Classe par **centralité à l'article** (`centrality` de 1 à 5) — la place et le poids que
  l'article y consacre. **Ignore le titre** : ne privilégie PAS l'angle du titre, ne te laisse
  pas guider par lui. Un élément très présent dans le corps mais absent du titre doit ressortir.
- **Diversité THÉMATIQUE obligatoire** — chaque élément doit porter sur une préoccupation
  **distincte**. N'inclus PAS deux variantes d'un même thème (p. ex. deux statistiques, ou
  « bilan carbone » ET « croissance chiffrée » qui relèvent tous deux des chiffres) : fusionne-les
  en un seul, et libère la place pour les **autres préoccupations** de l'article.
- Passe en revue les **différents types d'impact/enjeu** que l'article soulève et fais-les
  ressortir s'ils sont présents : impact climatique (carbone), impact sur la **faune / la vie
  sauvage** (dérangement, compétition, reproduction), **régulation / encadrement**, dimension
  sociale ou symbolique, etc. Ne laisse pas les chiffres accaparer tous les slots.
- Chaque élément : `statement` (≤20 mots, neutre, factuel), `kind` (`fait` | `biais` | `enjeu`
  | `affirmation` | `angle`), `centrality` (1–5), et si possible `seeds` (nœud d'origine).
- Ne juge PAS la qualité de l'article ; décris ce qui est central.

Réponds avec un objet `{"elements": [...]}` de 3 à 5 éléments, triés par `centrality` décroissante.
