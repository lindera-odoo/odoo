# -*- coding: utf-8 -*-
from dotenv import load_dotenv  # noqa
from pathlib import Path  # noqa
env_path = Path('.env')  # noqa
load_dotenv(dotenv_path=env_path)  # noqa

from . import controllers
from . import models
