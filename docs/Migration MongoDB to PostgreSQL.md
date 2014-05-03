
# Migration MongoDB → PostgreSQL

- port all models
	- archive DB back into production DB, dedicated table.
		- simplify dot.env, settings, etc (no more archive DB)
- port API
- port all views

- rename MongoDB classes as “MongoArticle” etc


- rename MongoDB tasks
- migrate feeds
	- clone feed into PG
		- this will launch tasks, new articles are pulled in, users can use 1flow again
	- clone articles and relink
	- clone reads
