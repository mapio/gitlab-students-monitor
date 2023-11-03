from flask import current_app, url_for
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from markupsafe import Markup

from flask_admin import expose
from flask_admin.model.template import LinkRowAction

from gsm import __version__
from gsm.models import *

SATUS2ICON = {
  'success': '✅',
  'failed': '❌',
  'canceled': '✋',
  'pending': '🤔',
  'running': '🏃',
}

class ROModelView(ModelView):
  can_view_details = True
  can_create = False
  can_edit = False
  can_delete = False

def pipeline2gitlaburl(sol, id):
  return f'{current_app.config["GITLAB_BASEURL"]}{sol.student.name}/{sol.student.name}-{sol.exercise.name}/-/pipelines/{id}'

def jobs2str(jobs):
  return '&nbsp;&nbsp;'.join(f'<span title="{j.status}">{SATUS2ICON[j.status]}</span>&nbsp;{j.name}' for j in jobs)

class StudentView(ROModelView):
  column_sortable_list = column_filters = column_list = ['name', 'created_at', 'num_solutions', 'num_pipelines']
  column_default_sort = ('name', False)
  column_details_list = ['name', 'created_at', 'solutions']
  column_extra_row_actions = [
    LinkRowAction('fa fa-arrow-circle-right', lambda s, i, r: current_app.config["GITLAB_BASEURL"] + r.name),
  ]
  column_formatters_detail = {
    'solutions': lambda v, c, m, p: Markup('<ul>' + '\n'.join(f'<li><a href="{url_for("solution.details_view", id = s.id)}">{s.exercise.name}</a> ({s.num_pipelines})' for s in m.solutions) + '</ul>')
  }

class SolutionView(ROModelView):
  column_sortable_list = column_filters = column_list = ['created_at', 'student.name', 'exercise.name', 'num_pipelines']
  column_default_sort = ('created_at', True)
  column_labels = {
    'student.name': 'Student', 
    'exercise.name': 'Exercise'                                                                                                                                                                                                                                                                                                                                                                                                                               
  }
  column_extra_row_actions = [
    LinkRowAction('fa fa-arrow-circle-right', lambda s, i, r: current_app.config["GITLAB_BASEURL"] + r.student.name + '/' + r.student.name + '-' + r.exercise.name),
  ]
  column_details_list = column_list + ['pipelines']
  column_formatters_detail = {
    'pipelines': lambda v, c, m, p: Markup('<ul>' + '\n'.join(f'<li><span title="{p.status}">{SATUS2ICON[p.status]} <a href="{pipeline2gitlaburl(p.solution, p.id)}">{p.created_at}</a> {jobs2str(p.jobs)}' for p in m.pipelines) + '</ul>')
  }
  def get_query(self):
    return super().get_query().filter(self.model.num_pipelines>0)
  def get_count_query(self):
    return self.session.execute(select(func.count(self.model.id)).where(self.model.num_pipelines>0))

class PipelineView(ROModelView):
  can_view_details = False
  column_filters = column_list = ['created_at', 'solution.student.name', 'solution.exercise.name', 'status', 'jobs', 'summary_count', 'summary_success', 'summary_failed', 'summary_skipped', 'summary_error']
  column_default_sort = ('created_at', True)
  column_sortable_list = ['created_at', 'solution.student.name', 'solution.exercise.name', 'status', ('jobs', 'jobs.name'), 'summary_count', 'summary_success', 'summary_failed', 'summary_skipped', 'summary_error']
  column_labels = {
    'solution.student.name': 'Student', 
    'solution.exercise.name': 'Exercise',
    'summary_count': '# Tests',
    'summary_success': '# Success',
    'summary_failed': '# Failed',
    'summary_skipped': '# Skipped',
    'summary_error': '# Error'
  }
  column_formatters = {
    'status': lambda v, c, m, p: Markup(f'<span title="{m.status}">{SATUS2ICON[m.status]}</span>'),
    'jobs': lambda v, c, m, p: Markup(jobs2str(m.jobs))
  }
  column_extra_row_actions = [
    LinkRowAction('fa fa-arrow-circle-right', lambda s, i, r: pipeline2gitlaburl(r.solution, i))
  ]

class ExerciseView(ROModelView):
  can_view_details = False
  column_list = ['name']

class JobView(ROModelView):
  can_view_details = False

def init_admin(app):
  admin = Admin(
    app, 
    name=f'GitLab Students Monitor [{__version__}]', 
    template_mode = 'bootstrap4',
    index_view = AdminIndexView(name = 'Home', template = 'admin/index.html', url = '/')
  )
  admin.add_view(StudentView(Student, db.session))
  admin.add_view(SolutionView(Solution, db.session))
  admin.add_view(PipelineView(Pipeline, db.session))
  admin.add_view(ExerciseView(Exercise, db.session, category = 'Details'))
  admin.add_view(JobView(Job, db.session, category = 'Details'))
  return admin

