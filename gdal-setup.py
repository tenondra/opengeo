import os
import platform
import re
import shutil
import subprocess
import sys
from logging import getLogger, INFO, StreamHandler
from pathlib import Path
from time import time

import requests

GDAL_VERSION = "3.2.3"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"}

logger = getLogger(__name__)
logger.setLevel(INFO)
logger.addHandler(StreamHandler(sys.stdout))


def main():
    if sys.version_info.major != 3 or sys.version_info.minor < 7:
        logger.error("You need python 3.7+ to use this app.")
        return
    if platform.system() == "Linux":
        ok = True
        if shutil.which("ogrinfo") is None:
            logger.error("You need to install the 'gdal-bin' package.")
            ok = False
        if shutil.which("gdal-config") is None:
            logger.error("You need to install the 'libgdal-dev' package.")
            ok = False
        if not ok:
            return
        else:
            logger.info("Ready to start the app")
    elif platform.system() == "Windows":
        Path("./whl").mkdir(exist_ok=True)
        version = {
            7: f"GDAL-{GDAL_VERSION}-cp37-cp37m-win_amd64.whl",
            8: f"GDAL-{GDAL_VERSION}-cp38-cp38-win_amd64.whl",
            9: f"GDAL-{GDAL_VERSION}-cp39-cp39-win_amd64.whl"
        }[sys.version_info.minor]
        logger.info(f"Downloading GDAL {GDAL_VERSION} for Python 3.{sys.version_info.minor}")
        r = requests.get(f"https://download.lfd.uci.edu/pythonlibs/q4trcu4l/{version}", headers=headers, stream=True)
        total = int(r.headers.get("content-length", 0))
        done = 0
        gdal_whl = Path(f"./whl/{version}")
        if not gdal_whl.exists() or os.path.getsize(gdal_whl) != total:
            with gdal_whl.open("wb") as gdal:
                start = time()
                for data in r.iter_content(chunk_size=1024):
                    s = gdal.write(data)
                    done += s
                    if time() - start >= 1.0:
                        logger.info(f"{version}   | {done} / {total}   | {done * 100 / total:.2f}%")
                        start = time()
        with Path("pyproject.toml").open("r") as f:
            content = f.read()
        try:
            new = re.sub(r"GDAL = \"[^\n]+\"", f"GDAL = {{ path = \"./whl/{version}\" }}", content, flags=re.S)
            with Path("pyproject.toml").open("w") as f:
                f.write(new)
            subprocess.check_call(["poetry", "update"])
            subprocess.check_call(["poetry", "install"])
        finally:
            with Path("pyproject.toml").open("w") as f:
                f.write(content)
        subprocess.check_call(["poetry", "update"])


if __name__ == '__main__':
    main()
