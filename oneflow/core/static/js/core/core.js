
// NOTE: Django-pipeline will automatically "closurize" this file.

App = Ember.Application.create({
    LOG_TRANSITIONS: true
});

App.Store = DS.Store.extend({
  revision: 12,
  adapter: DS.DjangoTastypieAdapter.extend({
      namespace: 'api/v1'
      // namespace: (url_root + '/api/v1').replace(/^\//g, ''),

    })
});

App.Router.map(function(){
    this.resource('teams');
    this.resource('discovery');
    this.resource('subscriptions', function() {
        this.route('edit', { path: '/:subscription_id' });
    });
    this.resource('help');
})

// App.IndexRoute = Ember.Route.extend({
//     redirect: function() {
//         this.replaceWith('subscriptions');
//     }
// });
