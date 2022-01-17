from django.http import HttpResponse
from rest_framework import status


class GraphQlAuthenticationStatusCodeMiddleware(object):
    """
    Django middleware that sets the HTTP status code to 401 if the authentication failed.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if type(response) is HttpResponse and \
                (b"You do not have permission to perform this action" in response.content \
                 or b"JSONWebTokenError: Token is required" in response.content):
            response.status_code = status.HTTP_401_UNAUTHORIZED
            response.content = b"{}"
        return response
