# -*- coding: utf-8 -*-
from dotenv import load_dotenv  # noqa
from pathlib import Path  # noqa
# TODO: either add the specific version of dotenv to the requirements.txt or use a string for the path i.e. env_path = './custom-addons/.env'
# since not all versions of dotenv accept POSIX paths...
env_path = Path('./custom-addons') / '.env'  # noqa
load_dotenv(dotenv_path=env_path)  # noqa

from . import controllers
from . import models
