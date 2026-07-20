---
subject: {{ subject | tojson }}
preheader: {{ preheader | tojson }}
hook_title: {{ hook_title | tojson }}
{% if cat_pill %}category: {{ orig_category | tojson }}
{% endif %}article_title: {{ orig_title | tojson }}
article_url: {{ orig_url | tojson }}
meta_line: {{ meta_line | tojson }}
signoff: {{ signoff | tojson }}
---

{{ intro }}

## Pourquoi cet article

*{{ selection_headline }}*

{{ why_selected }}

{{ payoff }}

## Avant de vous lancer

### Le contexte

{{ context }}

### Les réflexes
{% for r in reflexes %}
- {{ r }}
{%- endfor %}
{% if repere_facts %}
### Les faits à garder en tête
{% for f in repere_facts %}
- {{ f }}
{%- endfor %}
{% endif %}{% if key_terms %}
### Le lexique
{% for kt in key_terms %}
- **{{ kt.term }}** — {{ kt.definition }}
{%- endfor %}
{% endif %}
## Au fil de la lecture
{% for d in decryptage %}
> « {{ d.quote }} »

{{ d.reading }}
{% if d.clue %}
↩ *« {{ d.clue }} »*
{% endif %}{% endfor %}{% if exercices %}
### À vous de repérer
{% for ex in exercices %}
> « {{ ex.quote }} »

{{ ex.prompt }}

**Réponse —** {{ ex.answer }}
{% endfor %}{% endif %}
## Après la lecture

### L'architecture de l'argument
{% for s in architecture.spine %}
{{ loop.index }}. {{ s }}
{%- endfor %}

> {{ architecture.keystone }}

### À qui profite ce cadrage ?

{{ cui_bono }}

### Les enjeux de fond
{% for e in verdict.enjeux %}
- {{ e }}
{%- endfor %}

### Les objections les plus solides
{% for o in verdict.objections %}
- {{ o }}
{%- endfor %}

### Angles morts
{% for a in verdict.angles_morts %}
- {{ a }}
{%- endfor %}

### Nuances
{% for n in verdict.nuances %}
- {{ n }}
{%- endfor %}

### À retenir
{% for t in a_emporter.key_takeaways %}
- {{ t }}
{%- endfor %}

### Les réflexes critiques
{% for r in a_emporter.reflexes_critiques %}
- **{{ r.name }}** — {{ r.rule }}{% if r.reusable_on %} *(réutilisable : {{ r.reusable_on }})*{% endif %}
{%- endfor %}

### Les questions à se poser
{% for q in verdict.questions %}
> {{ q }}
{% endfor %}
### Pour aller plus loin
{% for r in go_further %}
**{% if r.url %}[{{ r.title }}]({{ 'https://' + r.url if '://' not in r.url else r.url }}){% else %}{{ r.title }}{% endif %}**{% if r.source %} — {{ r.source }}{% endif %}{% if r.type %} · {{ r.type }}{% endif %}
{% if r.why %}
{{ r.why }}
{% endif %}{% endfor %}
### Avant de partir

- **Abonnez-vous** à la newsletter pour recevoir chaque décryptage.
- **Partagez** cette édition à quelqu'un qui aime lire de près.
- **Réagissez** et commentez sur Instagram : [@singsing.media](https://instagram.com/singsing.media).
