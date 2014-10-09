# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'MailFeed'
        db.create_table(u'core_mailfeed', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('core', ['MailFeed'])

        # Adding model 'MailAccount'
        db.create_table(u'core_mailaccount', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['base.User'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('hostname', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('use_ssl', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('port', self.gf('django.db.models.fields.IntegerField')()),
            ('username', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
        ))
        db.send_create_signal('core', ['MailAccount'])

        # Adding unique constraint on 'MailAccount', fields ['user', 'hostname', 'username']
        db.create_unique(u'core_mailaccount', ['user_id', 'hostname', 'username'])

        # Adding model 'MailFeedRuleLine'
        db.create_table(u'core_mailfeedruleline', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('rule', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.MailFeedRule'])),
            ('header_field', self.gf('django.db.models.fields.CharField')(default=u'any', max_length=10)),
            ('other_header', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('match_type', self.gf('django.db.models.fields.CharField')(default=u'contains', max_length=10)),
            ('match_value', self.gf('django.db.models.fields.TextField')(max_length=255)),
        ))
        db.send_create_signal('core', ['MailFeedRuleLine'])

        # Adding model 'MailFeedRule'
        db.create_table(u'core_mailfeedrule', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('mailfeed', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.MailFeed'])),
            ('account', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.MailAccount'], null=True)),
        ))
        db.send_create_signal('core', ['MailFeedRule'])


    def backwards(self, orm):
        # Removing unique constraint on 'MailAccount', fields ['user', 'hostname', 'username']
        db.delete_unique(u'core_mailaccount', ['user_id', 'hostname', 'username'])

        # Deleting model 'MailFeed'
        db.delete_table(u'core_mailfeed')

        # Deleting model 'MailAccount'
        db.delete_table(u'core_mailaccount')

        # Deleting model 'MailFeedRuleLine'
        db.delete_table(u'core_mailfeedruleline')

        # Deleting model 'MailFeedRule'
        db.delete_table(u'core_mailfeedrule')


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
            'hash_codes': ('jsonfield.fields.JSONField', [], {'default': "{'unsubscribe': 'ab37bd359cb94d76a8953676d7afbb81'}", 'blank': 'True'}),
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
        'core.mailaccount': {
            'Meta': {'unique_together': "(('user', 'hostname', 'username'),)", 'object_name': 'MailAccount'},
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'port': ('django.db.models.fields.IntegerField', [], {}),
            'use_ssl': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'})
        },
        'core.mailfeed': {
            'Meta': {'object_name': 'MailFeed'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'core.mailfeedrule': {
            'Meta': {'object_name': 'MailFeedRule'},
            'account': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.MailAccount']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mailfeed': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.MailFeed']"})
        },
        'core.mailfeedruleline': {
            'Meta': {'object_name': 'MailFeedRuleLine'},
            'header_field': ('django.db.models.fields.CharField', [], {'default': "u'any'", 'max_length': '10'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'match_type': ('django.db.models.fields.CharField', [], {'default': "u'contains'", 'max_length': '10'}),
            'match_value': ('django.db.models.fields.TextField', [], {'max_length': '255'}),
            'other_header': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'rule': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.MailFeedRule']"})
        }
    }

    complete_apps = ['core']