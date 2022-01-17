import logging

from channels_graphql_ws import Subscription
from channels_graphql_ws.subscription import SubscriptionOptions
from django.db.models.signals import post_save
from django.dispatch import receiver
from graphene import ObjectType, Enum, String, Field
from graphene_django_extras.fields import DjangoListField

from opengeo.models import LobbyModel, LobbyPlayerModel, post_update
from opengeo.schema.object_types import Lobby, LobbyPlayer, Player, LobbyGame

"""
Definition of all graphql subscriptions
"""

logger = logging.getLogger(__name__)

LobbyStateEnum = Enum.from_enum(LobbyModel.StateChoices)

LobbyPlayerStateEnum = Enum.from_enum(LobbyPlayerModel.PlayerState)


class CustomSubscriptionOptions(SubscriptionOptions):
    model = None


class CustomSub(Subscription):
    """
    Custom subscription wrapper that plays nicely with model fields of the meta class
    """

    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
            cls,
            model=None,
            subscribe=None,
            publish=None,
            unsubscribed=None,
            output=None,
            arguments=None,
            _meta=None,
            **options,
    ):
        if not _meta:
            _meta = CustomSubscriptionOptions(cls)
        _meta.model = model
        return super().__init_subclass_with_meta__(subscribe, publish, unsubscribed, output, arguments, _meta,
                                                   **options)


class LobbyUpdateSubscription(CustomSub):
    state = LobbyStateEnum()
    name = String()
    lobby_players = DjangoListField(LobbyPlayer)
    lobby_id = String()
    owner = Field(Player)
    lobby_game = Field(LobbyGame)

    class Meta:
        model = Lobby

    class Arguments:
        lobby_id = String()

    @staticmethod
    async def subscribe(root, info, lobby_id=None):
        """
        When a user subscribes
        :param root:
        :param info:
        :param lobby_id:
        :return:
        """
        return [lobby_id] if lobby_id else None

    @staticmethod
    async def publish(root, info, lobby_id=None):
        """
        When a change is to be published
        :param root:
        :param info:
        :param lobby_id:
        :return:
        """
        state = root["state"]
        name = root["name"]
        lobby_players = root["lobby_players"]
        owner = root["owner"]
        lobby_game = root["lobby_game"]
        new_lobby_id = root["lobby_id"]
        assert lobby_id is None or lobby_id == new_lobby_id
        sub = LobbyUpdateSubscription(lobby_id=lobby_id, state=state, name=name, lobby_players=lobby_players,
                                      owner=owner, lobby_game=lobby_game)
        logger.debug(f"Sending lobby subscription {lobby_id} - {sub.lobby_players}")
        return sub

    @classmethod
    def update(cls, lobby_id, state, name, lobby_players, owner, lobby_game):
        """
        Send an update from arguments
        :param lobby_id: id of the lobby
        :param state: state of the lobby
        :param name: name of the lobby
        :param lobby_players: players in the lobby
        :param owner: owner of the lobby
        :param lobby_game: game associated with the lobby
        :return: None
        """
        cls.broadcast(group=lobby_id,
                      payload={"lobby_id": lobby_id, "state": state, "name": name, "lobby_players": lobby_players,
                               "owner": owner, "lobby_game": lobby_game})

    @classmethod
    def update_from_model(cls, lobby: LobbyModel):
        """
        Send an update from a lobby instance
        :param lobby: the changed lobby
        :return: None
        """
        return cls.update(str(lobby.id), lobby.state, lobby.name, list(lobby.lobby_players.all()), lobby.owner,
                          lobby.lobby_game)


class LobbyPlayerUpdateSubscription(Subscription):
    state = LobbyPlayerStateEnum()
    player_id = String()
    lobby = Field(Lobby)

    class Arguments:
        player_id = String()

    @staticmethod
    async def subscribe(root, info, player_id=None):
        """
        When a user subscribes
        :param root:
        :param info:
        :param player_id:
        :return:
        """
        logger.debug("New lobbyPlayer sub")
        return [player_id] if player_id else None

    @staticmethod
    async def publish(root, info, player_id=None):
        """
        When a change is to be sent to clients
        :param root:
        :param info:
        :param player_id:
        :return:
        """
        state = root["state"]
        new_id = root["player_id"]
        lobby = root["lobby"]
        assert player_id is None or player_id == new_id
        sub = LobbyPlayerUpdateSubscription(player_id=player_id, state=state, lobby=lobby)
        logger.debug(f"Sending lobbyPlayer data {sub}")
        return sub

    @classmethod
    def update(cls, player_id, state, lobby):
        """
        Send an update from the arguments
        :param player_id: id of the lobbyPlayer
        :param state: state of the lobbyPlayer
        :param lobby: lobby where the lobbyPlayer is joined in
        :return: None
        """
        cls.broadcast(group=player_id,
                      payload={"player_id": player_id, "state": state, "lobby": lobby})

    @classmethod
    def update_from_model(cls, lobby_player: LobbyPlayerModel):
        """
        Send an update from a lobbyPlayer instance
        :param lobby_player: the modified lobbyPlayer
        :return: None
        """
        return cls.update(str(lobby_player.player.id), lobby_player.state, lobby_player.lobby)


class Subscription(ObjectType):
    """
    Definition for all subscriptions
    """
    lobby_update = LobbyUpdateSubscription.Field()
    lobby_player_update = LobbyPlayerUpdateSubscription.Field()


@receiver(post_save, sender=LobbyPlayerModel, dispatch_uid="update_lobbyplayer_state")
def update_lobbyplayer_state(sender, instance, **kwargs):
    """
    After a lobbyPlayer is saved, trigger subscription updates
    :param sender:
    :param instance:
    :param kwargs:
    :return:
    """
    LobbyPlayerUpdateSubscription.update_from_model(instance)


@receiver(post_update, sender=LobbyPlayerModel, dispatch_uid="update_lobbyplayer_state_queryset")
def update_lobbyplayer_state(sender, instances, **kwargs):
    """
    After a multiple lobbyPlayers are updated, trigger subscription updates
    :param sender:
    :param instances:
    :param kwargs:
    :return:
    """
    for inst in instances:
        LobbyPlayerUpdateSubscription.update_from_model(inst)
