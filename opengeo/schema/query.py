import logging
import random
import typing
from random import uniform
from typing import Dict, Union

import geoio
import geopy.distance
import numpy as np
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from graphene_django_extras import DjangoFilterPaginateListField, DjangoObjectField
from graphql_jwt.decorators import login_required

from opengeo.schema.object_types import *

logger = logging.getLogger(__name__)

"""
Definitions of all graphql queries
"""

# Load the population density dataset
img = geoio.GeoImage(str((settings.BASE_DIR / "dataset.tiff").absolute()))
geo_data = img.get_data()
geo_data_array = np.asarray(geo_data)
transformation_values = img.get_gdal_obj().GetGeoTransform()


def get_score_distance(guess: GuessModel) -> Dict[str, int]:
    """
    Calculates the score and the distance of a guess from the target location
    :param guess: the guess
    :return: dictionary {"score": ,"distance": }
    """
    distance = geopy.distance.distance((guess.latitude, guess.longitude),
                                       (guess.location.latitude, guess.location.longitude))
    score = 4999.91 * 0.998036 ** distance.km
    return {"score": score, "distance": distance.m}


def get_population_density(lat: float, lon: float) -> float:
    """
    Loads population density based on geospatial coordinates from the dataset
    :param lat: Latitude
    :param lon: Longitude
    :return: population density
    """
    x, y = img.proj_to_raster(lon, lat)
    data = geo_data[0, int(y) % geo_data.shape[1], int(x) % geo_data.shape[2]]
    return data


def get_latlng_from_xy(x: int, y: int) -> Dict[str, float]:
    """
    Converts XY coordinates to lat,lng with randomness of one pixel in each direction
    :param x: x coordinate
    :param y: y coordinate
    :return: {"latitude": ,"longitude": } dict
    """
    lng, lat = (transformation_values[0] + (x + random.uniform(-.5, .5)) * transformation_values[1],
                transformation_values[3] + (y + random.uniform(-.5, .5)) * transformation_values[5])
    return {"latitude": lat, "longitude": lng}


class CustomQuery:
    current_location = Field(CurrentGame, lobby_id=ID(required=True), player_id=ID(required=True))
    current_guess = Field(Guess, player_id=ID(required=True), location_id=ID(required=True))
    random_location = List(RandomLocation, count=Int(), min_density=Int(), max_density=Int())
    results = Field(Results, lobby_game_id=ID(required=True), location_id=ID(required=True))
    final_results = List(FinalResults, lobby_id=ID(required=True))

    def resolve_current_location(self, info, lobby_id, player_id, **kwargs) -> Union[CurrentGame, None]:
        """
        Returns the current location a player should be guessing
        :param info:
        :param lobby_id:
        :param player_id:
        :param kwargs:
        :return:
        """
        try:
            lobby = LobbyModel.objects.get(id=lobby_id)
        except ObjectDoesNotExist:
            return None
        locations = lobby.lobby_game.game.locations.all()
        guessed = LocationModel.objects \
            .filter(Q(game_id=lobby.lobby_game.game_id) & Q(guesses__player_id=player_id)) \
            .all()
        loc = None if len(locations) < len(guessed) else locations[0 if len(guessed) == 0 else len(guessed) - 1]
        logger.debug("%s %s %s" % (loc, guessed, locations))
        logger.debug("Player %s; Lobby %s; LobbyGame %s" % (player_id, lobby_id, lobby.lobby_game_id))
        return CurrentGame(location=loc, lobby_game=lobby.lobby_game, round_number=len(guessed))

    def resolve_current_guess(self, info, player_id, location_id, **kwargs) -> Union[Guess, None]:
        """
        Returns the current guess for a player
        :param info:
        :param player_id:
        :param location_id:
        :param kwargs:
        :return:
        """
        try:
            # TODO: this will probably clash when replaying a game
            return GuessModel.objects.get(player_id=player_id, location_id=location_id)
        except ObjectDoesNotExist:
            return None

    def resolve_random_location(self, info, count=5, min_density=5, max_density=10000, **kwargs) \
            -> typing.List[RandomLocation]:
        """
        Returns random locations based on a user request
        :param info:
        :param count: number of locations
        :param min_density: minimum population density
        :param max_density: maximum population density
        :param kwargs:
        :return:
        """
        if min_density > 10000:
            min_density = 10000
        if max_density >= 99999:
            max_density = 99998
        if max_density - min_density > 50:
            max_density = min_density + 50
        results = []
        logger.debug("Getting random locations")
        if min_density >= 4000 or count >= 100:
            # Performance optimization with random choice of variables
            filtered = np.argwhere((geo_data_array >= min_density) & (geo_data_array <= max_density))
            while filtered.shape[0] == 0:
                # Who would do this
                if min_density > 50:
                    min_density -= 50
                else:
                    max_density += 50
                filtered = np.argwhere((geo_data_array >= min_density) & (geo_data_array <= max_density))
            # Replace if not enough results, exact duplicates should be ruled out by randomness of the resulting latlng
            chosen = filtered[np.random.choice(filtered.shape[0], count,
                                               replace=False if filtered.shape[0] > count else True)]
            return [RandomLocation(**get_latlng_from_xy(res[2], res[1]),
                                   population_density=geo_data_array[0, res[1], res[2]])
                    for res in chosen]
        while count > 0:
            # "Raycasting"
            density = 0
            lat = 0
            long = 0
            while density < min_density or density > max_density:
                # ignore antarctic and far north + sea
                lat = uniform(-60, 80)
                long = uniform(-180, 180)
                density = get_population_density(lat, long)
            logger.debug("Generated a random location")
            results.append(RandomLocation(latitude=lat, longitude=long, population_density=density))
            count -= 1
        return results

    def resolve_results(self, info, lobby_game_id, location_id, **kwargs) -> Results:
        """
        Loads the results for a single location in a game
        :param info:
        :param lobby_game_id:
        :param location_id:
        :param kwargs:
        :return:
        """
        # TODO: Some caching or other performance boost might benefit a lot
        queryset = GuessModel.objects \
            .filter(lobby_game_id=lobby_game_id, location_id=location_id, guess_end__isnull=False) \
            .all()
        location = LocationModel.objects.get(id=location_id)
        queryset = [Result(guess=g, **get_score_distance(g), lobby_player=g.player,
                           total_score=sum([get_score_distance(guess)["score"]
                                            for guess in GuessModel.objects
                                           .filter(Q(player_id=g.player_id) & Q(lobby_game_id=lobby_game_id))
                                           .all()]))
                    for g in queryset]
        return Results(results=queryset, location=location)

    def resolve_final_results(self, info, lobby_id, **kwargs) -> typing.List[FinalResults]:
        """
        Loads all results of a game
        :param info:
        :param lobby_id:
        :param kwargs:
        :return:
        """
        # TODO: Some caching or other performance boost might benefit a lot
        game: LobbyGameModel = LobbyModel.objects.get(id=lobby_id).lobby_game
        players: [LobbyPlayerModel] = LobbyPlayerModel.objects \
            .filter(guesses__lobby_game_id=game.id) \
            .distinct() \
            .all()
        locations = game.game.locations.all()
        res = sorted([
            FinalResults(lobby_player=player,
                         total_score=sum([r["score"]
                                          for r in [get_score_distance(g)
                                                    for g in player.guesses.filter(lobby_game_id=game.id).all()]]),
                         results=[FinalResult(guess=guess, **get_score_distance(guess))
                                  for guess in player.guesses.filter(lobby_game_id=game.id).all()],
                         locations=locations)
            for player in players
        ], key=lambda r: r.total_score, reverse=True)
        return res


class AuthenticatedDjangoObjectField(DjangoObjectField):
    """
    Wraps the resolver in the login_required decorator
    """

    def get_resolver(self, parent_resolver):
        return login_required(super().get_resolver(parent_resolver))


class AuthenticatedDjangoFilterPaginateListField(DjangoFilterPaginateListField):
    """
    Wraps the resolver in the login_required decorator
    """

    def get_resolver(self, parent_resolver):
        return login_required(super().get_resolver(parent_resolver))


class Query(ObjectType, CustomQuery):
    player = AuthenticatedDjangoObjectField(Player)
    lobby = AuthenticatedDjangoObjectField(Lobby)
    lobby_list = AuthenticatedDjangoFilterPaginateListField(Lobby, pagination=LimitOffsetGraphqlPagination(30))
    lobby_game = AuthenticatedDjangoObjectField(LobbyGame)
    lobby_player = AuthenticatedDjangoObjectField(LobbyPlayer)
