# -*- coding: utf-8 -*-

from django import template
from django.template.base import Node, TemplateSyntaxError
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _

from sparks.foundations import utils as sfu

register = template.Library()


class FirstOfAsNode(Node):
    def __init__(self, args, variable_name=None):
        self.vars = args
        self.variable_name = variable_name

    def render(self, context):
        for var in self.vars:
            value = var.resolve(context, True)

            if value:
                if self.variable_name:
                    context[self.variable_name] = value
                    break

                else:
                    return smart_text(value)

        return ''


@register.tag
def firstofas(parser, token):
    """ Original idea: https://code.djangoproject.com/ticket/12199 """

    bits = token.split_contents()[1:]
    variable_name = None
    expecting_save_as = bits[-2] == 'as'

    if expecting_save_as:
        variable_name = bits.pop(-1)
        bits = bits[:-1]

    if len(bits) < 1:
        raise TemplateSyntaxError(
            "'firstofas' statement requires at least one argument")

    return FirstOfAsNode([parser.compile_filter(bit) for bit in bits],
                         variable_name)


@register.inclusion_tag('snippets/countdown.html')
def countdown(value, redirect=None, limit=0, show_seconds=True,
              format=None, spacer=None):
    """ From http://www.plus2net.com/javascript_tutorial/countdown.php """

    if redirect is None:
        redirect = '/'

    if limit > 0:
        operation    = '+'
        round_value  = 0
        counter_test = '<='

    else:
        operation    = '-'
        round_value  = 0        # WAS: 2
        counter_test = '>='

    if format is None or format == 'long':
        separator = ', '
        short     = False
        units     = {
            'day': _('day'),
            'days': _('days'),
            'hour': _('hour'),
            'hours': _('hours'),
            'minute': _('minute'),
            'minutes': _('minutes'),
            'second': _('second'),
            'seconds': _('seconds'),
        }

    elif format == 'abbr':
        separator = ' '
        short     = True
        units     = {
            'day': _('day'),
            'days': _('days'),
            'hour': _('hour'),
            'hours': _('hours'),
            'minute': _('min'),
            'minutes': _('mins'),
            'second': _('sec'),
            'seconds': _('secs'),
        }
    elif format == 'short':
        separator = ' '
        short     = True
        units     = {
            'day': _('d'),
            'days': _('d'),
            'hour': _('h'),
            'hours': _('h'),
            'minute': _('m'),
            'minutes': _('m'),
            'second': _('s'),
            'seconds': _('s'),
        }
    else:
        raise TemplateSyntaxError("'countdown' 'format' keyword argument "
                                  "must be either 'short', 'abbr' or 'long'")

    return {
        'name': sfu.unique_hash(only_letters=True),
        'units': units,
        'short': short,
        'value': value,
        'limit': limit,
        'unit_sep': ' ' if spacer is None else spacer,
        'redirect': redirect,
        'operation': operation,
        'separator': separator,
        'round_value': round_value,
        'show_seconds': show_seconds,
        'counter_test': counter_test,
    }
