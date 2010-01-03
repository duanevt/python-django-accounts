from django import template
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
import cgi

register = template.Library()

totals = {}
def rollup(arg=None, group="default"):
    if arg is None and group in totals:
        total = totals[group] or 0
        totals[group] = 0
        return total
    try:
        group = str(group)
        totals[group] += arg
    except:
        totals[group] = arg
    return arg
register.filter(rollup)

def rollup_subtotal(format, group="default"):
    try:
        group = str(group)
        retval = format % totals[group]
    except Exception, ex:
        retval = " - 0 - "
    return retval
register.simple_tag(rollup_subtotal)

def rollup_total(format, group="default"):
    try:
        group = str(group)
        retval = format % totals[group]
        totals[group] = 0
    except Exception, ex:
        retval = " - 0 - "
    return retval
register.simple_tag(rollup_total)
