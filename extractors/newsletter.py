"""Newsletter extractor.

A newsletter has no per-slide length budget, so there's nothing to trim — this is
a passthrough that bundles the full analysis with the newsletter presentation into
the render-ready NewsletterDocument. Kept as a distinct stage so the format plugs
into the registry (adapt agent, extractor, renderer) like every other format.
"""
from models.full_analysis import ArticleFullAnalysis
from models.newsletter_presentation import NewsletterPresentation, NewsletterDocument


def extract(full: ArticleFullAnalysis, presentation: NewsletterPresentation) -> NewsletterDocument:
    return NewsletterDocument(analysis=full, presentation=presentation)
