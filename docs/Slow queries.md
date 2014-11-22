
Slow PG Queries
~~~~~~~~~~~~~~~

# Get Articles with URL errors from last week

Index are not used.
I need a partial one, and on content_error too.
We need to raise effective_cache_memory to 64GB at least.
Perhaps lower the index read cost.

EXPLAIN 
SELECT 
   "core_baseitem"."id",
   "core_baseitem"."polymorphic_ctype_id",
   "core_baseitem"."duplicate_of_id",
   "core_baseitem"."duplicate_status",
   "core_baseitem"."language_id",
   "core_baseitem"."name",
   "core_baseitem"."slug",
   "core_baseitem"."user_id",
   "core_baseitem"."is_restricted",
   "core_baseitem"."date_created",
   "core_baseitem"."date_updated",
   "core_baseitem"."default_rating",
   "core_baseitem"."text_direction",
   "core_baseitem"."origin",
   "core_article"."baseitem_ptr_id",
   "core_article"."url",
   "core_article"."comments_feed_url",
   "core_article"."url_absolute",
   "core_article"."url_error",
   "core_article"."is_orphaned",
   "core_article"."image_url",
   "core_article"."excerpt",
   "core_article"."content",
   "core_article"."content_type",
   "core_article"."content_error",
   "core_article"."word_count",
   "core_article"."date_published" 
FROM 
   "core_article" 
INNER JOIN 
   "core_baseitem" 
ON (
   "core_article"."baseitem_ptr_id" = "core_baseitem"."id" 
) WHERE (
   NOT ("core_article"."url_error" IS NULL) 
   AND "core_baseitem"."date_created" <= '2014-11-09 04:55:00.362460+00:00'  
   AND "core_baseitem"."date_created" >= '2014-11-02 04:55:00.362460+00:00' 
);


—————————————————————————————————————————————————————————————


# Update the number of feed recent items

I knew it would be expensive even before using a relational database. Even in MongoDB, it is.

   SELECT COUNT(*) 
   FROM "core_baseitem" 
   INNER JOIN "core_basefeed_items" 
   ON ( "core_baseitem"."id" = "core_basefeed_items"."baseitem_id" ) 
   INNER JOIN "core_article" 
   ON ( "core_baseitem"."id" = "core_article"."baseitem_ptr_id" ) 
   WHERE ("core_basefeed_items"."basefeed_id" = 3242  
   AND "core_article"."is_orphaned" = false  
   AND "core_article"."url_absolute" = true  
   AND "core_baseitem"."duplicate_of_id" IS NULL 
   AND "core_article"."date_published" > '2014-05-13 00:00:00+02:00' )

```
 Aggregate  (cost=279010.39..279010.40 rows=1 width=0)
   ->  Nested Loop  (cost=273103.79..279008.69 rows=680 width=0)
         Join Filter: (core_basefeed_items.baseitem_id = core_baseitem.id)
         ->  Hash Join  (cost=273103.36..275800.15 rows=699 width=8)
               Hash Cond: (core_basefeed_items.baseitem_id = core_article.baseitem_ptr_id)
               ->  Index Only Scan using core_basefeed_items_basefeed_id_4d41eacdbcee3fa6_uniq on core_basefeed_items  (cost=0.43..2147.11 rows=48278 width=4)
                     Index Cond: (basefeed_id = 2584)
               ->  Hash  (cost=271575.46..271575.46 rows=122197 width=4)
                     ->  Index Scan using core_article_date_published on core_article  (cost=0.43..271575.46 rows=122197 width=4)
                           Index Cond: (date_published > '2014-05-12 22:00:00+00'::timestamp with time zone)
                           Filter: ((NOT is_orphaned) AND url_absolute)
         ->  Index Scan using core_baseitem_pkey on core_baseitem  (cost=0.43..4.58 rows=1 width=4)
               Index Cond: (id = core_article.baseitem_ptr_id)
               Filter: (duplicate_of_id IS NULL)
```
