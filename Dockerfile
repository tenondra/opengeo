FROM osgeo/gdal:ubuntu-small-3.2.3 as build-stage

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

RUN apt-get update && \
    apt-get -y install python3-distutils python3-pip && \
    pip3 install poetry && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock /app/

WORKDIR /app
RUN poetry export -f requirements.txt --without-hashes --output requirements.txt


######################################################

FROM osgeo/gdal:ubuntu-small-3.2.3

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /app
COPY --from=build-stage /app/requirements.txt ./requirements.txt

RUN apt-get update && \
    apt-get -y install --no-install-recommends python3-pip && \
    pip3 install -r requirements.txt && \
    apt-get purge -y --auto-remove gcc perl python3-pip && \
    apt-get clean && \
    rm -rf /root/.cache/pip /var/lib/apt/lists/*

COPY . /app

RUN python manage.py migrate

CMD uvicorn --host 0.0.0.0 --reload opengeo-project.asgi:application

EXPOSE 8000
