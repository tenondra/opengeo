# Create your views here.
from hashlib import md5
from re import compile, escape

import requests
from PIL import Image
from django.http import HttpResponse, HttpResponseRedirect
from fake_useragent import UserAgent
from rest_framework import status
from rest_framework.views import APIView

# UserAgent and session for google streetview requests
ua = UserAgent()
s = requests.Session()
# Allow cookies
s.get("https://www.google.com/maps/?q=&layer=c&cbll=0,0&cbp=0,0,0,0,0")
consent = s.cookies.get("CONSENT", domain=".google.com")
if consent:
    s.cookies.set("CONSENT", consent.replace("PENDING", "YES"), domain=".google.com")

# Regex for matching street names in google streetview
street_name_regex = rb"\[\"[^\\^\[^\]^\"]{3,}\",\"[a-z]{1,3}\"\]"
attraction_icon_regex = rb"\"https:\/\/maps\.gstatic\.com\/mapfiles\/annotations\/icons/[^\"]+\.png\""
streetview_cleanup_regex = compile(rb"|".join([street_name_regex, attraction_icon_regex]))


class MapsProxyView(APIView):
    """
    Proxies requests to the google maps site
    """

    def get(self, request, path="", basepath="maps"):
        maps_url = f"https://www.google.com/{basepath}/{path}"
        if basepath == "maps-lite":
            # Not a streetview but lite google maps
            return HttpResponseRedirect(redirect_to=maps_url.replace(basepath, "maps"))
        if path.startswith("preview/place"):
            # Previews for places in streetview, we do not want them
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)
        if len(self.request.query_params) > 0:
            # Build the query string
            query_string = '&'.join([f"{key}={value}" for key, value in self.request.query_params.items()])
            maps_url += f"?{query_string}"
        maps_response = s.get(maps_url, headers={"User-Agent": ua.chrome})
        content = maps_response.content
        if path.startswith("photometa"):
            # This response contains street names for streets, remove them using the regex replacement
            content = streetview_cleanup_regex.sub(rb'[""]', maps_response.content)
        response = HttpResponse(content, status=maps_response.status_code,
                                content_type=maps_response.headers['content-type'] if not path.startswith(
                                    "?q=&layer=c") else "text/html")
        return response


def random_color(hash_string):
    """
    Taken from https://github.com/Adam-Gleave/id.py/blob/master/id.py/id.py
    Create a random foreground color from hash
    :param hash_string:
    :return:
    """
    # remove first three digits from hex string
    split = 6
    rgb = hash_string[:split]

    split = 2
    r = rgb[:split]
    g = rgb[split:2 * split]
    b = rgb[2 * split:3 * split]

    color = (int(r, 16), int(g, 16), int(b, 16), 0xFF)

    return color


def generate_image(image, color, hash_string):
    """
    Taken from https://github.com/Adam-Gleave/id.py/blob/master/id.py/id.py
    Generate identicon from hash
    :param image:
    :param color:
    :param hash_string:
    :return:
    """
    hash_string = hash_string[6:]
    lower_x = 1
    lower_y = 1
    upper_x = 4
    upper_y = 6
    limit_x = 6
    index = 0

    for x in range(lower_x, upper_x):
        for y in range(lower_y, upper_y):
            if int(hash_string[index], 16) % 2 == 0:
                image.putpixel((x, y), color)
                image.putpixel((limit_x - x, y), color)
            index += 1
    return image


class IdenticonView(APIView):
    """
    Returns an identicon for some data (a username)
    """

    def get(self, request, data: str, *args, **kwargs):
        hash_string = md5(data.lower().encode("utf-8")).hexdigest()
        color = random_color(hash_string)
        image = generate_image(Image.new("RGB", (7, 7), (16, 32, 44, 0)), color, hash_string).resize((128, 128), 0)
        response = HttpResponse(content_type="image/png")
        image.save(response, "PNG")
        return response

# -- Some locations for population density testing --

# cz
# lat, lon = 49.139012, 16.918692
# print(get_population_density(lat, lon))
# india
# lat, lon = 23.480407, 85.146536
# print(get_population_density(lat, lon))
# out of range
# lat, lon = 91.480407, 85.146536
# print(get_population_density(lat, lon))
# out of range
# lat, lon = 80.480407, 190.146536
# print(get_population_density(lat, lon))
# washington
# lat, lon = 38.939778, -77.143503
# print(get_population_density(lat, lon))
# atlantic
# print(get_population_density(32.371701, -51.291992))
