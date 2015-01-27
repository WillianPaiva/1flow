# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'ProcessorChain'
        db.delete_table(u'core_processorchain')

        # Removing M2M table for field applies_on on 'ProcessorChain'
        db.delete_table(db.shorten_name(u'core_processorchain_applies_on'))

        # Deleting model 'ChainedProcessor'
        db.delete_table(u'core_chainedprocessor')

        # Adding model 'ProcessingChain'
        db.create_table(u'core_processingchain', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('duplicate_of', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.ProcessingChain'], null=True, blank=True)),
            ('duplicate_status', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('slug', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='processor_chains', null=True, to=orm['base.User'])),
            ('parent', self.gf('mptt.fields.TreeForeignKey')(blank=True, related_name='children', null=True, to=orm['core.ProcessingChain'])),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('short_description_en', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('short_description_fr', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('short_description_nt', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('description_en', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('description_fr', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('description_nt', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            (u'lft', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            (u'rght', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            (u'tree_id', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            (u'level', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
        ))
        db.send_create_signal('core', ['ProcessingChain'])

        # Adding M2M table for field applies_on on 'ProcessingChain'
        m2m_table_name = db.shorten_name(u'core_processingchain_applies_on')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('processingchain', models.ForeignKey(orm['core.processingchain'], null=False)),
            ('contenttype', models.ForeignKey(orm[u'contenttypes.contenttype'], null=False))
        ))
        db.create_unique(m2m_table_name, ['processingchain_id', 'contenttype_id'])

        # Adding model 'ChainedItem'
        db.create_table(u'core_chaineditem', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('chain', self.gf('django.db.models.fields.related.ForeignKey')(related_name='processors', to=orm['core.ProcessingChain'])),
            ('item_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True, blank=True)),
            ('item_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('position', self.gf('django.db.models.fields.IntegerField')(default=0, blank=True)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('parameters', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('is_valid', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('check_error', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('notes_en', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('notes_fr', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('notes_nt', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('core', ['ChainedItem'])


        # Changing field 'ProcessingError.processor'
        db.alter_column(u'core_processingerror', 'processor_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.ChainedItem']))

    def backwards(self, orm):
        # Adding model 'ProcessorChain'
        db.create_table(u'core_processorchain', (
            ('short_description_en', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            (u'rght', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('duplicate_of', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.ProcessorChain'], null=True, blank=True)),
            ('parent', self.gf('mptt.fields.TreeForeignKey')(related_name='children', null=True, to=orm['core.ProcessorChain'], blank=True)),
            (u'level', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('description_nt', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('short_description_nt', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            (u'tree_id', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('description_en', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True)),
            (u'lft', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='processor_chains', null=True, to=orm['base.User'], blank=True)),
            ('description_fr', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('short_description_fr', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('duplicate_status', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal('core', ['ProcessorChain'])

        # Adding M2M table for field applies_on on 'ProcessorChain'
        m2m_table_name = db.shorten_name(u'core_processorchain_applies_on')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('processorchain', models.ForeignKey(orm['core.processorchain'], null=False)),
            ('contenttype', models.ForeignKey(orm[u'contenttypes.contenttype'], null=False))
        ))
        db.create_unique(m2m_table_name, ['processorchain_id', 'contenttype_id'])

        # Adding model 'ChainedProcessor'
        db.create_table(u'core_chainedprocessor', (
            ('chain', self.gf('django.db.models.fields.related.ForeignKey')(related_name='processors', to=orm['core.ProcessorChain'])),
            ('notes_fr', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('check_error', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('notes_en', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('parameters', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('is_valid', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('notes_nt', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('position', self.gf('django.db.models.fields.IntegerField')(default=0, blank=True)),
            ('processor', self.gf('django.db.models.fields.related.ForeignKey')(related_name='chains', to=orm['core.Processor'])),
        ))
        db.send_create_signal('core', ['ChainedProcessor'])

        # Deleting model 'ProcessingChain'
        db.delete_table(u'core_processingchain')

        # Removing M2M table for field applies_on on 'ProcessingChain'
        db.delete_table(db.shorten_name(u'core_processingchain_applies_on'))

        # Deleting model 'ChainedItem'
        db.delete_table(u'core_chaineditem')


        # Changing field 'ProcessingError.processor'
        db.alter_column(u'core_processingerror', 'processor_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.ChainedProcessor']))

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
            'address_book': ('json_field.fields.JSONField', [], {'default': '[]', 'blank': 'True'}),
            'avatar': ('django.db.models.fields.files.ImageField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'avatar_url': ('django.db.models.fields.URLField', [], {'max_length': '384', 'null': 'True', 'blank': 'True'}),
            'data': ('jsonfield.fields.JSONField', [], {'default': '{}', 'blank': 'True'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '254', 'db_index': 'True'}),
            'email_announcements': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            'hash_codes': ('jsonfield.fields.JSONField', [], {'default': "{'unsubscribe': 'cb1f8c3a44d44b868a95aeb577972883'}", 'blank': 'True'}),
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
            'content_type': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'is_orphaned': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'publishers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'publications'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['base.User']"}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '512'}),
            'url_absolute': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'url_error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'version_description': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'word_count': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'core.author': {
            'Meta': {'unique_together': "(('origin_name', 'website'),)", 'object_name': 'Author'},
            'duplicate_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Author']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identities': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'identities_rel_+'", 'null': 'True', 'to': "orm['core.Author']"}),
            'is_unsure': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '7168', 'null': 'True', 'blank': 'True'}),
            'origin_id': ('django.db.models.fields.BigIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'origin_id_str': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'origin_name': ('django.db.models.fields.CharField', [], {'max_length': '7168', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'authors'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['base.User']"}),
            'website': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.WebSite']", 'null': 'True', 'blank': 'True'}),
            'website_data': ('json_field.fields.JSONField', [], {'default': '{}', 'blank': 'True'})
        },
        'core.baseaccount': {
            'Meta': {'object_name': 'BaseAccount'},
            'conn_error': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_last_conn': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'max_length': '384', 'null': 'True', 'blank': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_usable': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'options': ('json_field.fields.JSONField', [], {'default': '{}', 'blank': 'True'}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_core.baseaccount_set'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'accounts'", 'to': u"orm['base.User']"})
        },
        'core.basefeed': {
            'Meta': {'object_name': 'BaseFeed'},
            'closed_reason': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'date_closed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_last_fetch': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'description_en': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_fr': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_nt': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'duplicate_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.BaseFeed']", 'null': 'True', 'blank': 'True'}),
            'duplicate_status': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'errors': ('json_field.fields.JSONField', [], {'default': '[]', 'blank': 'True'}),
            'fetch_interval': ('django.db.models.fields.IntegerField', [], {'default': '43200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_good': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'is_internal': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_restricted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'items': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'feeds'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['core.BaseItem']"}),
            'languages': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['core.Language']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'options': ('json_field.fields.JSONField', [], {'default': '{}', 'blank': 'True'}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_core.basefeed_set'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            'short_description_en': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'short_description_fr': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'short_description_nt': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['core.SimpleTag']", 'null': 'True', 'blank': 'True'}),
            'thumbnail': ('django.db.models.fields.files.ImageField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'thumbnail_url': ('django.db.models.fields.URLField', [], {'max_length': '384', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'feeds'", 'null': 'True', 'to': u"orm['base.User']"})
        },
        'core.baseitem': {
            'Meta': {'object_name': 'BaseItem'},
            'authors': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'authored_items'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['core.Author']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'date_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'default_rating': ('django.db.models.fields.FloatField', [], {'default': '0.0', 'blank': 'True'}),
            'duplicate_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.BaseItem']", 'null': 'True', 'blank': 'True'}),
            'duplicate_status': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_restricted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Language']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'origin': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_core.baseitem_set'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'sources': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'sources_rel_+'", 'null': 'True', 'to': "orm['core.BaseItem']"}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['core.SimpleTag']", 'null': 'True', 'blank': 'True'}),
            'text_direction': ('django.db.models.fields.CharField', [], {'default': "u'ltr'", 'max_length': '3', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.User']", 'null': 'True', 'blank': 'True'})
        },
        'core.chaineditem': {
            'Meta': {'object_name': 'ChainedItem'},
            'chain': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'processors'", 'to': "orm['core.ProcessingChain']"}),
            'check_error': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_valid': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'item_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'item_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'notes_en': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'notes_fr': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'notes_nt': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'parameters': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'})
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
        'core.folder': {
            'Meta': {'unique_together': "(('name', 'user', 'parent'),)", 'object_name': 'Folder'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'max_length': '384', 'null': 'True', 'blank': 'True'}),
            u'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            u'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['core.Folder']"}),
            u'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
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
        u'core.historicalarticle': {
            'Meta': {'ordering': "(u'-history_date', u'-history_id')", 'object_name': 'HistoricalArticle'},
            u'baseitem_ptr_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'comments_feed_url': ('django.db.models.fields.URLField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'content_error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'blank': 'True'}),
            'date_published': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'date_updated': ('django.db.models.fields.DateTimeField', [], {'blank': 'True'}),
            'default_rating': ('django.db.models.fields.FloatField', [], {'default': '0.0', 'blank': 'True'}),
            'duplicate_of_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'duplicate_status': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'excerpt': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'history_date': ('django.db.models.fields.DateTimeField', [], {}),
            u'history_id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            u'history_type': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            u'history_user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.User']", 'null': 'True'}),
            u'id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'is_orphaned': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_restricted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'language_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'origin': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'polymorphic_ctype_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'text_direction': ('django.db.models.fields.CharField', [], {'default': "u'ltr'", 'max_length': '3', 'db_index': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '512', 'db_index': 'True'}),
            'url_absolute': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'url_error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'user_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'version_description': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'word_count': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
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
            'duplicate_status': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'iso639_1': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'iso639_2': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'iso639_3': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            u'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            u'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['core.Language']"}),
            u'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            u'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'core.mailaccount': {
            'Meta': {'object_name': 'MailAccount', '_ormbases': ['core.BaseAccount']},
            u'baseaccount_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.BaseAccount']", 'unique': 'True', 'primary_key': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255', 'blank': 'True'}),
            'port': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'use_ssl': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'core.mailfeed': {
            'Meta': {'object_name': 'MailFeed', '_ormbases': ['core.BaseFeed']},
            'account': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'mail_feeds'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['core.MailAccount']"}),
            u'basefeed_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.BaseFeed']", 'unique': 'True', 'primary_key': 'True'}),
            'finish_action': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'match_action': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'rules_operation': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'scrape_blacklist': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'scrape_whitelist': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'})
        },
        'core.mailfeedrule': {
            'Meta': {'ordering': "('group', 'position')", 'object_name': 'MailFeedRule'},
            'check_error': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'clone_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.MailFeedRule']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'group_operation': ('django.db.models.fields.IntegerField', [], {'default': '1', 'blank': 'True'}),
            'header_field': ('django.db.models.fields.IntegerField', [], {'default': '4', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_valid': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'mailfeed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'rules'", 'to': "orm['core.MailFeed']"}),
            'match_case': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'match_type': ('django.db.models.fields.IntegerField', [], {'default': '1', 'blank': 'True'}),
            'match_value': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'other_header': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'})
        },
        'core.nodepermissions': {
            'Meta': {'object_name': 'NodePermissions'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.SyncNode']", 'null': 'True', 'blank': 'True'}),
            'permission': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'default': "'32c8727d60be4aeb874a3eb4adff867a'", 'max_length': '32', 'blank': 'True'})
        },
        'core.originaldata': {
            'Meta': {'object_name': 'OriginalData'},
            'feedparser': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'feedparser_processed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'google_reader': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'google_reader_processed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'item': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'original_data'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['core.BaseItem']"}),
            'raw_email': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'raw_email_processed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'twitter': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'twitter_processed': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'core.preferences': {
            'Meta': {'object_name': 'Preferences'},
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['base.User']", 'unique': 'True', 'primary_key': 'True'})
        },
        'core.processingchain': {
            'Meta': {'object_name': 'ProcessingChain'},
            'applies_on': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'description_en': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_fr': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_nt': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'duplicate_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.ProcessingChain']", 'null': 'True', 'blank': 'True'}),
            'duplicate_status': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            u'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['core.ProcessingChain']"}),
            u'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'short_description_en': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'short_description_fr': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'short_description_nt': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            u'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'processor_chains'", 'null': 'True', 'to': u"orm['base.User']"})
        },
        'core.processingerror': {
            'Meta': {'object_name': 'ProcessingError'},
            'data': ('json_field.fields.JSONField', [], {'default': '{}', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'exception': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'instance_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'issue_ref': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'processor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'errors'", 'to': "orm['core.ChainedItem']"})
        },
        'core.processor': {
            'Meta': {'object_name': 'Processor'},
            'accept_code': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'description_en': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_fr': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_nt': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'duplicate_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Processor']", 'null': 'True', 'blank': 'True'}),
            'duplicate_status': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            u'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'needs_parameters': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['core.Processor']"}),
            'process_code': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'processor_type': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'requirements': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'short_description_en': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'short_description_fr': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'short_description_nt': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'source_address': ('django.db.models.fields.CharField', [], {'max_length': '384', 'null': 'True', 'blank': 'True'}),
            u'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'processors'", 'null': 'True', 'to': u"orm['base.User']"})
        },
        'core.read': {
            'Meta': {'unique_together': "(('user', 'item'),)", 'object_name': 'Read'},
            'bookmark_type': ('django.db.models.fields.CharField', [], {'default': "u'U'", 'max_length': '2'}),
            'check_set_subscriptions_131004_done': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'date_analysis': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_archived': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_auto_read': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_bookmarked': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
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
            'is_bookmarked': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'is_fact': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_fun': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_good': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'is_knowhow': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_knowledge': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_number': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_prospective': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_quote': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'is_rules': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_starred': ('django.db.models.fields.NullBooleanField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
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
            'last_etag': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'last_modified': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '512'}),
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
            'duplicate_status': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Language']", 'null': 'True', 'blank': 'True'}),
            u'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            u'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'origin_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'origin_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['core.SimpleTag']"}),
            u'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'}),
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
            'no_home_redirect': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'preferences': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'staff'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['core.Preferences']"}),
            'reading_lists_show_bad_articles': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'selector_shows_admin_links': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'super_powers_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'core.subscription': {
            'Meta': {'unique_together': "(('feed', 'user'),)", 'object_name': 'Subscription'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'subscriptions'", 'blank': 'True', 'to': "orm['core.BaseFeed']"}),
            'folders': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'subscriptions'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['core.Folder']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'reads': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'subscriptions'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['core.Read']"}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['core.SimpleTag']", 'null': 'True', 'blank': 'True'}),
            'thumbnail': ('django.db.models.fields.files.ImageField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'thumbnail_url': ('django.db.models.fields.URLField', [], {'max_length': '384', 'null': 'True', 'blank': 'True'}),
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
            'local_token': ('django.db.models.fields.CharField', [], {'default': "'74f57dfb36cb4b5dad1774a263cc6c53'", 'max_length': '32', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '384', 'null': 'True', 'blank': 'True'}),
            'permission': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'remote_token': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '-1', 'blank': 'True'}),
            'strategy': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'sync_error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'uri': ('django.db.models.fields.CharField', [], {'max_length': '384', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['base.User']", 'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '32', 'null': 'True', 'blank': 'True'})
        },
        'core.tweet': {
            'Meta': {'object_name': 'Tweet', '_ormbases': ['core.BaseItem']},
            u'baseitem_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.BaseItem']", 'unique': 'True', 'primary_key': 'True'}),
            'entities': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'tweets'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['core.BaseItem']"}),
            'entities_fetched': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'mentions': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'mentions'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['core.Author']"}),
            'tweet_id': ('django.db.models.fields.BigIntegerField', [], {'db_index': 'True', 'unique': 'True', 'blank': 'True'})
        },
        'core.twitteraccount': {
            'Meta': {'object_name': 'TwitterAccount', '_ormbases': ['core.BaseAccount']},
            u'baseaccount_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.BaseAccount']", 'unique': 'True', 'primary_key': 'True'}),
            'fetch_owned_lists': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'fetch_subscribed_lists': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'social_auth': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'twitter_account'", 'unique': 'True', 'to': u"orm['default.UserSocialAuth']"}),
            'timeline': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'twitter_account'", 'unique': 'True', 'null': 'True', 'to': "orm['core.TwitterFeed']"})
        },
        'core.twitterfeed': {
            'Meta': {'object_name': 'TwitterFeed', '_ormbases': ['core.BaseFeed']},
            'account': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'twitter_feeds'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['core.TwitterAccount']"}),
            'backfill_completed': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            u'basefeed_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.BaseFeed']", 'unique': 'True', 'primary_key': 'True'}),
            'finish_action': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'is_backfilled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_timeline': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'match_action': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'rules_operation': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'scrape_blacklist': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'scrape_whitelist': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'track_locations': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'track_terms': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'uri': ('django.db.models.fields.CharField', [], {'max_length': '255', 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        'core.twitterfeedrule': {
            'Meta': {'ordering': "('group', 'position')", 'object_name': 'TwitterFeedRule'},
            'check_error': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'clone_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.TwitterFeedRule']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'group_operation': ('django.db.models.fields.IntegerField', [], {'default': '1', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_valid': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'match_case': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'match_field': ('django.db.models.fields.IntegerField', [], {'default': '1', 'blank': 'True'}),
            'match_type': ('django.db.models.fields.IntegerField', [], {'default': '1', 'blank': 'True'}),
            'match_value': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'other_field': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'position': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'twitterfeed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'rules'", 'to': "orm['core.TwitterFeed']"})
        },
        'core.usercounters': {
            'Meta': {'object_name': 'UserCounters'},
            'placeholder': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'user_counters'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['base.User']"})
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
            'duplicate_status': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'fetch_limit_nr': ('django.db.models.fields.IntegerField', [], {'default': '16', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.URLField', [], {'max_length': '384', 'null': 'True', 'blank': 'True'}),
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
        },
        u'default.usersocialauth': {
            'Meta': {'unique_together': "(('provider', 'uid'),)", 'object_name': 'UserSocialAuth', 'db_table': "'social_auth_usersocialauth'"},
            'extra_data': ('social.apps.django_app.default.fields.JSONField', [], {'default': "'{}'"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'uid': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'social_auth'", 'to': u"orm['base.User']"})
        }
    }

    complete_apps = ['core']