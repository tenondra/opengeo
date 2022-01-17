from graphene import Int, Field, InputObjectType, Float, ID, ObjectType, List
from graphene_django_extras import DjangoObjectType, DjangoFilterListField, LimitOffsetGraphqlPagination

from opengeo.models import *
from opengeo.schema.utils import get_player_id, UNAUTHORIZED

"""
Custom graphql object types
"""


class PlayerRegisterType(DjangoObjectType):
    class Meta:
        description = "Player registration type"
        model = PlayerModel
        fields = ["name", "password"]


class LobbyPlayer(DjangoObjectType):
    id = Int()

    class Meta:
        description = "Type definition for lobby players relation"
        model = LobbyPlayerModel
        pagination = LimitOffsetGraphqlPagination(default_limit=30)

    def resolve_guesses(self, info):
        if get_player_id(info) != str(self.player_id):
            return [UNAUTHORIZED]
        return self.guesses.all()

    def resolve_created_games(self, info):
        if get_player_id(info) != str(self.player_id):
            return [UNAUTHORIZED]
        return self.created_games.all()

    def resolve_id(self, info):
        return self.player_id


class Player(DjangoObjectType):
    class Meta:
        description = "Type definition for one player"
        model = PlayerModel
        pagination = LimitOffsetGraphqlPagination(default_limit=30)
        exclude_fields = ["password"]


class Location(DjangoObjectType):
    class Meta:
        description = "Type definition for one location"
        model = LocationModel
        pagination = LimitOffsetGraphqlPagination(default_limit=30)

    @staticmethod
    def get_queryset(query, info, *args, **kwargs):
        return list(query)


class Guess(DjangoObjectType):
    class Meta:
        description = "Type definition for one guess"
        model = GuessModel
        pagination = LimitOffsetGraphqlPagination(default_limit=30)

    def resolve_location(self, info):
        if get_player_id(info) != str(self.player_id):
            return UNAUTHORIZED
        if not self.guess_end:
            return None
        return self.location

    @staticmethod
    def get_queryset(query, info, *args, **kwargs):
        return list(query)


class Game(DjangoObjectType):
    rounds = Int()

    class Meta:
        description = "Type definition for one game"
        model = GameModel
        pagination = LimitOffsetGraphqlPagination(default_limit=30)
        exclude_fields = ["locations"]

    @staticmethod
    def get_queryset(query, info, *args, **kwargs):
        return list(query)

    def resolve_rounds(self, info, *args, **kwargs):
        return LocationModel.objects.filter(game__id__exact=self.id).count()


class LobbyGame(DjangoObjectType):
    game = Field(Game)

    class Meta:
        description = "Type definition for lobby game relation"
        model = LobbyGameModel
        pagination = LimitOffsetGraphqlPagination(30)
        exclude_fields = ["guesses"]

    @staticmethod
    def get_queryset(query, info, *args, **kwargs):
        return list(query)


class Lobby(DjangoObjectType):
    lobby_players = DjangoFilterListField(LobbyPlayer)
    owner = Field(Player)
    id = Int()

    class Meta:
        description = "Type definition for one lobby"
        model = LobbyModel
        pagination = LimitOffsetGraphqlPagination(default_limit=30)
        filter_fields = {
            "created": ["gt"],
            "state": ["exact"]
        }

    @staticmethod
    def get_queryset(query, info, *args, **kwargs):
        return list(query)


"""
Non-model object types
"""


class LocationInput(InputObjectType):
    latitude = Float()
    longitude = Float()
    game = ID()


class CurrentGame(ObjectType):
    location = Field(Location)
    lobby_game = Field(LobbyGame)
    round_number = Int()


class RandomLocation(ObjectType):
    latitude = Float()
    longitude = Float()
    population_density = Int()


class Result(ObjectType):
    """
    A single result for a player
    """
    lobby_player = Field(LobbyPlayer)
    score = Int()
    total_score = Int()
    guess = Field(Guess)
    distance = Int()


class Results(ObjectType):
    """
    List of results for a location
    """
    results = List(Result)
    location = Field(Location)


class FinalResult(ObjectType):
    """
    A single result for a location
    """
    score = Int()
    guess = Field(Guess)
    distance = Int()


class FinalResults(ObjectType):
    """
    List of results for a player
    """
    lobby_player = Field(LobbyPlayer)
    total_score = Int()
    results = List(FinalResult)
    locations = List(Location)
