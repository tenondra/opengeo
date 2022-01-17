from logging import getLogger

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from graphene import ObjectType, Field, Mutation, List, String, Boolean
from graphene_django.types import ErrorType
from graphene_django_extras import DjangoSerializerMutation, LimitOffsetGraphqlPagination
from graphql_jwt import Refresh, Verify, ObtainJSONWebToken, DeleteJSONWebTokenCookie
from graphql_jwt.decorators import login_required

from opengeo.models import LobbyModel, LocationModel, LobbyPlayerModel, GuessModel, PlayerModel
from opengeo.schema.object_types import Location, LobbyPlayer, PlayerRegisterType, LocationInput
from opengeo.schema.subscription import LobbyUpdateSubscription
from opengeo.schema.utils import get_player_id, apply_to_class, request_passes_test, same_player_test, make_request_test
from opengeo.serializers import PlayerSerializer, LocationSerializer, GuessSerializer, GameSerializer, LobbySerializer, \
    LobbyPlayerSerializer, LobbyGameSerializer, GuessCreateSerializer

logger = getLogger(__name__)

"""
Definitions for all graphql mutations
"""


class PlayerRegisterMutation(Mutation):
    """
    Registration of a player
    """

    class Arguments:
        name = String()
        password = String()

    player = Field(PlayerRegisterType)
    ok = Boolean()

    @classmethod
    def mutate(cls, root, info, name, password, *args, **kwargs):
        player = PlayerModel(name=name)
        player.set_password(password)
        try:
            player.save()
            return PlayerRegisterMutation(player=player, ok=True)
        except ValueError:
            return PlayerRegisterMutation(ok=False)


@apply_to_class(login_required)
class PlayerSerializerMutation(DjangoSerializerMutation):
    """
    U+D Player mutations from serializer
    """

    class Meta:
        serializer_class = PlayerSerializer
        pagination = LimitOffsetGraphqlPagination(default_limit=30)
        only_fields = ["id", "name"]

    @staticmethod
    def _send_subscriptions(response) -> None:
        """
        Send updates to subscriptions affected by player changes
        :param response: response from a mutation
        :return: None
        """
        if response.ok:
            player = response.playermodel
            try:
                lobbies = LobbyModel.objects.filter(Q(owner__id=player.id) & Q(
                    state__in=[LobbyModel.StateChoices.RUNNING, LobbyModel.StateChoices.RUNNING])).all()
                for lobby in lobbies:
                    LobbyUpdateSubscription.update_from_model(lobby)
                if hasattr(player, "lobby_player") and player.lobby_player and player.lobby_player.lobby:
                    LobbyUpdateSubscription.update_from_model(player.lobby_player.lobby)
            except ObjectDoesNotExist:
                pass

    @classmethod
    @request_passes_test(same_player_test)
    def update(cls, root, info, **kwargs):
        response = super().update(root, info, **kwargs)
        cls._send_subscriptions(response)
        return response

    @classmethod
    @request_passes_test(same_player_test)
    def delete(cls, root, info, **kwargs):
        response = super().delete(root, info, **kwargs)
        cls._send_subscriptions(response)
        return response


@apply_to_class(login_required)
class LocationSerializerMutation(DjangoSerializerMutation):
    """
    CUD Location mutations from serializer
    """

    class Meta:
        serializer_class = LocationSerializer
        pagination = LimitOffsetGraphqlPagination(default_limit=30)


class MultipleLocationSerializerMutation(Mutation):
    """
    Creation of multiple locations
    """

    class Input:
        locations = List(LocationInput)

    locations = List(lambda: Location)

    @classmethod
    @login_required
    def mutate(cls, root, info, locations, *args, **kwargs):
        locations = [LocationModel.objects.create(latitude=loc.latitude, longitude=loc.longitude, game_id=loc.game)
                     for loc in locations]
        return MultipleLocationSerializerMutation(locations=locations)


def model_owned(field_selector):
    @make_request_test
    def decorator(info, mutation, **kwargs):
        if mutation is not None:
            id_field = "id" if "id" in kwargs.get(mutation._meta.input_field_name) else "player"
            field_id = kwargs.get(mutation._meta.input_field_name).get(id_field)
            return get_player_id(info) == str(field_selector(mutation._meta.model.objects, field_id))
        return get_player_id(info) == kwargs.get("id")

    return decorator


class GuessUpdateSerializerMutation(DjangoSerializerMutation):
    """
    UD Guess mutations from serializer
    """

    class Meta:
        serializer_class = GuessSerializer
        pagination = LimitOffsetGraphqlPagination(default_limit=30)

    @classmethod
    @login_required
    @request_passes_test(model_owned(lambda obj, field_id: obj.get(id=field_id).player_id))
    def update(cls, root, info, **kwargs):
        lat = kwargs.get(cls._meta.input_field_name)['latitude']
        lat_sign = 1 if lat > 0 else -1
        kwargs.get(cls._meta.input_field_name)['latitude'] = lat % (90 * lat_sign)
        lng = kwargs.get(cls._meta.input_field_name)['longitude']
        lng_sign = 1 if lng > 0 else -1
        kwargs.get(cls._meta.input_field_name)['longitude'] = lng % (180 * lng_sign)
        response = super().update(root, info, **kwargs)
        if response.ok:
            if response.guessmodel.guess_end:
                if response.guessmodel.location.game.locations.last() == response.guessmodel.location:
                    response.guessmodel.player.state = LobbyPlayerModel.PlayerState.AFTER_GAME
                else:
                    response.guessmodel.player.state = LobbyPlayerModel.PlayerState.WAITING_NEXT_ROUND
                response.guessmodel.player.save(update_fields=["state"])
        return response

    @classmethod
    def save(cls, serialized_obj: GuessSerializer, root, info, **kwargs):
        if serialized_obj.is_valid():
            if serialized_obj.instance.guess_end is None:
                # Save only valid and UNFINISHED
                obj = serialized_obj.save()
                return True, obj
            else:
                return False, [ErrorType(field="guess_end", messages=["Cannot update a finished guess"])]
        else:
            errors = [
                ErrorType(field=key, messages=value)
                for key, value in serialized_obj.errors.items()
            ]
            return False, errors


class GuessCreateSerializerMutation(DjangoSerializerMutation):
    """
    Mutation for creation of a single guess
    """

    class Meta:
        serializer_class = GuessCreateSerializer
        pagination = LimitOffsetGraphqlPagination(default_limit=30)

    @staticmethod
    def _update_player_state(guess: GuessModel, lobby_player: LobbyPlayerModel):
        """
        Send subscription updates from the modified guess
        :param guess: guess affected by a mutation
        :param lobby_player: author of the guess
        :return: None
        """
        if guess.guess_end:
            if guess.location.game.locations.last() == guess.location:
                lobby_player.state = LobbyPlayerModel.PlayerState.AFTER_GAME
            else:
                lobby_player.state = LobbyPlayerModel.PlayerState.WAITING_NEXT_ROUND
            lobby_player.save(update_fields=["state"])

    @classmethod
    @login_required
    def create(cls, root, info, **kwargs):
        response = super().create(root, info, **kwargs)
        if response.ok:
            cls._update_player_state(response.guessmodel, response.guessmodel.player)
        return response

    @classmethod
    def save(cls, serialized_obj: GuessSerializer, root, info, **kwargs):
        if serialized_obj.is_valid():
            lobby_game = serialized_obj.validated_data['lobby_game']
            locations = lobby_game.game.locations.all()
            # Guesses made by the author in the specific game
            guessed = serialized_obj.validated_data['player'].guesses.filter(lobby_game_id=lobby_game.id).all()
            # Do not create a guess if there is a pending one
            if len(guessed) >= 1 and guessed[len(guessed) - 1].guess_end is None:
                return False, [
                    ErrorType(field="id", messages=["Cannot create a new guess when an old one is pending."])]
            loc = None if len(locations) <= len(guessed) else locations[len(guessed)]
            # No more locations in the game
            if loc is None:
                return False, [ErrorType(field="location", messages=["No location remaining."])]
            new_serializer = GuessSerializer(data={**serialized_obj.data, "location": loc.id})
            new_serializer.is_valid(True)
            return True, new_serializer.save()
        else:
            errors = [
                ErrorType(field=key, messages=value)
                for key, value in serialized_obj.errors.items()
            ]
            return False, errors


@apply_to_class(login_required)
class GameSerializerMutation(DjangoSerializerMutation):
    """
    CD Game mutations from serializer
    """

    class Meta:
        serializer_class = GameSerializer
        pagination = LimitOffsetGraphqlPagination(default_limit=30)
        exclude_fields = ["creator"]

    @classmethod
    def create(cls, root, info, **kwargs):
        kwargs[cls._meta.input_field_name]["creator"] = int(get_player_id(info))
        return super().create(root, info, **kwargs)

    @classmethod
    @request_passes_test(model_owned(lambda obj, field_id: obj.get(id=field_id).creator_id))
    def delete(cls, root, info, **kwargs):
        return super().delete(root, info, **kwargs)


@apply_to_class(login_required)
class GameUpdateSerializerMutation(DjangoSerializerMutation):
    """
    Update Game mutation from serializer
    """

    class Meta:
        serializer_class = GameSerializer
        pagination = LimitOffsetGraphqlPagination(default_limit=30)
        only_fields = ["id", "name", "creator"]

    @classmethod
    @request_passes_test(model_owned(lambda obj, field_id: obj.get(id=field_id).creator_id))
    def update(cls, root, info, **kwargs):
        return super().update(root, info, **kwargs)


@apply_to_class(login_required)
class LobbyGameSerializerMutation(DjangoSerializerMutation):
    """
    CD LobbyGame mutations from serializer
    """

    class Meta:
        serializer_class = LobbyGameSerializer
        pagination = LimitOffsetGraphqlPagination(30)

    @classmethod
    def create(cls, root, info, **kwargs):
        return super().create(root, info, **kwargs)

    @classmethod
    @request_passes_test(model_owned(lambda obj, field_id: obj.get(id=field_id).lobby.owner_id))
    def delete(cls, root, info, **kwargs):
        return super().delete(root, info, **kwargs)


@apply_to_class(login_required)
class LobbyGameUpdateSerializerMutation(DjangoSerializerMutation):
    """
    U LobbyGame mutation from serializer
    """

    class Meta:
        serializer_class = LobbyGameSerializer
        pagination = LimitOffsetGraphqlPagination(30)
        only_fields = ["game"]

    @classmethod
    @request_passes_test(model_owned(lambda obj, field_id: obj.get(id=field_id).lobby.owner_id))
    def update(cls, root, info, **kwargs):
        return super().update(root, info, **kwargs)


@apply_to_class(login_required)
class LobbySerializerMutation(DjangoSerializerMutation):
    """
    CUD Lobby mutations from serializer
    """
    lobby_players = Field(LobbyPlayer)

    class Meta:
        pagination = LimitOffsetGraphqlPagination(default_limit=30)
        serializer_class = LobbySerializer
        exclude_fields = ["created"]

    @classmethod
    def create(cls, root, info, **kwargs):
        response = super().create(root, info, **kwargs)
        if response.ok:
            players = response.lobbymodel.lobby_players.all()
            # Update states of the owner and other players (although there should be none other)
            if len(players) == 0:
                response.lobbymodel.owner.lobby_player.lobby = response.lobbymodel.id
            response.lobbymodel.owner.lobby_player.state = LobbyPlayerModel.PlayerState.IDLE
            response.lobbymodel.owner.lobby_player.lobby_id = response.lobbymodel.id
            response.lobbymodel.owner.lobby_player.save(update_fields=["state", "lobby"])
        return response

    @classmethod
    @request_passes_test(model_owned(lambda obj, field_id: obj.get(id=field_id).owner_id))
    def update(cls, root, info, **kwargs):
        response = super().update(root, info, **kwargs)
        if response.ok:
            # Update state of players based on the state of the lobby
            if kwargs.get("new_lobbymodel").state:
                player_state = {
                    LobbyModel.StateChoices.RUNNING: LobbyPlayerModel.PlayerState.IN_GAME,
                    LobbyModel.StateChoices.OPEN: LobbyPlayerModel.PlayerState.IDLE,
                    LobbyModel.StateChoices.CLOSED: LobbyPlayerModel.PlayerState.SEARCHING_LOBBY
                }[response.lobbymodel.state]
                response.lobbymodel.lobby_players.update(state=player_state)
            LobbyUpdateSubscription.update_from_model(response.lobbymodel)
        return response

    @classmethod
    @request_passes_test(model_owned(lambda obj, field_id: obj.get(id=field_id).owner_id))
    def delete(cls, root, info, **kwargs):
        response = super().update(root, info, **kwargs)
        if response.ok:
            LobbyUpdateSubscription.update_from_model(response.lobbymodel)
        return response


def creating_for_self(info, mutation, *args, **kwargs):
    target_id = kwargs.get(mutation._meta.input_field_name).get("player")
    return get_player_id(info) == target_id


def lobby_owner_or_self(field_selector):
    @make_request_test
    def decorator(info, mutation, **kwargs):
        if mutation is not None:
            id_field = "id" if "id" in kwargs.get(mutation._meta.input_field_name) else "player"
            field_id = kwargs.get(mutation._meta.input_field_name).get(id_field)
            logger.debug(mutation._meta.model.objects.get(player_id=field_id).lobby.owner_id)
            logger.debug(get_player_id(info))
            return model_owned(field_selector)(info, mutation, **kwargs) or \
                   get_player_id(info) == str(mutation._meta.model.objects.get(player_id=field_id).lobby.owner_id)

        return False

    return decorator


@apply_to_class(login_required)
class LobbyPlayerSerializerMutation(DjangoSerializerMutation):
    """
    CUD LobbyPlayer mutations from serializer
    """

    class Meta:
        serializer_class = LobbyPlayerSerializer
        pagination = LimitOffsetGraphqlPagination(default_limit=30)

    @classmethod
    @request_passes_test(creating_for_self)
    def create(cls, root, info, **kwargs):
        kwargs[cls._meta.input_field_name]["id"] = kwargs[cls._meta.input_field_name]["player"]
        response = super().create(root, info, **kwargs)
        if response.ok:
            lobby_player = response.lobbyplayermodel
            if lobby_player.lobby is not None:
                LobbyUpdateSubscription.update_from_model(lobby_player.lobby)
        return response

    @classmethod
    @request_passes_test(lobby_owner_or_self(lambda obj, field_id: obj.get(player_id=field_id).player_id))
    def update(cls, root, info, **kwargs):
        kwargs[cls._meta.input_field_name]["id"] = kwargs[cls._meta.input_field_name]["player"]
        old_lobby = None
        data = kwargs.get(cls._meta.input_field_name)
        if data.lobby is not None:
            # First load the old lobby in case it gets deleted/changed in the mutation
            try:
                player = LobbyPlayerModel.objects.get(player_id=data.player)
                old_lobby = player.lobby
            except LobbyModel.DoesNotExist:
                pass
        response = super().update(root, info, **kwargs)
        if response.ok:
            lobby_player = response.lobbyplayermodel
            if lobby_player.lobby is not None:
                # Send update to lobby that lobbyplayer had changed
                LobbyUpdateSubscription.update_from_model(lobby_player.lobby)
            elif data.lobby is not None:
                # Lobby was deleted
                try:
                    # Close the lobby (although it should be deleted if the database is set up correctly)
                    lobby = LobbyModel.objects \
                        .get(Q(owner__id=lobby_player.player.id) &
                             Q(state__in=[LobbyModel.StateChoices.OPEN, LobbyModel.StateChoices.RUNNING]))
                    lobby.state = LobbyModel.StateChoices.CLOSED
                    lobby.save()
                except LobbyModel.DoesNotExist:
                    if old_lobby:
                        # Remove players from the old lobby
                        new_players = list(filter(lambda pl: str(pl.player_id) != data.player,
                                                  old_lobby.lobby_players.all()))
                        LobbyUpdateSubscription.update(str(old_lobby.id), old_lobby.state, old_lobby.name, new_players,
                                                       old_lobby.owner, old_lobby.lobby_game)
        return response

    @classmethod
    @request_passes_test(model_owned(lambda obj, field_id: obj.get(player_id=field_id).player_id))
    def delete(cls, root, info, **kwargs):
        kwargs[cls._meta.input_field_name]["id"] = kwargs[cls._meta.input_field_name]["player"]
        response = super().delete(root, info, **kwargs)
        if response.ok:
            lobby_player = response.lobbyplayermodel
            if lobby_player.lobby is not None:
                LobbyUpdateSubscription.update_from_model(
                    LobbyModel.objects.filter(owner__player__id=lobby_player.lobby.owner_id).first())
        return response


class Mutations(ObjectType):
    # Authentication
    token_auth = ObtainJSONWebToken.Field()
    verify_token = Verify.Field()
    refresh_token = Refresh.Field()
    delete_token_cookie = DeleteJSONWebTokenCookie.Field()
    register_player = PlayerRegisterMutation.Field()
    # Own mutations
    player_update = PlayerSerializerMutation.UpdateField()
    player_delete = PlayerSerializerMutation.DeleteField()
    location_create = LocationSerializerMutation.CreateField()
    batch_location_create = MultipleLocationSerializerMutation.Field()
    guess_update = GuessUpdateSerializerMutation.UpdateField()
    guess_create = GuessCreateSerializerMutation.CreateField()
    game_create = GameSerializerMutation.CreateField()
    game_update = GameUpdateSerializerMutation.UpdateField()
    game_delete = GameSerializerMutation.DeleteField()
    lobby_game_create = LobbyGameSerializerMutation.CreateField()
    lobby_game_update = LobbyGameUpdateSerializerMutation.UpdateField()
    lobby_game_delete = LobbyGameSerializerMutation.DeleteField()
    lobby_create, lobby_delete, lobby_update = LobbySerializerMutation.MutationFields()
    lobby_player_create, lobby_player_delete, lobby_player_update = LobbyPlayerSerializerMutation.MutationFields()
