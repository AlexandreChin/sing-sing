---
subject: {{ subject | tojson }}
preheader: {{ preheader | tojson }}
hook_title: {{ hook_title | tojson }}
{% if cat_pill %}category: {{ orig_category | tojson }}
{% endif %}article_title: {{ orig_title | tojson }}
article_url: {{ orig_url | tojson }}
meta_line: {{ meta_line | tojson }}
signoff: {{ signoff | tojson }}
medium: {{ medium | tojson }}
{% if go_further %}go_further:
{% for r in go_further %}  - type: {{ (r.type or "") | tojson }}
    title: {{ r.title | tojson }}
    source: {{ (r.source or "") | tojson }}
    url: {{ (r.url or "") | tojson }}
    why: {{ (r.why or "") | tojson }}
{% endfor %}{% endif %}---

{{ essentiel }}

## {{ labels.why }}

*{{ selection_headline }}*

{{ why_selected }}

{{ payoff }}

## Avant de vous lancer

### Le contexte

{{ context }}
{% if key_terms %}
### Le lexique
{% for kt in key_terms %}
- **{{ kt.term }}** : {{ kt.definition }}
{%- endfor %}
{% endif %}
### {{ labels.how_to }}

{{ reading_posture }} Voici les réflexes à garder sous la main :
{% for r in a_emporter.reflexes_critiques %}{% set L = LENSES.get(r.lens_ref, {}) %}
- {{ L.icon }} **{{ L.name }}** : {{ r.rule }}
{%- endfor %}
{% if repere_facts %}
### Les faits à garder en tête
{% for f in repere_facts %}
- {{ f }}
{%- endfor %}
{% endif %}
## {{ labels.during }}
{% for d in decryptage %}
::: card
> « {{ d.quote }} »

{% if d.lens_icon %}{{ d.lens_icon }} **{{ d.lens_name }}** : {% endif %}{{ d.prompt }}

→ {{ d.reading }}
:::
{% endfor %}
## {{ labels.after }}

### Le cadrage

{{ framing }}

::: note
{{ labels.cadrage_note }}
:::

### Les présupposés
{% for p in architecture.presupposes %}
- {{ p }}
{%- endfor %}

### Angles morts
{% for a in verdict.angles_morts %}
- {{ a }}
{%- endfor %}

### Nuances
{% for n in verdict.nuances %}
- {{ n }}
{%- endfor %}

### Les objections les plus solides
{% for o in verdict.objections %}
- {{ o }}
{%- endfor %}

### Les enjeux de fond
{% for e in verdict.enjeux %}
- {{ e }}
{%- endfor %}

> {{ architecture.keystone }}

::: gofurther
:::

### Avant de partir

- **Abonnez-vous** à la newsletter pour recevoir chaque décryptage.
- **Partagez** cette édition {{ labels.share_note }}.
- **Réagissez** et commentez sur Instagram : [@singsing.media](https://instagram.com/singsing.media).
