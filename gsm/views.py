from flask_admin import Admin, AdminIndexView

from gsm import __version__
from gsm.models import *

def init_admin(app):
  admin = Admin(
    app, 
    name=f'GitLab Students Monitor [{__version__}]', 
    template_mode = 'bootstrap4',
    index_view = AdminIndexView(name = 'Home', template = 'admin/index.html', url = '/')
  )
  return admin