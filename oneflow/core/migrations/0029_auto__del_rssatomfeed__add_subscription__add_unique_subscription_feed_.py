# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'RssAtomFeed'
        db.delete_table(u'core_rssatomfeed')

        # Removing M2M table for field tags on 'RssAtomFeed'
        db.delete_table(db.shorten_name(u'core_rssatomfeed_tags'))

        # Removing M2M table for field languages on 'RssAtomFeed'
        db.delete_table(db.shorten_name(u'core_rssatomfeed_languages'))

        # Adding model 'Subscription'
        db.create_table(u'core_subscription', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('feed', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.BaseFeed'], unique=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['base.User'], unique=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('notes', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('core', ['Subscription'])

        # Adding M2M table for field items on 'Subscription'
        m2m_table_name = db.shorten_name(u'core_subscription_items')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('subscription', models.ForeignKey(orm['core.subscription'], null=False)),
            ('read', models.ForeignKey(orm['core.read'], null=False))
        ))
        db.create_unique(m2m_table_name, ['subscription_id', 'read_id'])

        # Adding M2M table for field tags on 'Subscription'
        m2m_table_name = db.shorten_name(u'core_subscription_tags')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('subscription', models.ForeignKey(orm['core.subscription'], null=False)),
            ('simpletag', models.ForeignKey(orm['core.simpletag'], null=False))
        ))
        db.create_unique(m2m_table_name, ['subscription_id', 'simpletag_id'])

        # Adding M2M table for field folders on 'Subscription'
        m2m_table_name = db.shorten_name(u'core_subscription_folders')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('subscription', models.ForeignKey(orm['core.subscription'], null=False)),
            ('folder', models.ForeignKey(orm['core.folder'], null=False))
        ))
        db.create_unique(m2m_table_name, ['subscription_id', 'folder_id'])

        # Adding unique constraint on 'Subscription', fields ['feed', 'user']
        db.create_unique(u'core_subscription', ['feed_id', 'user_id'])

        # Adding model 'Read'
        db.create_table(u'core_read', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['base.User'], unique=True)),
            ('item', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.BaseItem'], unique=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, blank=True)),
            ('is_good', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_read', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_read', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('is_auto_read', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_auto_read', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('is_archived', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_archived', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('is_starred', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('date_starred', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('is_bookmarked', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_bookmarked', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('bookmark_type', self.gf('django.db.models.fields.CharField')(default=u'U', max_length=2)),
            ('is_fact', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_fact', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('is_quote', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_quote', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('is_number', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_number', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('is_analysis', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_analysis', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('is_prospective', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_prospective', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('is_knowhow', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_knowhow', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('is_rules', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_rules', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('is_knowledge', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_knowledge', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('knowledge_type', self.gf('django.db.models.fields.CharField')(max_length=2, null=True, blank=True)),
            ('is_fun', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_fun', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('rating', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('check_set_subscriptions_131004_done', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('core', ['Read'])

        # Adding M2M table for field senders on 'Read'
        m2m_table_name = db.shorten_name(u'core_read_senders')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('read', models.ForeignKey(orm['core.read'], null=False)),
            ('user', models.ForeignKey(orm[u'base.user'], null=False))
        ))
        db.create_unique(m2m_table_name, ['read_id', 'user_id'])

        # Adding M2M table for field tags on 'Read'
        m2m_table_name = db.shorten_name(u'core_read_tags')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('read', models.ForeignKey(orm['core.read'], null=False)),
            ('simpletag', models.ForeignKey(orm['core.simpletag'], null=False))
        ))
        db.create_unique(m2m_table_name, ['read_id', 'simpletag_id'])

        # Adding unique constraint on 'Read', fields ['user', 'item']
        db.create_unique(u'core_read', ['user_id', 'item_id'])

        # Adding model 'BaseItem'
        db.create_table(u'core_baseitem', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('polymorphic_ctype', self.gf('django.db.models.fields.related.ForeignKey')(related_name='polymorphic_core.baseitem_set', null=True, to=orm['contenttypes.ContentType'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('slug', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['base.User'], null=True, blank=True)),
            ('is_restricted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_added', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('default_rating', self.gf('django.db.models.fields.FloatField')(default=0.0, blank=True)),
            ('language', self.gf('django.db.models.fields.CharField')(max_length=5)),
            ('text_direction', self.gf('django.db.models.fields.CharField')(default=u'ltr', max_length=3)),
            ('image_url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('excerpt', self.gf('django.db.models.fields.TextField')()),
            ('origin', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('duplicate_of', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.BaseItem'])),
        ))
        db.send_create_signal('core', ['BaseItem'])

        # Adding M2M table for field tags on 'BaseItem'
        m2m_table_name = db.shorten_name(u'core_baseitem_tags')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('baseitem', models.ForeignKey(orm['core.baseitem'], null=False)),
            ('simpletag', models.ForeignKey(orm['core.simpletag'], null=False))
        ))
        db.create_unique(m2m_table_name, ['baseitem_id', 'simpletag_id'])

        # Adding M2M table for field sources on 'BaseItem'
        m2m_table_name = db.shorten_name(u'core_baseitem_sources')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_baseitem', models.ForeignKey(orm['core.baseitem'], null=False)),
            ('to_baseitem', models.ForeignKey(orm['core.baseitem'], null=False))
        ))
        db.create_unique(m2m_table_name, ['from_baseitem_id', 'to_baseitem_id'])

        # Adding model 'CombinedFeed'
        db.create_table(u'core_combinedfeed', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['base.User'])),
            ('is_restricted', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('core', ['CombinedFeed'])

        # Adding model 'Folder'
        db.create_table(u'core_folder', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['base.User'])),
            ('parent', self.gf('mptt.fields.TreeForeignKey')(blank=True, related_name='children', null=True, to=orm['core.Folder'])),
            (u'lft', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            (u'rght', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            (u'tree_id', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            (u'level', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
        ))
        db.send_create_signal('core', ['Folder'])

        # Adding unique constraint on 'Folder', fields ['name', 'user', 'parent']
        db.create_unique(u'core_folder', ['name', 'user_id', 'parent_id'])

        # Adding model 'CombinedFeedRule'
        db.create_table(u'core_combinedfeedrule', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('combinedfeed', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.CombinedFeed'])),
            ('clone_of', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.MailFeedRule'], null=True, blank=True)),
            ('position', self.gf('django.db.models.fields.IntegerField')(default=0, blank=True)),
            ('is_valid', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('check_error', self.gf('django.db.models.fields.CharField')(default=u'', max_length=255, blank=True)),
        ))
        db.send_create_signal('core', ['CombinedFeedRule'])

        # Adding M2M table for field feeds on 'CombinedFeedRule'
        m2m_table_name = db.shorten_name(u'core_combinedfeedrule_feeds')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('combinedfeedrule', models.ForeignKey(orm['core.combinedfeedrule'], null=False)),
            ('basefeed', models.ForeignKey(orm['core.basefeed'], null=False))
        ))
        db.create_unique(m2m_table_name, ['combinedfeedrule_id', 'basefeed_id'])

        # Adding model 'WebSite'
        db.create_table(u'core_website', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('slug', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('url', self.gf('django.db.models.fields.URLField')(unique=True, max_length=200)),
            ('parent', self.gf('mptt.fields.TreeForeignKey')(blank=True, related_name='children', null=True, to=orm['core.WebSite'])),
            ('duplicate_of', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.WebSite'])),
            ('fetch_limit_nr', self.gf('django.db.models.fields.IntegerField')(default=16)),
            ('mail_warned', self.gf('jsonfield.fields.JSONField')()),
            ('thumbnail', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('thumbnail_url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('short_description_en', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('short_description_fr', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('short_description_nt', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('description_en', self.gf('django.db.models.fields.TextField')()),
            ('description_fr', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('description_nt', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            (u'lft', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            (u'rght', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            (u'tree_id', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            (u'level', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
        ))
        db.send_create_signal('core', ['WebSite'])

        # Adding model 'Article'
        db.create_table(u'core_article', (
            (u'baseitem_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.BaseItem'], unique=True, primary_key=True)),
            ('url', self.gf('django.db.models.fields.URLField')(unique=True, max_length=200)),
            ('url_absolute', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('url_error', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('pages_urls', self.gf('jsonfield.fields.JSONField')(default=u'[]', blank=True)),
            ('is_orphaned', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_published', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('content_type', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('content_error', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('word_count', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('core', ['Article'])

        # Adding M2M table for field publishers on 'Article'
        m2m_table_name = db.shorten_name(u'core_article_publishers')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('article', models.ForeignKey(orm['core.article'], null=False)),
            ('user', models.ForeignKey(orm[u'base.user'], null=False))
        ))
        db.create_unique(m2m_table_name, ['article_id', 'user_id'])

        # Adding model 'BaseFeed'
        db.create_table(u'core_basefeed', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('polymorphic_ctype', self.gf('django.db.models.fields.related.ForeignKey')(related_name='polymorphic_core.basefeed_set', null=True, to=orm['contenttypes.ContentType'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['base.User'], null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('slug', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, auto_now_add=True, blank=True)),
            ('is_internal', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_restricted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('date_closed', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('closed_reason', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('fetch_interval', self.gf('django.db.models.fields.IntegerField')(default=43200, blank=True)),
            ('date_last_fetch', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('errors', self.gf('jsonfield.fields.JSONField')(null=True, blank=True)),
            ('options', self.gf('jsonfield.fields.JSONField')(null=True, blank=True)),
            ('duplicate_of', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.BaseFeed'], null=True, blank=True)),
            ('notes', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('is_good', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('thumbnail', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('thumbnail_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('short_description_en', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('short_description_fr', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('short_description_nt', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('description_en', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('description_fr', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('description_nt', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('core', ['BaseFeed'])

        # Adding M2M table for field items on 'BaseFeed'
        m2m_table_name = db.shorten_name(u'core_basefeed_items')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('basefeed', models.ForeignKey(orm['core.basefeed'], null=False)),
            ('baseitem', models.ForeignKey(orm['core.baseitem'], null=False))
        ))
        db.create_unique(m2m_table_name, ['basefeed_id', 'baseitem_id'])

        # Adding M2M table for field languages on 'BaseFeed'
        m2m_table_name = db.shorten_name(u'core_basefeed_languages')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('basefeed', models.ForeignKey(orm['core.basefeed'], null=False)),
            ('language', models.ForeignKey(orm['core.language'], null=False))
        ))
        db.create_unique(m2m_table_name, ['basefeed_id', 'language_id'])

        # Deleting field 'MailFeed.user'
        db.delete_column(u'core_mailfeed', 'user_id')

        # Deleting field 'MailFeed.is_public'
        db.delete_column(u'core_mailfeed', 'is_public')

        # Deleting field 'MailFeed.id'
        db.delete_column(u'core_mailfeed', u'id')

        # Deleting field 'MailFeed.name'
        db.delete_column(u'core_mailfeed', 'name')

        # Adding field 'MailFeed.basefeed_ptr'
        db.add_column(u'core_mailfeed', u'basefeed_ptr',
                      self.gf('django.db.models.fields.related.OneToOneField')(default=1, to=orm['core.BaseFeed'], unique=True, primary_key=True),
                      keep_default=False)


    def backwards(self, orm):
        # Removing unique constraint on 'Folder', fields ['name', 'user', 'parent']
        db.delete_unique(u'core_folder', ['name', 'user_id', 'parent_id'])

        # Removing unique constraint on 'Read', fields ['user', 'item']
        db.delete_unique(u'core_read', ['user_id', 'item_id'])

        # Removing unique constraint on 'Subscription', fields ['feed', 'user']
        db.delete_unique(u'core_subscription', ['feed_id', 'user_id'])

        # Adding model 'RssAtomFeed'
        db.create_table(u'core_rssatomfeed', (
            ('date_closed', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('is_internal', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('duplicate_of', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.RssAtomFeed'], null=True, blank=True)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['base.User'], null=True, blank=True)),
            ('description_fr', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('description_en', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('short_description_nt', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('last_etag', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('fetch_interval', self.gf('django.db.models.fields.IntegerField')(default=43200, blank=True)),
            ('date_last_fetch', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('site_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('short_description_en', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True)),
            ('errors', self.gf('jsonfield.fields.JSONField')(null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('closed_reason', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200, unique=True)),
            ('description_nt', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('notes', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('is_restricted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('thumbnail', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('is_good', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('short_description_fr', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, auto_now_add=True, blank=True)),
            ('thumbnail_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('options', self.gf('jsonfield.fields.JSONField')(null=True, blank=True)),
        ))
        db.send_create_signal('core', ['RssAtomFeed'])

        # Adding M2M table for field tags on 'RssAtomFeed'
        m2m_table_name = db.shorten_name(u'core_rssatomfeed_tags')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('rssatomfeed', models.ForeignKey(orm['core.rssatomfeed'], null=False)),
            ('simpletag', models.ForeignKey(orm['core.simpletag'], null=False))
        ))
        db.create_unique(m2m_table_name, ['rssatomfeed_id', 'simpletag_id'])

        # Adding M2M table for field languages on 'RssAtomFeed'
        m2m_table_name = db.shorten_name(u'core_rssatomfeed_languages')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('rssatomfeed', models.ForeignKey(orm['core.rssatomfeed'], null=False)),
            ('language', models.ForeignKey(orm['core.language'], null=False))
        ))
        db.create_unique(m2m_table_name, ['rssatomfeed_id', 'language_id'])

        # Deleting model 'Subscription'
        db.delete_table(u'core_subscription')

        # Removing M2M table for field items on 'Subscription'
        db.delete_table(db.shorten_name(u'core_subscription_items'))

        # Removing M2M table for field tags on 'Subscription'
        db.delete_table(db.shorten_name(u'core_subscription_tags'))

        # Removing M2M table for field folders on 'Subscription'
        db.delete_table(db.shorten_name(u'core_subscription_folders'))

        # Deleting model 'Read'
        db.delete_table(u'core_read')

        # Removing M2M table for field senders on 'Read'
        db.delete_table(db.shorten_name(u'core_read_senders'))

        # Removing M2M table for field tags on 'Read'
        db.delete_table(db.shorten_name(u'core_read_tags'))

        # Deleting model 'BaseItem'
        db.delete_table(u'core_baseitem')

        # Removing M2M table for field tags on 'BaseItem'
        db.delete_table(db.shorten_name(u'core_baseitem_tags'))

        # Removing M2M table for field sources on 'BaseItem'
        db.delete_table(db.shorten_name(u'core_baseitem_sources'))

        # Deleting model 'CombinedFeed'
        db.delete_table(u'core_combinedfeed')

        # Deleting model 'Folder'
        db.delete_table(u'core_folder')

        # Deleting model 'CombinedFeedRule'
        db.delete_table(u'core_combinedfeedrule')

        # Removing M2M table for field feeds on 'CombinedFeedRule'
        db.delete_table(db.shorten_name(u'core_combinedfeedrule_feeds'))

        # Deleting model 'WebSite'
        db.delete_table(u'core_website')

        # Deleting model 'Article'
        db.delete_table(u'core_article')

        # Removing M2M table for field publishers on 'Article'
        db.delete_table(db.shorten_name(u'core_article_publishers'))

        # Deleting model 'BaseFeed'
        db.delete_table(u'core_basefeed')

        # Removing M2M table for field items on 'BaseFeed'
        db.delete_table(db.shorten_name(u'core_basefeed_items'))

        # Removing M2M table for field languages on 'BaseFeed'
        db.delete_table(db.shorten_name(u'core_basefeed_languages'))


        # User chose to not deal with backwards NULL issues for 'MailFeed.user'
        raise RuntimeError("Cannot reverse this migration. 'MailFeed.user' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration        # Adding field 'MailFeed.user'
        db.add_column(u'core_mailfeed', 'user',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['base.User']),
                      keep_default=False)

        # Adding field 'MailFeed.is_public'
        db.add_column(u'core_mailfeed', 'is_public',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'MailFeed.id'
        raise RuntimeError("Cannot reverse this migration. 'MailFeed.id' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration        # Adding field 'MailFeed.id'
        db.add_column(u'core_mailfeed', u'id',
                      self.gf('django.db.models.fields.AutoField')(primary_key=True),
                      keep_default=False)


        # User chose to not deal with backwards NULL issues for 'MailFeed.name'
        raise RuntimeError("Cannot reverse this migration. 'MailFeed.name' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration        # Adding field 'MailFeed.name'
        db.add_column(u'core_mailfeed', 'name',
                      self.gf('django.db.models.fields.CharField')(max_length=255),
                      keep_default=False)

        # Deleting field 'MailFeed.basefeed_ptr'
        db.delete_column(u'core_mailfeed', u'basefeed_ptr_id')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'base.user': {
            'Meta': {'object_name': 'User'},
            'data': ('jsonfield.fields.JSONField', [], {'default': '{}', 'blank': 'True'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '254', 'db_index': 'True'}),
            'email_announcements': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            'hash_codes': ('jsonfield.fields.JSONField', [], {'default': "{'unsubscribe': '2c82c8ba76fb4e09827c21079696497e'}", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'register_data': ('jsonfield.fields.JSONField', [], {'default': '{}', 'blank': 'True'}),
            'sent_emails': ('jsonfield.fields.JSONField', [], {'default': '{}', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '254', 'db_index': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'core.article': {
            'Meta': {'object_name': 'Article', '_ormbases': ['core.BaseItem']},
            u'baseitem_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.BaseItem']", 'unique': 'True', 'primary_key': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'content_error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'date_published': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'is_orphaned': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'pages_urls': ('jsonfield.fields.JSONField', [], {'default': "u'[]'", 'blank': 'True'}),
            'publishers': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['base.User']", 'symmetrical': 'False'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200'}),
            'url_absolute': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'url_error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'word_count': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'core.basefeed': {
            'Meta': {'object_name': 'BaseFeed'},
            'closed_reason': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'date_closed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now_add': 'True', 'blank': 'True'}),
            'date_last_fetch': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'description_en': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_fr': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_nt': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'duplicate_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.BaseFeed']", 'null': 'True', 'blank': 'True'}),
            'errors': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'fetch_interval': ('django.db.models.fields.IntegerField', [], {'default': '43200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_good': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_internal': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_restricted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'items': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.BaseItem']", 'symmetrical': 'False'}),
            'languages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.Language']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'options': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_core.basefeed_set'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            'short_description_en': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'short_description_fr': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'short_description_nt': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'thumbnail': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'thumbnail_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.User']", 'null': 'True', 'blank': 'True'})
        },
        'core.baseitem': {
            'Meta': {'object_name': 'BaseItem'},
            'date_added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'default_rating': ('django.db.models.fields.FloatField', [], {'default': '0.0', 'blank': 'True'}),
            'duplicate_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.BaseItem']"}),
            'excerpt': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'is_restricted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'origin': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_core.baseitem_set'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'sources': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'sources_rel_+'", 'to': "orm['core.BaseItem']"}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.SimpleTag']", 'symmetrical': 'False'}),
            'text_direction': ('django.db.models.fields.CharField', [], {'default': "u'ltr'", 'max_length': '3'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.User']", 'null': 'True', 'blank': 'True'})
        },
        'core.combinedfeed': {
            'Meta': {'object_name': 'CombinedFeed'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_restricted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.User']"})
        },
        'core.combinedfeedrule': {
            'Meta': {'ordering': "('position',)", 'object_name': 'CombinedFeedRule'},
            'check_error': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255', 'blank': 'True'}),
            'clone_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.MailFeedRule']", 'null': 'True', 'blank': 'True'}),
            'combinedfeed': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.CombinedFeed']"}),
            'feeds': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.BaseFeed']", 'symmetrical': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_valid': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'})
        },
        'core.corepermissions': {
            'Meta': {'object_name': 'CorePermissions'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'core.folder': {
            'Meta': {'unique_together': "(('name', 'user', 'parent'),)", 'object_name': 'Folder'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            u'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            u'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['core.Folder']"}),
            u'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            u'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.User']"})
        },
        'core.helpcontent': {
            'Meta': {'ordering': "['ordering', 'id']", 'object_name': 'HelpContent'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content_en': ('django.db.models.fields.TextField', [], {}),
            'content_fr': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'content_nt': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'name_en': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'name_fr': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'name_nt': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'ordering': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'core.historyentry': {
            'Meta': {'object_name': 'HistoryEntry'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_core.historyentry_set'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.User']"})
        },
        'core.language': {
            'Meta': {'object_name': 'Language'},
            'dj_code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '16'}),
            'duplicate_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Language']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            u'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            u'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['core.Language']"}),
            u'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            u'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'core.mailaccount': {
            'Meta': {'unique_together': "(('user', 'hostname', 'username'),)", 'object_name': 'MailAccount'},
            'conn_error': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_last_conn': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2007, 1, 1, 0, 0)'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_usable': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255', 'blank': 'True'}),
            'port': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'use_ssl': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'core.mailfeed': {
            'Meta': {'object_name': 'MailFeed', '_ormbases': ['core.BaseFeed']},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.MailAccount']", 'null': 'True', 'blank': 'True'}),
            u'basefeed_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.BaseFeed']", 'unique': 'True', 'primary_key': 'True'}),
            'finish_action': ('django.db.models.fields.CharField', [], {'default': "u'markread'", 'max_length': '10'}),
            'mailbox': ('django.db.models.fields.CharField', [], {'default': "u'INBOX'", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'match_action': ('django.db.models.fields.CharField', [], {'default': "u'scrape'", 'max_length': '10'}),
            'recurse_mailbox': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'rules_operation': ('django.db.models.fields.CharField', [], {'default': "u'any'", 'max_length': '10'}),
            'scrape_blacklist': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'scrape_whitelist': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'})
        },
        'core.mailfeedrule': {
            'Meta': {'ordering': "('group', 'position')", 'object_name': 'MailFeedRule'},
            'check_error': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255', 'blank': 'True'}),
            'clone_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.MailFeedRule']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'group_operation': ('django.db.models.fields.CharField', [], {'default': "u'any'", 'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'header_field': ('django.db.models.fields.CharField', [], {'default': "u'any'", 'max_length': '10'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_valid': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'mailfeed': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.MailFeed']"}),
            'match_case': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'match_type': ('django.db.models.fields.CharField', [], {'default': "u'contains'", 'max_length': '10'}),
            'match_value': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '1024'}),
            'other_header': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'})
        },
        'core.read': {
            'Meta': {'unique_together': "(('user', 'item'),)", 'object_name': 'Read'},
            'bookmark_type': ('django.db.models.fields.CharField', [], {'default': "u'U'", 'max_length': '2'}),
            'check_set_subscriptions_131004_done': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'date_analysis': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_archived': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_auto_read': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_bookmarked': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True'}),
            'date_fact': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_fun': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_knowhow': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_knowledge': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_number': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_prospective': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_quote': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_read': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_rules': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_starred': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_analysis': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_archived': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_auto_read': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_bookmarked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_fact': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_fun': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_good': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_knowhow': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_knowledge': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_number': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_prospective': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_quote': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_read': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_rules': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_starred': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'item': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.BaseItem']", 'unique': 'True'}),
            'knowledge_type': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'rating': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'senders': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'senders'", 'symmetrical': 'False', 'to': u"orm['base.User']"}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.SimpleTag']", 'symmetrical': 'False'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['base.User']", 'unique': 'True'})
        },
        'core.simpletag': {
            'Meta': {'unique_together': "(('name', 'language'),)", 'object_name': 'SimpleTag'},
            'duplicate_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.SimpleTag']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Language']", 'null': 'True'}),
            u'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            u'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'origin_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'origin_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['core.SimpleTag']"}),
            u'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            u'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'core.subscription': {
            'Meta': {'unique_together': "(('feed', 'user'),)", 'object_name': 'Subscription'},
            'feed': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.BaseFeed']", 'unique': 'True'}),
            'folders': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.Folder']", 'symmetrical': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'items': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.Read']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.SimpleTag']", 'symmetrical': 'False'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['base.User']", 'unique': 'True'})
        },
        'core.userimport': {
            'Meta': {'object_name': 'UserImport', '_ormbases': ['core.HistoryEntry']},
            'date_finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_started': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'historyentry_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.HistoryEntry']", 'unique': 'True', 'primary_key': 'True'}),
            'lines': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'results': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'urls': ('django.db.models.fields.TextField', [], {})
        },
        'core.website': {
            'Meta': {'object_name': 'WebSite'},
            'description_en': ('django.db.models.fields.TextField', [], {}),
            'description_fr': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_nt': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'duplicate_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.WebSite']"}),
            'fetch_limit_nr': ('django.db.models.fields.IntegerField', [], {'default': '16'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            u'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            u'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'mail_warned': ('jsonfield.fields.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['core.WebSite']"}),
            u'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'short_description_en': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'short_description_fr': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'short_description_nt': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'thumbnail': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'thumbnail_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200'})
        }
    }

    complete_apps = ['core']