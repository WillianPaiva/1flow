
from django.views.generic import ListView, TemplateView




class FeedDetailView(TemplateView):
    template_name = 'index/feed.html'

    def get_context_data(self, username, extra_context=None, *args, **kwargs):
        context = super(FeedDetailView, self).get_context_data(*args, **kwargs)

        user = get_object_or_404(get_user_model(),
                                 username__iexact=username)

        # Check perms
        #if not profile.can_view_profile(self.request.user):
        #    return HttpResponseForbidden(_("You don't have permission to view this profile."))

        if not self.request.user.mongo.is_st

        # context
        context['badges'] = badges

        return context
