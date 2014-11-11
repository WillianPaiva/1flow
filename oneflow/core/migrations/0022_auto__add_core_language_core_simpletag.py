# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        db.create_table(u'core_language', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('dj_code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=16)),
            ('duplicate_of', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Language'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),

            ('parent', self.gf('mptt.fields.TreeForeignKey')(blank=True, related_name='children', null=True, to=orm['core.Language'])),
            (u'lft', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            (u'rght', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            (u'tree_id', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            (u'level', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
        ))
        db.send_create_signal('core', ['Language'])

        db.create_table(u'core_simpletag', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('duplicate_of', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.SimpleTag'])),
            ('language', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['core.Language'])),
            ('slug', self.gf('django.db.models.fields.CharField')(max_length=128, null=True)),
            ('origin_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('origin_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),

            ('parent', self.gf('mptt.fields.TreeForeignKey')(blank=True, related_name='children', null=True, to=orm['core.SimpleTag'])),
            (u'lft', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            (u'rght', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            (u'tree_id', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            (u'level', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
        ))

        db.send_create_signal('core', ['SimpleTag'])
        db.create_unique(u'core_simpletag', ['name', 'language_id', ])

    def backwards(self, orm):
        # Deleting model 'UserImport'
        db.delete_table(u'core_language')
        db.delete_table(u'core_simpletag')

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
            'hash_codes': ('jsonfield.fields.JSONField', [], {'default': "{'unsubscribe': '389dbb2a0c314828a5f1ba140fbca691'}", 'blank': 'True'}),
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
        'core.corepermissions': {
            'Meta': {'object_name': 'CorePermissions'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
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
            'Meta': {'object_name': 'MailFeed'},
            'finish_action': ('django.db.models.fields.CharField', [], {'default': "u'markread'", 'max_length': '10'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'match_action': ('django.db.models.fields.CharField', [], {'default': "u'scrape'", 'max_length': '10'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'scrape_blacklist': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'scrape_whitelist': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.User']"})
        },
        'core.mailfeedrule': {
            'Meta': {'ordering': "('position',)", 'object_name': 'MailFeedRule'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.MailAccount']", 'null': 'True', 'blank': 'True'}),
            'check_error': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255', 'blank': 'True'}),
            'clone_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.MailFeedRule']", 'null': 'True', 'blank': 'True'}),
            'finish_action': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'header_field': ('django.db.models.fields.CharField', [], {'default': "u'any'", 'max_length': '10'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_valid': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'mailbox': ('django.db.models.fields.CharField', [], {'default': "u'INBOX'", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'mailfeed': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.MailFeed']"}),
            'match_action': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'match_case': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'match_type': ('django.db.models.fields.CharField', [], {'default': "u'contains'", 'max_length': '10'}),
            'match_value': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '1024'}),
            'other_header': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'recurse_mailbox': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
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
        'core.userimport': {
            'Meta': {'object_name': 'UserImport'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now_add': 'True', 'blank': 'True'}),
            'date_finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_started': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lines': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'messages': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'results': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'urls': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.User']"})
        }
    }

    complete_apps = ['core']
