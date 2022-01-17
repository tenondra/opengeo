from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, Serializer

from opengeo.models import *


class LocationSerializer(ModelSerializer):
    class Meta:
        model = LocationModel
        fields = ["game", "latitude", "longitude", "id", "guesses"]


class GuessSerializer(ModelSerializer):
    guess_end = serializers.DateTimeField(required=False)
    guess_start = serializers.DateTimeField(required=False)
    latitude = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)

    class Meta:
        model = GuessModel
        fields = ["location", "latitude", "longitude", "id", "guess_start", "guess_end", "player", "lobby_game"]


class GuessCreateSerializer(ModelSerializer):
    location = LocationSerializer(required=False, read_only=True)

    class Meta:
        model = GuessModel
        fields = ["location", "player", "lobby_game"]


class LobbySerializer(ModelSerializer):
    class Meta:
        model = LobbyModel
        fields = ["lobby_game", "state", "name", "lobby_players", "owner", 'created']


class LobbyPlayerSerializer(ModelSerializer):
    class Meta:
        model = LobbyPlayerModel
        fields = '__all__'


class LobbyGameSerializer(ModelSerializer):
    class Meta:
        model = LobbyGameModel
        fields = ['lobbies', 'game']


class PlayerSerializer(ModelSerializer):
    guesses = GuessSerializer(required=False, many=True, read_only=True, default=[])
    lobby_player = LobbyPlayerSerializer(required=False, default=None)

    class Meta:
        model = PlayerModel
        fields = ["id", "name", "lobby_player", "guesses"]


class GameSerializer(ModelSerializer):
    locations = LocationSerializer(many=True, required=False, default=[], read_only=True)
    game_lobbies = LobbyGameSerializer(many=True, required=False, default=[], read_only=True)

    class Meta:
        model = GameModel
        fields = ["name", "id", "time_limit", "locations", "game_lobbies", "creator"]


class LocationRelatedField(serializers.RelatedField):
    def to_internal_value(self, data):
        pass

    def to_representation(self, value: LocationModel):
        return {
            "id": value.pk,
            "latitude": value.latitude,
            "longitude": value.longitude
        }


class PlayerRelatedField(serializers.RelatedField):
    def to_internal_value(self, data):
        pass

    def to_representation(self, value: PlayerModel):
        return {
            "id": value.pk,
            "name": value.name
        }


class GuessListSerializer(Serializer):
    id = serializers.IntegerField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    player = PlayerRelatedField(queryset=PlayerModel.objects.all())
    location = LocationRelatedField(queryset=LocationModel.objects.all())
    distance = serializers.IntegerField()
    score = serializers.IntegerField()


class PlayerGuessSummarySerializer(Serializer):
    guesses = GuessListSerializer(many=True, read_only=True)
    player = PlayerRelatedField(queryset=PlayerModel.objects.all())
    total_distance = serializers.IntegerField()
    total_score = serializers.IntegerField()


class GuessSummarySerializer(Serializer):
    player_guesses = PlayerGuessSummarySerializer(many=True, read_only=True)
