import logging
from os import environ
from pathlib import Path
from sys import exit
from tomllib import load

from gsm import LOG

def configure(app):

  if not 'GSM_CONFIG_FILE' in environ:
    exit('Please specify a configuration file setting GSM_CONFIG_FILE variable')
  with open(environ['GSM_CONFIG_FILE'], 'rb') as inf:
    CONFS = load(inf)
  missing = {'environment', 'flask', 'gitlab'} - set(CONFS.keys())
  if missing:
    exit(f'Config file {environ["GSM_CONFIG_FILE"]} missing keys: {missing}')

  if 'LOG_LEVEL' in CONFS['environment']:
    level = CONFS['environment']['LOG_LEVEL'].upper()
    app.logger.setLevel(getattr(logging, level))
    LOG.setLevel(getattr(logging, level))
    LOG.info('Log level set to %s', level)

  app.config['GITLAB_URL'] = CONFS['gitlab']['URL']
  app.config['GITLAB_TOKEN'] = CONFS['gitlab']['TOKEN']
  app.config['GITLAB_GROUP'] = CONFS['gitlab']['GROUP']

  dbfile = Path(app.instance_path) / 'gsm.sqlite'
  if 'SQLITE_DATABASE_FILE' in CONFS['environment']:
    dbfile = Path(CONFS['environment']['SQLITE_DATABASE_FILE'])
  app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + str(dbfile.absolute())
  LOG.info('Using database %s', app.config['SQLALCHEMY_DATABASE_URI'])

  app.config.from_mapping(CONFS['flask'])
