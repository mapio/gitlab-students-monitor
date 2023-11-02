from flask import url_for, current_app
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from markupsafe import Markup

from gsm import __version__
from gsm.models import *

class ROModelView(ModelView):
  can_view_details = True
  can_create = False
  can_edit = False
  can_delete = False

class StudentView(ROModelView):
  column_list = ['name', 'created_at', 'num_solutions', 'num_pipelines']
  culumn_filters = ['name']
  column_sortable_list = column_list
  column_details_list = ['id', 'name', 'created_at', 'solutions']
  column_formatters = {
    'name': lambda v, c, m, p: Markup(f'<a href="{current_app.config["GITLAB_URL"] + m.name}">{m.name}</a>')
  }  
  column_formatters_detail = {
    'solutions': lambda v, c, m, p: Markup('<ul>' + '\n'.join(f'<li><a href="{url_for("solution.details_view", id = s.id)}">{s.exercise.name}</a> ({s.num_pipelines})' for s in m.solutions) + '</ul>')
  }

class ExerciseView(ROModelView):
  can_view_details = False
  column_list = ['name']

class SolutionView(ROModelView):
  column_list = ['student.name', 'exercise.name', 'num_pipelines']
  column_details_list = ['pipelines']

class PipelineView(ROModelView):
  column_list = ['id', 'solution.student.name', 'solution.exercise.name', 'sha', 'status', 'summary_count', 'summary_success', 'summary_failed', 'summary_skipped', 'summary_errors', 'created_at']
  column_details_list = ['jobs']

class JobView(ROModelView):
  pass

def init_admin(app):
  admin = Admin(
    app, 
    name=f'GitLab Students Monitor [{__version__}]', 
    template_mode = 'bootstrap4',
    index_view = AdminIndexView(name = 'Home', template = 'admin/index.html', url = '/')
  )
  admin.add_view(StudentView(Student, db.session))
  admin.add_view(ExerciseView(Exercise, db.session))
  admin.add_view(SolutionView(Solution, db.session))
  admin.add_view(PipelineView(Pipeline, db.session))
  admin.add_view(JobView(Job, db.session))
  return admin

