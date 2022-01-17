# OpenGeo

### This app is intended to run in Docker containers.

Before starting the app, make sure you have cloned it with the frontend project (`git clone --recurse-submodules`) or clone them using `git submodule init` and `git submodule update`.

Verify that the frontend project is present in the opengeo-frontend directory.

---
## Project configuration
- **./config/config.yml** - Backend configuration
- **./opengeo-frontend/docker/.env** - Frontend runtime configuration, should be based on .env.example

---
## Play With Docker
Easiest setup, but only temporary
1. Log in to [Play With Docker](https://labs.play-with-docker.com/)
2. Create a new instance
#TODO

## Docker

1. Install docker and docker compose
2. Configure the app
3. Run `docker compose up -d --build` in the project directory
4. The app should be running on http://127.0.0.1:3000/, if you want to allow connections outside of localhost, modify the docker-compose.yml file to your liking

## Windows

1. Install Python 3.7+ and pip
2. Install poetry with `pip3 install poetry`
3. Install [node.js 14+](https://nodejs.org/en/) and [yarn](https://classic.yarnpkg.com/en/docs/install/#windows-stable)
4. Set up the python GDAL installation with `python3 gdal-setup.py` which will download the required GDAL wheel and set up the poetry environment
5. [Configure](#project-configuration) the app
6. Prepare the backend using `poetry run python manage.py migrate`
7. Start the backend: `poetry run python manage.py runserver 127.0.0.1:8000 --nostatic`
8. Change the current working directory to 'opengeo-frontend'
9. Prepare the frontend: `yarn install`
10. Start the frontend: `yarn start`

## Linux

1. Install Python 3.7+ and pip
2. Install `gdal-bin libgdal-dev` via APT, or `gdal gdal-devel` via DNF
3. Install poetry with `pip3 install poetry`
4. Install [node.js 14+](https://nodejs.org/en/) and [yarn](https://classic.yarnpkg.com/en/docs/install/#debian-stable)
5. Check the GDAL installation with `python3 gdal-setup.py`
6. Create a Python virtualenv by running `poetry install` in the project directory
7. [Configure](#project-configuration) the app
8. Prepare the backend using `poetry run python manage.py migrate`
9. Start the backend: `poetry run python manage.py runserver 127.0.0.1:8000 --nostatic`
10. `cd opengeo-frontend`
11. Prepare the frontend: `yarn install`
12. Start the frontend: `yarn start`

## Mac

Too bad, though the steps should be similar to Linux

---

Nice resources:

- [Street view url query](https://stackoverflow.com/questions/387942/google-street-view-url)
- [React app configuration](https://create-react-app.dev/docs/advanced-configuration/)
- [React proxy config](https://create-react-app.dev/docs/proxying-api-requests-in-development/)
