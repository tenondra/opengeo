import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models import TextChoices
from django.dispatch import Signal

# Custom signal after multiple object updates
post_update = Signal()


class MyCustomQuerySet(models.QuerySet):
    """
    Custom queryset that sends the post_update signal after multiple objects were updated
    """

    def update(self, **kwargs):
        super().update(**kwargs)
        post_update.send(sender=self.model, instances=self.all())


class MyCustomManager(models.Manager):
    """
    Custom manager for the custom queryset
    """

    def get_queryset(self):
        return MyCustomQuerySet(self.model, using=self._db)


class PlayerManager(BaseUserManager):
    """
    Custom manager for the custom user auth model (player)
    """
    use_in_migrations = True

    def create_user(self, name, password):
        player = self.model(name=name)
        player.set_password(password)
        player.save(using=self._db)
        return player

    def create_superuser(self, **kwargs):
        """
        Do not allow superuser creation
        :param kwargs:
        :return:
        """
        return None


class PlayerModel(AbstractBaseUser):
    """
    A player
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30)

    objects = PlayerManager()

    USERNAME_FIELD = 'id'
    REQUIRED_FIELDS = ['name', 'password']

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name

    def __str__(self):
        return str(self.id)


class LobbyPlayerModel(models.Model):
    """
    A player relation to a lobby
    """

    class PlayerState(TextChoices):
        IDLE = "idle"
        READY = "ready"
        IN_GAME = "in_game"
        WAITING_NEXT_ROUND = "waiting_next_round"
        AFTER_GAME = "after_game"
        SEARCHING_LOBBY = "searching_lobby"

    lobby = models.ForeignKey("LobbyModel", related_name="lobby_players", null=True, blank=True,
                              on_delete=models.CASCADE)
    state = models.CharField(choices=PlayerState.choices, max_length=20, default=PlayerState.SEARCHING_LOBBY)
    player = models.OneToOneField(PlayerModel, on_delete=models.CASCADE, related_name="lobby_player", primary_key=True)
    objects = MyCustomManager()


class GameModel(models.Model):
    """
    A game
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, null=True, blank=True)
    time_limit = models.IntegerField()
    creator = models.ForeignKey(PlayerModel, on_delete=models.CASCADE, related_name="created_games")


class LocationModel(models.Model):
    """
    A location
    """
    id = models.BigAutoField(primary_key=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    game = models.ForeignKey(GameModel, on_delete=models.CASCADE, related_name="locations")


class GuessModel(models.Model):
    """
    A guess
    """
    id = models.BigAutoField(primary_key=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    player = models.ForeignKey(LobbyPlayerModel, on_delete=models.CASCADE, related_name="guesses")
    location = models.ForeignKey(LocationModel, on_delete=models.CASCADE, related_name="guesses")
    lobby_game = models.ForeignKey("LobbyGameModel", on_delete=models.CASCADE, related_name="guesses")
    guess_start = models.DateTimeField(auto_now_add=True)
    guess_end = models.DateTimeField(null=True, blank=True)


class LobbyGameModel(models.Model):
    """
    A game-lobby relation
    """
    id = models.BigAutoField(primary_key=True)
    game = models.ForeignKey(GameModel, on_delete=models.CASCADE, related_name="game_lobbies")


class LobbyModel(models.Model):
    """
    A lobby
    """

    class StateChoices(TextChoices):
        OPEN = "open",
        RUNNING = "running",
        CLOSED = "closed"

    id = models.BigAutoField(primary_key=True)
    lobby_game = models.ForeignKey(LobbyGameModel, related_name="lobbies", on_delete=models.CASCADE, null=True,
                                   blank=True)
    owner = models.ForeignKey(PlayerModel, on_delete=models.CASCADE, related_name="owned_lobbies")
    state = models.CharField(choices=StateChoices.choices, max_length=10, default=StateChoices.OPEN)
    name = models.CharField(max_length=20, default=uuid.uuid4)
    created = models.DateTimeField(auto_now=True)
