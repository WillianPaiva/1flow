
-- See `Slow Queries.md` for explanations.

CREATE INDEX idx_core_baseitem_duplicate_of_id_is_not_null
ON core_baseitem(duplicate_of_id)
WHERE duplicate_of_id IS NOT NULL;

-- ————————————————————————————————————————————————————————————————————— errors

CREATE INDEX idx_core_article_url_error_not_null
ON core_article(url_error)
WHERE url_error IS NOT NULL;

CREATE INDEX idx_core_article_content_error_not_null
ON core_article(content_error)
WHERE content_error IS NOT NULL;

-- ——————————————————————————————————————————————————————————————————— booleans

CREATE INDEX idx_core_article_orphaned
ON core_article(is_orphaned)
WHERE is_orphaned IS TRUE;

-- CREATE INDEX idx_core_article_content_type_1
-- ON core_article(content_type)
-- WHERE content_type = 1;
