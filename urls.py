from django.conf.urls.defaults import *
from views import *

urlpatterns = patterns('',
    url(r'^journal/', journal, name="accounts-journal"),
    url(r'^ledger/(?P<id>\d+)/', ledger, name="accounts-ledger"),
    url(r'^', summary, name="accounts-summary"),
)
