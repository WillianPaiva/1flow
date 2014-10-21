# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'UserFeeds'
        db.create_table(u'core_userfeeds', (
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='feeds', unique=True, primary_key=True, to=orm['base.User'])),
            ('imported_items', self.gf('django.db.models.fields.related.OneToOneField')(blank=True, related_name='imported_items', unique=True, null=True, to=orm['core.BaseFeed'])),
            ('sent_items', self.gf('django.db.models.fields.related.OneToOneField')(blank=True, related_name='sent_items', unique=True, null=True, to=orm['core.BaseFeed'])),
            ('received_items', self.gf('django.db.models.fields.related.OneToOneField')(blank=True, related_name='received_items', unique=True, null=True, to=orm['core.BaseFeed'])),
            ('written_items', self.gf('django.db.models.fields.related.OneToOneField')(blank=True, related_name='written_items', unique=True, null=True, to=orm['core.BaseFeed'])),
        ))
        db.send_create_signal('core', ['UserFeeds'])

        # Adding M2M table for field blogs on 'UserFeeds'
        m2m_table_name = db.shorten_name(u'core_userfeeds_blogs')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('userfeeds', models.ForeignKey(orm['core.userfeeds'], null=False)),
            ('basefeed', models.ForeignKey(orm['core.basefeed'], null=False))
        ))
        db.create_unique(m2m_table_name, ['userfeeds_id', 'basefeed_id'])

        # Adding model 'UserSubscriptions'
        db.create_table(u'core_usersubscriptions', (
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='subscriptions', unique=True, primary_key=True, to=orm['base.User'])),
            ('imported_items', self.gf('django.db.models.fields.related.OneToOneField')(blank=True, related_name='imported_items', unique=True, null=True, to=orm['core.Subscription'])),
            ('sent_items', self.gf('django.db.models.fields.related.OneToOneField')(blank=True, related_name='sent_items', unique=True, null=True, to=orm['core.Subscription'])),
            ('received_items', self.gf('django.db.models.fields.related.OneToOneField')(blank=True, related_name='received_items', unique=True, null=True, to=orm['core.Subscription'])),
            ('written_items', self.gf('django.db.models.fields.related.OneToOneField')(blank=True, related_name='written_items', unique=True, null=True, to=orm['core.Subscription'])),
        ))
        db.send_create_signal('core', ['UserSubscriptions'])

        # Adding M2M table for field blogs on 'UserSubscriptions'
        m2m_table_name = db.shorten_name(u'core_usersubscriptions_blogs')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('usersubscriptions', models.ForeignKey(orm['core.usersubscriptions'], null=False)),
            ('subscription', models.ForeignKey(orm['core.subscription'], null=False))
        ))
        db.create_unique(m2m_table_name, ['usersubscriptions_id', 'subscription_id'])


    def backwards(self, orm):
        # Deleting model 'UserFeeds'
        db.delete_table(u'core_userfeeds')

        # Removing M2M table for field blogs on 'UserFeeds'
        db.delete_table(db.shorten_name(u'core_userfeeds_blogs'))

        # Deleting model 'UserSubscriptions'
        db.delete_table(u'core_usersubscriptions')

        # Removing M2M table for field blogs on 'UserSubscriptions'
        db.delete_table(db.shorten_name(u'core_usersubscriptions_blogs'))


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
            'hash_codes': ('jsonfield.fields.JSONField', [], {'default': "{'unsubscribe': 'a2a11d045c484d9cb16448cca4075f1d'}", 'blank': 'True'}),
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
            'publishers': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['base.User']", 'symmetrical': 'False', 'blank': 'True'}),
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
            'items': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.BaseItem']", 'symmetrical': 'False', 'blank': 'True'}),
            'languages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.Language']", 'symmetrical': 'False', 'blank': 'True'}),
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
            'sources': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'sources_rel_+'", 'blank': 'True', 'to': "orm['core.BaseItem']"}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.SimpleTag']", 'symmetrical': 'False', 'blank': 'True'}),
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
            'account': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['core.MailAccount']", 'null': 'True', 'blank': 'True'}),
            u'basefeed_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.BaseFeed']", 'unique': 'True', 'primary_key': 'True'}),
            'finish_action': ('django.db.models.fields.CharField', [], {'default': "u'markread'", 'max_length': '10'}),
            'match_action': ('django.db.models.fields.CharField', [], {'default': "u'scrape'", 'max_length': '10'}),
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
            'item': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.BaseItem']"}),
            'knowledge_type': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'rating': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'senders': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'senders'", 'symmetrical': 'False', 'to': u"orm['base.User']"}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.SimpleTag']", 'symmetrical': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.User']"})
        },
        'core.rssatomfeed': {
            'Meta': {'object_name': 'RssAtomFeed', '_ormbases': ['core.BaseFeed']},
            u'basefeed_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.BaseFeed']", 'unique': 'True', 'primary_key': 'True'}),
            'last_etag': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'last_modified': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.SimpleTag']", 'symmetrical': 'False', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200'}),
            'website': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.WebSite']", 'null': 'True', 'blank': 'True'})
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
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.BaseFeed']"}),
            'folders': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.Folder']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'items': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.Read']", 'symmetrical': 'False', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.SimpleTag']", 'symmetrical': 'False', 'blank': 'True'}),
            'thumbnail': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'thumbnail_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.User']"})
        },
        'core.userfeeds': {
            'Meta': {'object_name': 'UserFeeds'},
            'blogs': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['core.BaseFeed']", 'null': 'True', 'blank': 'True'}),
            'imported_items': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'imported_items'", 'unique': 'True', 'null': 'True', 'to': "orm['core.BaseFeed']"}),
            'received_items': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'received_items'", 'unique': 'True', 'null': 'True', 'to': "orm['core.BaseFeed']"}),
            'sent_items': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'sent_items'", 'unique': 'True', 'null': 'True', 'to': "orm['core.BaseFeed']"}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'feeds'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['base.User']"}),
            'written_items': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'written_items'", 'unique': 'True', 'null': 'True', 'to': "orm['core.BaseFeed']"})
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
        'core.usersubscriptions': {
            'Meta': {'object_name': 'UserSubscriptions'},
            'blogs': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'blogs'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['core.Subscription']"}),
            'imported_items': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'imported_items'", 'unique': 'True', 'null': 'True', 'to': "orm['core.Subscription']"}),
            'received_items': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'received_items'", 'unique': 'True', 'null': 'True', 'to': "orm['core.Subscription']"}),
            'sent_items': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'sent_items'", 'unique': 'True', 'null': 'True', 'to': "orm['core.Subscription']"}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'subscriptions'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['base.User']"}),
            'written_items': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'written_items'", 'unique': 'True', 'null': 'True', 'to': "orm['core.Subscription']"})
        },
        'core.website': {
            'Meta': {'object_name': 'WebSite'},
            'description_en': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_fr': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_nt': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'duplicate_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.WebSite']", 'null': 'True', 'blank': 'True'}),
            'fetch_limit_nr': ('django.db.models.fields.IntegerField', [], {'default': '16', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            u'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'mail_warned': ('jsonfield.fields.JSONField', [], {'default': "u'[]'", 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['core.WebSite']"}),
            u'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'short_description_en': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'short_description_fr': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'short_description_nt': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            u'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['core']