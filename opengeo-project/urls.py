"""opengeo-project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib.staticfiles.views import serve as serve_static
from django.urls import re_path, path
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView
from graphql_jwt.decorators import jwt_cookie
from schema_graph.views import Schema

from opengeo.views import *

urlpatterns = \
    [
        re_path(r'^graphql/?$', csrf_exempt(jwt_cookie(GraphQLView.as_view(graphiql=True)))),
    ]

urlpatterns += [
    re_path(r"^(?P<basepath>maps|maps-lite)/(?P<path>.*)/?$", csrf_exempt(MapsProxyView.as_view()), name="maps-proxy"),
    re_path(r'^identicon/(?P<data>[^/ ]+)/?$', IdenticonView.as_view()),
    re_path(r"^schema/?$", Schema.as_view()),
]

if settings.ADMIN_ENABLED:
    from django.contrib import admin

    urlpatterns.append(path('admin/', admin.site.urls))

if settings.DEBUG:
    urlpatterns.append(
        re_path(r'^static/(?P<path>.*)$', never_cache(serve_static)),
    )
