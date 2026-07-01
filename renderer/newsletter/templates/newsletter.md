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

## Vérification des faits
{% for f in fact_check %}
> « {{ f.claim }} »
> *{{ f.presentation }}*

{{ f.reading }}
{% endfor %}
## Les failles
{% for s in failles %}
### {{ s.heading }}

{{ s.body }}
{% endfor %}
## Ce qui tient
{% for s in strengths %}
### ✓ {{ s.heading }}

{{ s.body }}
{% endfor %}
## Angles morts & nuances
{% for a in angles_morts %}
- {{ a }}
{%- endfor %}

## Notre verdict

{% if score %}**{{ score }} / 5**{% if band %} — {{ band }}{% endif %}

{% endif %}{{ verdict_line }}
{% if for_whom %}
*Pour qui : {{ for_whom }}*
{% endif %}
## Pour aller plus loin
{% for r in go_further %}
**{{ r.title }}**{% if r.source %} — {{ r.source }}{% endif %}
{% if r.why %}
{{ r.why }}
{% endif %}{% endfor %}

---

{{ signoff }}

— Sing Sing
