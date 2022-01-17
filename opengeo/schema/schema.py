from graphene import Schema
from graphene_django_extras import all_directives

from opengeo.schema.mutation import Mutations
from opengeo.schema.query import Query
from opengeo.schema.subscription import Subscription


"""
Definition of the graphql schema
"""

schema = Schema(query=Query, mutation=Mutations, directives=all_directives, subscription=Subscription)
