from datetime import datetime
from pathlib import Path

import click
from flask import current_app
from flask.cli import with_appcontext
from gitlab import Gitlab
from gitlab.exceptions import GitlabError
from tqdm import tqdm

from gsm.models import *

ACCEPTED_STATUSES = frozenset(['success', 'failed', 'canceled'])

def datestr2obj(string):
  if string is None: return None
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
    dbs.begin()
    known = frozenset(dbs.execute(db.select(Student.id)).scalars().all())
    added = []
    with Gitlab(url = current_app.config['GITLAB_ENDPOINT'], private_token = current_app.config['GITLAB_TOKEN']) as gl:
      for student in tqdm(gl.groups.get(current_app.config['GITLAB_GROUP']).subgroups.list(all = True), position = 0):
        if student.id in known: continue
        dbs.add(Student(id = student.id, name = student.name, created_at = datestr2obj(student.created_at)))
        added.append(student.id)
    dbs.commit()
    if added: print('Added:', added)
  except Exception:
    dbs.rollback()
    raise

@click.command()
@click.argument("path")
@with_appcontext
def update_exercises(path):
  dbs = db.session
  try:
    dbs.begin()
    known = frozenset(dbs.execute(db.select(Exercise.name)).scalars().all())
    added = []
    for exercise in Path(path).iterdir():
      if not exercise.is_dir() or exercise.name in known: continue
      dbs.add(Exercise(name = exercise.name))
      added.append(exercise.name)
    dbs.commit()
    if added: print('Added:', added)
  except Exception:
    dbs.rollback()
    raise

@click.command()
@with_appcontext
def update_solutions():
  dbs = db.session
  try:
    dbs.begin()
    known = frozenset(dbs.execute(db.select(Solution.id)).scalars().all())
    exercise2id = dict(dbs.execute(db.select(Exercise.name, Exercise.id)).all())
    added, updated = [], []
    with Gitlab(url = current_app.config['GITLAB_ENDPOINT'], private_token = current_app.config['GITLAB_TOKEN']) as gl:
      for student in tqdm(dbs.execute(db.select(Student)).scalars().all(), position = 0):
        try:
          solutions = gl.groups.get(student.id).projects.list(all = True, archived = False)
        except GitlabError:
          click.echo(f'Failed to get projects for student {student}')
          continue
        for solution in solutions:
          if solution.id in known: 
            s = dbs.query(Solution).get(solution.id)
            la = datestr2obj(solution.last_activity_at)
            if s.last_activity_at != la:
              s.last_activity_at = la
              updated.append(solution.id)
              dbs.add(s)
            continue
          # prefix = f'{student.name}-'
          # if not solution.name.startswith(prefix): continue
          # exercise = solution.name[len(prefix):]
          exercise = solution.name
          if not exercise in exercise2id: continue
          dbs.add(Solution(
            id = solution.id, 
            created_at = datestr2obj(solution.created_at), 
            last_activity_at = datestr2obj(solution.last_activity_at),
            exercise_id = exercise2id[exercise], 
            student_id = student.id
          ))
          added.append(solution.id)
        dbs.flush()
    dbs.commit()
    if added or updated: print('Added:', added, 'Updated:', updated)
  except Exception:
    dbs.rollback()
    raise

@click.command()
@with_appcontext
def update_pipelines():
  dbs = db.session
  try:
    dbs.begin()
    known = frozenset(dbs.execute(db.select(Pipeline.id)).scalars().all()) | frozenset(dbs.execute(db.select(DiscardedPipeline.id)).scalars().all())
    added = []
    with Gitlab(url = current_app.config['GITLAB_ENDPOINT'], private_token = current_app.config['GITLAB_TOKEN']) as gl:
      for solution in tqdm(dbs.execute(db.select(Solution)).scalars().all(), position = 0):
        project = gl.projects.get(solution.id)
        try:
          pipelines = project.pipelines.list(all = True)
        except GitlabError:
          click.echo(f'Failed to get pipelines for solution {solution}')
          continue
        for pipeline in pipelines:
          if pipeline.id in known: continue
          pipeline = project.pipelines.get(pipeline.id)
          if pipeline.user['username'] != solution.student.name:
            dbs.add(DiscardedPipeline(id = pipeline.id))
            continue
          if pipeline.status not in ACCEPTED_STATUSES: continue
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
          added.append(pipeline.id)
      dbs.flush()    
    dbs.commit()
    if added: print('Added:', added)
  except Exception:
    dbs.rollback()
    raise

@click.command()
@with_appcontext
def update_jobs():
  dbs = db.session
  projects = {}
  try:
    dbs.begin()
    known = frozenset(dbs.execute(db.select(Job.id)).scalars().all())
    added = []
    with Gitlab(url = current_app.config['GITLAB_ENDPOINT'], private_token = current_app.config['GITLAB_TOKEN']) as gl:
      for pipeline in tqdm(dbs.execute(db.select(Pipeline)).scalars().all(), position = 0):
        if pipeline.solution_id not in projects: projects[pipeline.solution_id] = gl.projects.get(pipeline.solution_id)
        try:
          jobs = projects[pipeline.solution_id].pipelines.get(pipeline.id).jobs.list(all = True)
        except GitlabError:
          click.echo(f'Failed to get jobs for pipeline {pipeline}')
          continue
        for job in jobs:
          if job.id in known or job.user['username'] != pipeline.solution.student.name: continue
          dbs.add(Job(
            id = job.id, 
            pipeline_id = pipeline.id, 
            status = job.status, 
            name = job.name,
            duration = job.duration,
            runner = job.runner['description'] if job.runner else None
          ))
          added.append(job.id)
      dbs.flush()    
    dbs.commit()
    if added: print('Added:', added)
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
