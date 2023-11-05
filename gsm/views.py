from flask import current_app, url_for
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from markupsafe import Markup

from flask_admin.model.template import LinkRowAction, EndpointLinkRowAction

from gsm import __version__
from gsm.models import *

SATUS2ICON = {
  'success': '✅',
  'failed': '❌',
  'canceled': '✋',
  'pending': '🤔',
  'running': '🏃', 
  'created': '👶',
}

class ROModelView(ModelView):
  extra_css = ['https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css']
  can_view_details = True
  can_create = False
  can_edit = False
  can_delete = False

def pipeline2gitlaburl(sol, id):
  student = sol.student.name
  exercise = sol.exercise.name
  return f'{current_app.config["GITLAB_BASEURL"]}{student}/{student}-{exercise}/-/pipelines/{id}'

def job2gitlaburl(job, id):
  solution = job.pipeline.solution 
  student = solution.student.name
  exercise = solution.exercise.name
  return f'{current_app.config["GITLAB_BASEURL"]}{student}/{student}-{exercise}/-/jobs/{id}'

def jobs2str(jobs):
  return '&nbsp;&nbsp;'.join(f'<span title="{j.status}">{SATUS2ICON[j.status]}</span>&nbsp;<a href="{job2gitlaburl(j, j.id)}">{j.name}</a>' for j in jobs)

def pipeline2progress(pipeline):
  if pipeline.summary_count == 0: return """
<div class="progress">
  <div class="progress-bar bg-info" role="progressbar" style="width: 100%" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100"></div>
</div>
"""
  success = int(pipeline.summary_success / pipeline.summary_count * 100) 
  danger = int(pipeline.summary_failed / pipeline.summary_count * 100)
  warning = int(pipeline.summary_skipped / pipeline.summary_count * 100)
  return f"""
<div class="progress">
  <div class="progress-bar bg-success" role="progressbar" style="width: {success}%" aria-valuenow="{success}" aria-valuemin="0" aria-valuemax="100"></div>
  <div class="progress-bar bg-danger" role="progressbar" style="width: {danger}%" aria-valuenow="{danger}" aria-valuemin="0" aria-valuemax="100"></div>
  <div class="progress-bar bg-warning" role="progressbar" style="width: {warning}%" aria-valuenow="{warning}" aria-valuemin="0" aria-valuemax="100"></div>
</div>
"""

class AllStudentView(ROModelView):
  column_sortable_list = column_filters = column_list = ['name', 'num_solutions', 'num_pipelines', 'created_at']
  column_default_sort = ('name', False)
  column_details_list = ['name', 'created_at', 'solutions']
  column_extra_row_actions = [
    LinkRowAction('fa fa-arrow-up-right-from-square', lambda s, i, r: current_app.config["GITLAB_BASEURL"] + r.name),
  ]
  column_formatters_detail = {
    'solutions': lambda v, c, m, p: Markup('<ul>' + '\n'.join(f'<li><a href="{url_for("solution.details_view", id = s.id)}">{s.exercise.name}</a> ({s.num_pipelines})' for s in m.solutions) + '</ul>')
  }

class StudentView(AllStudentView):
  def get_query(self):
    return super().get_query().filter(self.model.num_pipelines>0)
  def get_count_query(self):
    return super().get_count_query().filter(self.model.num_pipelines>0)

class AllSolutionView(ROModelView):
  column_sortable_list = column_filters = column_list = ['last_activity_at', 'exercise.name', 'student.name', 'num_pipelines', 'created_at']
  column_default_sort = ('last_activity_at', True)
  column_labels = {
    'student.name': 'Student', 
    'exercise.name': 'Exercise'                                                                                                                                                                                                                                                                                                                                                                                                                               
  }
  column_extra_row_actions = [
    LinkRowAction('fa fa-arrow-up-right-from-square', lambda s, i, r: current_app.config["GITLAB_BASEURL"] + r.student.name + '/' + r.student.name + '-' + r.exercise.name),
  ]
  column_details_list = column_list + ['pipelines']
  column_formatters_detail = {
    'pipelines': lambda v, c, m, p: Markup('<ul>' + '\n'.join(f'<li><span title="{p.status}">{SATUS2ICON[p.status]} <a href="{pipeline2gitlaburl(p.solution, p.id)}">{p.created_at}</a> {jobs2str(p.jobs)}' for p in m.pipelines) + '</ul>')
  }

class SolutionView(AllSolutionView):
  def get_query(self):
    return super().get_query().filter(self.model.num_pipelines>0)
  def get_count_query(self):
    return super().get_count_query().filter(self.model.num_pipelines>0)

class PipelineView(ROModelView):
  column_details_list = column_filters = ['created_at', 'solution.student.name', 'solution.exercise.name', 'status', 'summary_count', 'summary_success', 'summary_failed', 'summary_skipped', 'summary_error', 'jobs']
  column_list = ['created_at', 'solution.student.name', 'solution.exercise.name', 'jobs', 'progress']
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
    'progress': lambda v, c, m, p: Markup(pipeline2progress(m)),
    'jobs': lambda v, c, m, p: Markup(jobs2str(m.jobs))
  }
  column_formatters_detail = {
    'jobs': lambda v, c, m, p: Markup('<ul>' + '\n'.join(f'<li><span title="{j.status}">{SATUS2ICON[j.status]} <a href="{job2gitlaburl(j, j.id)}">{j.name}</a>' for j in m.jobs) + '</ul>')
  }
  column_extra_row_actions = [
    LinkRowAction('fa fa-arrow-up-right-from-square', lambda s, i, r: pipeline2gitlaburl(r.solution, i)),
    LinkRowAction('fa fa-file-lines', lambda s, i, r: url_for('solution.details_view', id = r.solution.id)),
  ]

class ExerciseView(ROModelView):
  can_view_details = False
  column_list = ['name']

class JobView(ROModelView):
  can_view_details = False
  column_sortable_list = column_filters = column_list = ['pipeline.created_at', 'status', 'name', 'duration', 'runner']
  column_default_sort = ('pipeline.created_at', True)
  column_labels = {
    'pipeline.created_at': 'Created At', 
  }
  column_formatters = {
    'status': lambda v, c, m, p: Markup(f'<span title="{m.status}">{SATUS2ICON[m.status]}</span>'),
  }
  column_extra_row_actions = [
    LinkRowAction('fa fa-arrow-up-right-from-square', lambda s, i, r: job2gitlaburl(r, i))
  ]

def init_admin(app):
  admin = Admin(
    app, 
    name = f'GitLab Students Monitor [{__version__}]', 
    template_mode = 'bootstrap4',
    index_view = AdminIndexView(name = 'Home', url = '/'),
  )
  admin.add_view(StudentView(Student, db.session))
  admin.add_view(SolutionView(Solution, db.session))
  admin.add_view(PipelineView(Pipeline, db.session))
  admin.add_view(AllStudentView(Student, db.session, category = 'Details', endpoint = 'allstudent', name = 'All Students'))
  admin.add_view(AllSolutionView(Solution, db.session, category = 'Details', endpoint = 'allsolution', name = 'All Solutions'))
  admin.add_view(ExerciseView(Exercise, db.session, category = 'Details'))
  admin.add_view(JobView(Job, db.session, category = 'Details'))
  return admin

