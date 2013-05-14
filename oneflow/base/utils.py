# -*- coding: utf-8 -*-

from django.template import RequestContext

from sparks.django import mail

from models import EmailContent


def send_email_with_db_content(request, email_template_name, user, **kwargs):

    def post_send(user, email_template_name):
        # TODO: implement me for real!
        #   I just wrote this function the way I wanted it to act,
        #   but user.log_email_sent() doesn't exist yet.

        def post_send_log_mail_sent():
            user.log_email_sent(email_template_name)

        return post_send_log_mail_sent

    email_data = EmailContent.objects.filter(name=email_template_name)

    mail.send_mail_html_from_template(
        'emails/email_with_db_content.html',
        subject=email_data.subject,
        recipients=[user.email],
        context=RequestContext(request, {
                               'email_subject': email_data.subject,
                               'email_body': email_data.body}),
        #post_send=post_send(user)
        **kwargs)
