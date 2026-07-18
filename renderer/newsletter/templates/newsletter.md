# {{ subject }}

{% if meta_line %}*{{ meta_line }}*

{% endif %}{{ intro }}

## Pourquoi cet article

{{ why_selected }}

{{ payoff }}

## Avant de lire

{{ context }}
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
## La vue d'ensemble

### Ce qui tient
{% for s in strengths %}
#### ✓ {{ s.heading }}

{{ s.body }}
{% endfor %}
### Angles morts & nuances
{% for a in angles_morts %}
- {{ a }}
{%- endfor %}

### À vous de juger

{% if score %}**{{ score }} / 5**{% if band %} — {{ band }}{% endif %}

{% endif %}{{ wrap_up }}
{% if for_whom %}
*Pour qui : {{ for_whom }}*
{% endif %}
## Pour aller plus loin
{% for r in go_further %}
**{{ r.title }}**{% if r.source %} — {{ r.source }}{% endif %}
{% if r.why %}
{{ r.why }}
{% endif %}{% endfor %}
## Prolonger la réflexion
{% for p in prolongements %}
### {{ p.heading }}

{{ p.body }}
{% endfor %}
> {{ open_question }}

---

{{ signoff }}

— Sing Sing
