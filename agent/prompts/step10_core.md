# Étape 10 — Éléments centraux de l'article

À partir de l'ARTICLE et du matériel factuel extrait (citations clés, faits, observations,
affirmations, biais), identifie les **3 à 5 éléments les plus centraux** de l'article :
ce dont l'article **parle fondamentalement**, ce qu'il **défend** ou ce qui l'**inquiète**.

Règles :
- Classe par **centralité à l'article** (`centrality` de 1 à 5) — la place et le poids que
  l'article y consacre. **Ignore le titre** : ne privilégie PAS l'angle du titre, ne te laisse
  pas guider par lui. Un élément très présent dans le corps mais absent du titre doit ressortir.
- **Couvre la diversité** des préoccupations de l'article — ne réduis pas tout à un seul thème.
  Si l'article traite à la fois du bilan carbone, de la concurrence avec la faune et de la
  régulation, les trois doivent apparaître.
- Chaque élément : `statement` (≤20 mots, neutre, factuel), `kind` (`fait` | `biais` | `enjeu`
  | `affirmation` | `angle`), `centrality` (1–5), et si possible `seeds` (nœud d'origine).
- Ne juge PAS la qualité de l'article ; décris ce qui est central.

Réponds avec un objet `{"elements": [...]}` de 3 à 5 éléments, triés par `centrality` décroissante.
