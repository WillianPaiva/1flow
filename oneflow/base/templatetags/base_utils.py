# -*- coding: utf-8 -*-

from django import template
from django.template.base import Node, TemplateSyntaxError
from django.utils.encoding import smart_text

register = template.Library()


class FirstOfAsNode(Node):
    def __init__(self, vars, variable_name=None):
        self.vars = vars
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


@register.tag(name="firstofas")
def do_firstofas(parser, token):
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
