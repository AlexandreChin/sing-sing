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

# {{ subject }}

{% if meta_line %}*{{ meta_line }}*

{% endif %}{{ intro }}

## L'intérêt

*{{ selection_headline }}*

{{ why_selected }}

{{ payoff }}

## Les repères

### Le contexte

{{ context }}

### Les réflexes
{% for r in reflexes %}
- {{ r }}
{%- endfor %}

## Au fil de la lecture
{% for d in decryptage %}
> « {{ d.quote }} »

{{ d.reading }}
{% if d.clue %}
↩ *« {{ d.clue }} »*
{% endif %}{% endfor %}
## L'architecture de l'argument
{% for s in architecture.spine %}
{{ loop.index }}. {{ s }}
{%- endfor %}

> {{ architecture.keystone }}

## À emporter

### À retenir
{% for t in a_emporter.key_takeaways %}
- {{ t }}
{%- endfor %}

### Les réflexes critiques
{% for r in a_emporter.reflexes_critiques %}
- {{ r }}
{%- endfor %}

## À vous de juger

### L'enjeu de fond

{{ verdict.enjeu }}

### L'objection la plus solide

{{ verdict.objection }}

{{ verdict.tient_fragile }}

### Angles morts & nuances
{% for a in verdict.angles_morts %}
- {{ a }}
{%- endfor %}

### La question

> {{ verdict.la_question }}

## Prolonger la réflexion

### À qui profite ce cadrage ?

{{ cui_bono }}

### Pour aller plus loin
{% for r in go_further %}
**{{ r.title }}**{% if r.source %} — {{ r.source }}{% endif %}
{% if r.why %}
{{ r.why }}
{% endif %}{% endfor %}
---

{{ signoff }}

— Sing Sing
