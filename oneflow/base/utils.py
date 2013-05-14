# -*- coding: utf-8 -*-

import logging

from django.template import RequestContext, Template

from sparks.django import mail

from models import EmailContent

LOGGER = logging.getLogger(__name__)


def send_email_with_db_content(request, email_template_name, **kwargs):
    """

        :param kwargs: can contain ``new_user`` in case of a new user
            registration.
    """

    def post_send(user, email_template_name):
        # TODO: implement me for real!
        #   I just wrote this function the way I wanted it to act,
        #   but user.log_email_sent() doesn't exist yet.

        def post_send_log_mail_sent():
            user.log_email_sent(email_template_name)

        return post_send_log_mail_sent

    # If there is no new user, it's not a registration, we
    # just get the request user, to fill email fields.
    user = kwargs.pop('new_user', request.user)

    # Prepare for the first rendering pass (Django)
    request_context = RequestContext(request, {'new_user': user})
    email_data      = EmailContent.objects.get(name=email_template_name)

    # Pre-render templates for the mail HTML content.
    # email subject is mapped to <title> and <h1>.
    stemplate     = Template(email_data.subject)
    email_subject = stemplate.render(request_context)
    btemplate     = Template(email_data.body)
    email_body    = btemplate.render(request_context)

    # Update for the second rendering pass (Markdown in Django)
    request_context.update({'email_subject': email_subject,
                           'email_body': email_body, })

    mail.send_mail_html_from_template(
        'emails/email_with_db_content.html',
        # We intentionaly pass the unrendered subject string,
        # because it will be rendered independantly in the
        # send_mail… function (cf. there for details).
        subject=email_data.subject,
        recipients=[user.email],
        context=request_context,
        #post_send=post_send(user)
        **kwargs)

    LOGGER.info('Batched %s mail to send to %s.',
                email_template_name, user.email)
