from django import template
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
import cgi

register = template.Library()

totals = {}
def rollup(arg, group="default"):
	try:
		totals[group] += arg
	except:
		totals[group] = arg
	return arg
register.filter(rollup)

def rollup_total(format, group="default"):
	try:
		retval = format % totals[group]
		totals[group] = 0
	except Exception, ex:
		retval = "%s: - 0 - " % ex
	return retval
register.simple_tag(rollup_total)
