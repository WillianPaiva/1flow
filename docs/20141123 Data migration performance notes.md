
# Data migration note

When turning Article.date_published into BaseItem.date_published.


## Operations / steps

- create BaseItem.date_published_transient (in a south migration)
- copy all values from Article to BaseItem (in a data migration)
- remove the Article.date_published field (in a south migration)
- rename BaseItem.date_published_transient to date_published (migration too)


## Performance note on the data migration

In python, we needed to do :

    for article in orm.Article.objects.exclude(date_published=None):
        article.date_published_transient = article.date_published
        article.save()

On my development machine (30k articles, 8Gb RAM, SSD), this took less than 30 seconds.
On the CECA machine (50k articles, 16Gb RAM, HDD), this took less than 15 minutes.
On 1flow.io (7.5M articles, 96Gb RAM, HDD), this failed after 7 hours, OOM killed the python process, after having consumed more than 30Gb of RAM. Even `statsd` failed to receive some statistics, a situation which had not happened since 2 years on the first small server. The machine was really down on its knees, for such a simple operation…

The following SQL query did exactly the same, and took only a few hours (started 23h30, finished when I connected back @ 7h30). 

	UPDATE 
		core_baseitem
	SET 
		date_published_transient = core_article.date_published
	FROM 
		core_article
	WHERE 
		core_article.baseitem_ptr_id = core_baseitem.id
	AND 
		core_article.date_published IS NOT NULL;

I should have done it directly with a cursor connection. But I was too confiant it would acheive to run. Even the mongo→postgresql migration ran without any problem, and took much less RAM.

And:

    ./manage.py migrate oneflow.core --fake 0092

To bypass the corresponding Django/South migration.
