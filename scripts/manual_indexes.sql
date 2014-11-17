
-- See `Slow Queries.md` for explanations.

CREATE INDEX idx_core_article_url_error_not_null
ON core_article(url_error)
WHERE url_error IS NOT NULL;

CREATE INDEX idx_core_article_content_error_not_null
ON core_article(content_error)
WHERE content_error IS NOT NULL;
