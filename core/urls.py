from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.home, name='home'),

    # login / logout urls
    url(r'^login/$', 'django.contrib.auth.views.login', name='login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout_then_login', name='logout'),

    url(r'^studies/$', views.studies, name='studies'),
    url(r'^studies/assessements/$', views.assessements, name='assessements'),
    url(r'^studies/assessements/scores_encoding$', views.scores_encoding, name='scores_encoding')
]
