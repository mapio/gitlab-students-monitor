import logging

from flask import Flask

__version__ = '0.1.2'

logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s [%(levelname)s] (%(module)s/%(funcName)s): %(message)s',
  force=True,
)
LOG = logging.getLogger('gm_log')

def create_app():
  app = Flask(__name__)
  from gsm.config import configure
  configure(app)
  from gsm.models import db
  db.init_app(app)
  from gsm.views import init_admin
  init_admin(app)
  from gsm.cli import init_cli
  init_cli(app)
  return app

