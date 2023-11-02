from datetime import datetime
from pathlib import Path

import click
from flask import current_app
from flask.cli import with_appcontext
from gitlab import Gitlab
from tqdm import tqdm

from gsm.models import *


def datestr2obj(string):
  return datetime.fromisoformat(string[0:string.index('.')])

@click.command()
@with_appcontext
def init_db():
  import gsm.models
  gsm.models.db.drop_all()
  gsm.models.db.create_all()
  gsm.models.db.session.commit()
  click.echo('DB initialized')

@click.command()
@with_appcontext
def update_students():
  dbs = db.session
  try:
    known = frozenset(dbs.execute(db.select(Student.id)).scalars().all())
    with Gitlab(url = current_app.config['GITLAB_ENDPOINT'], private_token = current_app.config['GITLAB_TOKEN']) as gl:
      for student in tqdm(gl.groups.get(current_app.config['GITLAB_GROUP']).subgroups.list(all = True), position = 0):
        if student.id in known: continue
        dbs.add(Student(id = student.id, name = student.name, created_at = datestr2obj(student.created_at)))
    dbs.commit()
  except Exception:
    dbs.rollback()
    raise

@click.command()
@click.argument("path")
@with_appcontext
def update_exercises(path):
  dbs = db.session
  try:
    known = frozenset(dbs.execute(db.select(Exercise.name)).scalars().all())
    for exercise in Path(path).iterdir():
      if not exercise.is_dir() or exercise.name in known: continue
      dbs.add(Exercise(name = exercise.name))
    dbs.commit()
  except Exception:
    dbs.rollback()
    raise

@click.command()
@with_appcontext
def update_solutions():
  dbs = db.session
  try:
    known = frozenset(dbs.execute(db.select(Solution.id)).scalars().all())
    exercise2id = dict(dbs.execute(db.select(Exercise.name, Exercise.id)).all())
    with Gitlab(url = current_app.config['GITLAB_ENDPOINT'], private_token = current_app.config['GITLAB_TOKEN']) as gl:
      for student in tqdm(dbs.execute(db.select(Student)).scalars().all(), position = 0):
        for solution in gl.groups.get(student.id).projects.list(all = True):
          if solution.id in known: continue
          prefix = f'{student.name}-'
          if not solution.name.startswith(prefix): continue
          exercise = solution.name[len(prefix):]
          if not exercise in exercise2id: continue
          dbs.add(Solution(id = solution.id, created_at = datestr2obj(solution.created_at), exercise_id = exercise2id[exercise], student_id = student.id))
    dbs.commit()
  except Exception:
    dbs.rollback()
    raise

@click.command()
@with_appcontext
def update_pipelines():
  dbs = db.session
  try:
    known = frozenset(dbs.execute(db.select(Pipeline.id)).scalars().all()) | frozenset(dbs.execute(db.select(DiscardedPipeline.id)).scalars().all())
    with Gitlab(url = current_app.config['GITLAB_ENDPOINT'], private_token = current_app.config['GITLAB_TOKEN']) as gl:
      for solution in tqdm(dbs.execute(db.select(Solution)).scalars().all(), position = 0):
        project = gl.projects.get(solution.id)
        for pipeline in project.pipelines.list(all = True):
          if pipeline.id in known: continue
          pipeline = project.pipelines.get(pipeline.id)
          if pipeline.user['username'] != solution.student.name:
            dbs.add(DiscardedPipeline(id = pipeline.id))
            continue
          summary = pipeline.test_report_summary.get().total
          dbs.add(Pipeline(
            id = pipeline.id, 
            created_at = datestr2obj(pipeline.created_at), 
            solution_id = solution.id, 
            status = pipeline.status, 
            sha = pipeline.sha,
            summary_count = summary['count'],
            summary_success = summary['success'],
            summary_failed = summary['failed'],
            summary_skipped = summary['skipped'],
            summary_error = summary['error']
          ))
    dbs.commit()
  except Exception:
    dbs.rollback()
    raise

@click.command()
@with_appcontext
def update_jobs():
  dbs = db.session
  projects = {}
  try:
    known = frozenset(dbs.execute(db.select(Job.id)).scalars().all())
    with Gitlab(url = current_app.config['GITLAB_ENDPOINT'], private_token = current_app.config['GITLAB_TOKEN']) as gl:
      for pipeline in tqdm(dbs.execute(db.select(Pipeline)).scalars().all(), position = 0):
        if pipeline.solution_id not in projects: projects[pipeline.solution_id] = gl.projects.get(pipeline.solution_id)
        for job in projects[pipeline.solution_id].pipelines.get(pipeline.id).jobs.list(all = True):
          if job.id in known or job.user['username'] != pipeline.solution.student.name: continue
          dbs.add(Job(id = job.id, pipeline_id = pipeline.id, status = job.status, name = job.name))
    dbs.commit()
  except Exception:
    dbs.rollback()
    raise

def init_cli(app):
  app.cli.add_command(init_db)
  app.cli.add_command(update_students)
  app.cli.add_command(update_exercises)
  app.cli.add_command(update_solutions)
  app.cli.add_command(update_pipelines)
  app.cli.add_command(update_jobs)
