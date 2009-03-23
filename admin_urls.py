from django.conf.urls.defaults import *
from solardev.enrollment.invoice_views import *

urlpatterns = patterns('',
    (r'invoice/(?P<invoice>\d+)/cancel-fees/', cancel_fees),
    (r'invoice/(?P<invoice>\d+)/add-enrollment/', add_enrollment),
)
