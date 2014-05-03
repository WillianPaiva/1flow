
# Migration MongoDB → PostgreSQL

- port all models
	- The archive DB will be back into the production DB, only a simple  dedicated table.
		- simplify dot.env, settings, etc (no more archive DB)

- rename MongoDB classes as “MongoArticle” etc
- duplicate core.tasks.refresh_all_feeds() to allow parallel fetches in both databases
- port all views to PG.

- MIGRATE

- port/clean API (tastypie)
