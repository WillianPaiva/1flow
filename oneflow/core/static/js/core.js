App = Ember.Application.create({
    LOG_TRANSITIONS: true
});

App.Store = DS.Store.extend({
  revision: 12
});

App.Router.map(function(){
    this.resource('teams');
    this.resource('notimpl');
    this.resource('help');
})

Ember.Handlebars.registerBoundHelper('fromNow', function(date){
    console.log(date + " " + moment(date, "YYYYMMDD").fromNow());
    return moment(date, "YYYYMMDD").fromNow();
});
