# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Author.name'
        db.alter_column(u'core_author', 'name', self.gf('django.db.models.fields.CharField')(max_length=384, null=True))

        # Changing field 'Author.origin_name'
        db.alter_column(u'core_author', 'origin_name', self.gf('django.db.models.fields.CharField')(max_length=384))

    def backwards(self, orm):

        # Changing field 'Author.name'
        db.alter_column(u'core_author', 'name', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

        # Changing field 'Author.origin_name'
        db.alter_column(u'core_author', 'origin_name', self.gf('django.db.models.fields.CharField')(max_length=255))

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
            'hash_codes': ('jsonfield.fields.JSONField', [], {'default': "{'unsubscribe': '8f6cc0bd720c4cfcaea53ab8842d21d6'}", 'blank': 'True'}),
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
            'comments_feed_url': ('django.db.models.fields.URLField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'content_error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'date_published': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'is_orphaned': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'publishers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'publications'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['base.User']"}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '512'}),
            'url_absolute': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'url_error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'word_count': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'core.author': {
            'Meta': {'unique_together': "(('origin_name', 'website'),)", 'object_name': 'Author'},
            'duplicate_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Author']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_unsure': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '384', 'null': 'True', 'blank': 'True'}),
            'origin_name': ('django.db.models.fields.CharField', [], {'max_length': '384', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.User']", 'null': 'True', 'blank': 'True'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'authors'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['base.User']"}),
            'website': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.WebSite']", 'null': 'True', 'blank': 'True'})
        },
        'core.basefeed': {
            'Meta': {'object_name': 'BaseFeed'},
            'closed_reason': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'date_closed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_last_fetch': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'description_en': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_fr': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_nt': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'duplicate_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.BaseFeed']", 'null': 'True', 'blank': 'True'}),
            'errors': ('json_field.fields.JSONField', [], {'default': '[]', 'blank': 'True'}),
            'fetch_interval': ('django.db.models.fields.IntegerField', [], {'default': '43200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_good': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_internal': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_restricted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'items': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'feeds'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['core.BaseItem']"}),
            'languages': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'feeds'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['core.Language']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'options': ('json_field.fields.JSONField', [], {'default': '{}', 'blank': 'True'}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_core.basefeed_set'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            'short_description_en': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'short_description_fr': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'short_description_nt': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['core.SimpleTag']", 'null': 'True', 'blank': 'True'}),
            'thumbnail': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'thumbnail_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.User']", 'null': 'True', 'blank': 'True'})
        },
        'core.baseitem': {
            'Meta': {'object_name': 'BaseItem'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'authored_items'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['core.Author']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'default_rating': ('django.db.models.fields.FloatField', [], {'default': '0.0', 'blank': 'True'}),
            'duplicate_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.BaseItem']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_restricted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '5'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'origin': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_core.baseitem_set'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'sources': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'sources_rel_+'", 'null': 'True', 'to': "orm['core.BaseItem']"}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['core.SimpleTag']", 'null': 'True', 'blank': 'True'}),
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
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'folders'", 'to': u"orm['base.User']"})
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
        'core.helpwizards': {
            'Meta': {'object_name': 'HelpWizards'},
            'preferences': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'wizards'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['core.Preferences']"}),
            'show_all': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'welcome_beta_shown': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'core.historyentry': {
            'Meta': {'object_name': 'HistoryEntry'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_core.historyentry_set'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.User']"})
        },
        'core.homepreferences': {
            'Meta': {'object_name': 'HomePreferences'},
            'experimental_features': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'preferences': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'home'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['core.Preferences']"}),
            'read_shows': ('django.db.models.fields.IntegerField', [], {'default': '2', 'blank': 'True'}),
            'show_advanced_preferences': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'style': ('django.db.models.fields.CharField', [], {'default': "u'RL'", 'max_length': '2', 'blank': 'True'})
        },
        'core.language': {
            'Meta': {'object_name': 'Language'},
            'dj_code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '16'}),
            'duplicate_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Language']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            u'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            u'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
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
            'account': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'mail_feeds'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['core.MailAccount']"}),
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
        'core.nodepermissions': {
            'Meta': {'object_name': 'NodePermissions'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.SyncNode']", 'null': 'True', 'blank': 'True'}),
            'permission': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'default': "'c37f37d21dde4772bcc9316666ca7a4e'", 'max_length': '32', 'blank': 'True'})
        },
        'core.originaldata': {
            'Meta': {'object_name': 'OriginalData'},
            'feedparser': ('django.db.models.fields.TextField', [], {}),
            'feedparser_processed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'google_reader': ('django.db.models.fields.TextField', [], {}),
            'google_reader_processed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'item': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'original_data'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['core.BaseItem']"}),
            'raw_email': ('django.db.models.fields.TextField', [], {}),
            'raw_email_processed': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'core.preferences': {
            'Meta': {'object_name': 'Preferences'},
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['base.User']", 'unique': 'True', 'primary_key': 'True'})
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
            'item': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reads'", 'to': "orm['core.BaseItem']"}),
            'knowledge_type': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'rating': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'senders': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'reads_sent'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['base.User']"}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['core.SimpleTag']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'all_reads'", 'to': u"orm['base.User']"})
        },
        'core.readpreferences': {
            'Meta': {'object_name': 'ReadPreferences'},
            'auto_mark_read_delay': ('django.db.models.fields.IntegerField', [], {'default': '4500', 'blank': 'True'}),
            'bookmarked_marks_archived': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'bookmarked_marks_unread': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'preferences': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'read'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['core.Preferences']"}),
            'read_switches_to_fullscreen': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'reading_speed': ('django.db.models.fields.IntegerField', [], {'default': '200', 'blank': 'True'}),
            'show_bottom_navbar': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'starred_marks_archived': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'starred_marks_read': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'starred_removes_bookmarked': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'watch_attributes_mark_archived': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'core.rssatomfeed': {
            'Meta': {'object_name': 'RssAtomFeed', '_ormbases': ['core.BaseFeed']},
            u'basefeed_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.BaseFeed']", 'unique': 'True', 'primary_key': 'True'}),
            'last_etag': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'last_modified': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200'}),
            'website': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'feeds'", 'null': 'True', 'to': "orm['core.WebSite']"})
        },
        'core.selectorpreferences': {
            'Meta': {'object_name': 'SelectorPreferences'},
            'extended_folders_depth': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'folders_show_unread_count': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'lists_show_unread_count': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'preferences': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'selector'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['core.Preferences']"}),
            'show_closed_streams': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subscriptions_in_multiple_folders': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'titles_show_unread_count': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'core.sharepreferences': {
            'Meta': {'object_name': 'SharePreferences'},
            'default_message': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'preferences': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'share'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['core.Preferences']"})
        },
        'core.simpletag': {
            'Meta': {'unique_together': "(('name', 'language'),)", 'object_name': 'SimpleTag'},
            'duplicate_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.SimpleTag']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Language']", 'null': 'True'}),
            u'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            u'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'origin_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'origin_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['core.SimpleTag']"}),
            u'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            u'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'core.snappreferences': {
            'Meta': {'object_name': 'SnapPreferences'},
            'default_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'preferences': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'snap'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['core.Preferences']"}),
            'select_paragraph': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'core.staffpreferences': {
            'Meta': {'object_name': 'StaffPreferences'},
            'allow_all_articles': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'no_home_redirect': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'preferences': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'staff'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['core.Preferences']"}),
            'reading_lists_show_bad_articles': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'selector_shows_admin_links': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'super_powers_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'core.subscription': {
            'Meta': {'unique_together': "(('feed', 'user'),)", 'object_name': 'Subscription'},
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'subscriptions'", 'blank': 'True', 'to': "orm['core.BaseFeed']"}),
            'folders': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'subscriptions'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['core.Folder']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'reads': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'subscriptions'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['core.Read']"}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['core.SimpleTag']", 'null': 'True', 'blank': 'True'}),
            'thumbnail': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'thumbnail_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'all_subscriptions'", 'blank': 'True', 'to': u"orm['base.User']"})
        },
        'core.syncnode': {
            'Meta': {'object_name': 'SyncNode'},
            'broadcast': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_last_seen': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_local_instance': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'local_token': ('django.db.models.fields.CharField', [], {'default': "'f3c46760998043d2bf661f97943aeff9'", 'max_length': '32', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '384', 'null': 'True', 'blank': 'True'}),
            'permission': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'remote_token': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '-1', 'blank': 'True'}),
            'strategy': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'sync_error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'uri': ('django.db.models.fields.CharField', [], {'max_length': '384', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'c5f8982508ff41d483b8b0222708fc00'", 'unique': 'True', 'max_length': '32', 'blank': 'True'})
        },
        'core.userfeeds': {
            'Meta': {'object_name': 'UserFeeds'},
            'blogs': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['core.BaseFeed']", 'null': 'True', 'blank': 'True'}),
            'imported_items': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'imported_items_user_feed'", 'unique': 'True', 'null': 'True', 'to': "orm['core.BaseFeed']"}),
            'received_items': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'received_items_user_feed'", 'unique': 'True', 'null': 'True', 'to': "orm['core.BaseFeed']"}),
            'sent_items': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'sent_items_user_feed'", 'unique': 'True', 'null': 'True', 'to': "orm['core.BaseFeed']"}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'user_feeds'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['base.User']"}),
            'written_items': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'written_items_user_feed'", 'unique': 'True', 'null': 'True', 'to': "orm['core.BaseFeed']"})
        },
        'core.userimport': {
            'Meta': {'object_name': 'UserImport', '_ormbases': ['core.HistoryEntry']},
            'date_finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_started': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'historyentry_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.HistoryEntry']", 'unique': 'True', 'primary_key': 'True'}),
            'lines': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'results': ('json_field.fields.JSONField', [], {'default': '{}', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'urls': ('django.db.models.fields.TextField', [], {})
        },
        'core.usersubscriptions': {
            'Meta': {'object_name': 'UserSubscriptions'},
            'blogs': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'blogs'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['core.Subscription']"}),
            'imported_items': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'imported_items_user_subscriptions'", 'unique': 'True', 'null': 'True', 'to': "orm['core.Subscription']"}),
            'received_items': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'received_items_user_subscriptions'", 'unique': 'True', 'null': 'True', 'to': "orm['core.Subscription']"}),
            'sent_items': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'sent_items_user_subscriptions'", 'unique': 'True', 'null': 'True', 'to': "orm['core.Subscription']"}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'user_subscriptions'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['base.User']"}),
            'written_items': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'written_items_user_subscriptions'", 'unique': 'True', 'null': 'True', 'to': "orm['core.Subscription']"})
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
            'mail_warned': ('json_field.fields.JSONField', [], {'default': '[]', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['core.WebSite']"}),
            u'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'short_description_en': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'short_description_fr': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'short_description_nt': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            u'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['core']