# {{ subject }}

{% if meta_line %}*{{ meta_line }}*

{% endif %}{{ intro }}

## L'intérêt

{{ why_selected }}

{{ payoff }}

## Les repères

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
## L'architecture de l'argument

### Angles morts & nuances
{% for a in angles_morts %}
- {{ a }}
{%- endfor %}

### À vous de juger

{{ wrap_up }}

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
