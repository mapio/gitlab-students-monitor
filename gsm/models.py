from typing import List

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime, ForeignKey, Integer, String, event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from gsm import LOG


class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)

@event.listens_for(Engine, 'connect')
def set_sqlite_pragma(dbapi_connection, connection_record):
  cursor = dbapi_connection.cursor()
  cursor.execute('PRAGMA foreign_keys = ON')
  cursor.close()

class Student(db.Model):
  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
  created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
  solutions: Mapped[List['Solution']] = relationship(back_populates='student', order_by = 'desc(Solution.created_at)', cascade='all, delete', passive_deletes=True)
  @hybrid_property
  def num_solutions(self):
    return len(self.solutions)
  @num_solutions.expression
  def num_solutions(cls):
    return select(func.count(Solution.id)).where(Solution.student_id == Student.id).scalar_subquery()
  @hybrid_property
  def num_pipelines(self):
    return sum(len(s.pipelines) for s in self.solutions)
  @num_pipelines.expression
  def num_pipelines(cls):
    return select(func.count(Pipeline.id)).join(Solution).where(Solution.student_id == Student.id).scalar_subquery()
  def __repr__(self):
    return self.name
  
class Exercise(db.Model):
  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
  solutions: Mapped[List['Solution']] = relationship(back_populates='exercise')
  @hybrid_property
  def num_solutions(self):
    return len([s for s in self.solutions if s.num_pipelines > 0])
  @num_solutions.expression
  def num_solutions(cls):
    return select(func.count(Solution.id)).where(Solution.exercise_id == Exercise.id, Solution.num_pipelines > 0).scalar_subquery()
  @hybrid_property
  def num_successful_solutions(self):
    return len([s for s in self.solutions if s.status == 'success'])
  @num_successful_solutions.expression
  def num_successful_solutions(cls):
    return select(func.count(Solution.id)).where(Solution.exercise_id == Exercise.id, Solution.status == 'success').scalar_subquery()


  def __repr__(self):
    return self.name

class Solution(db.Model):
  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  exercise_id: Mapped[int] = mapped_column(ForeignKey('exercise.id'))
  exercise: Mapped[Exercise] = relationship(back_populates='solutions')
  student_id: Mapped[int] = mapped_column(ForeignKey('student.id', ondelete='CASCADE'))
  student: Mapped[Student] = relationship(back_populates='solutions')
  created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
  last_activity_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
  pipelines: Mapped[List['Pipeline']] = relationship(back_populates='solution', order_by = 'desc(Pipeline.created_at)', cascade='all, delete', passive_deletes=True)
  @hybrid_property
  def num_succeses(self):
    return self.pipelines[0].summary_success if self.pipelines else None
  @num_succeses.expression
  def num_succeses(cls):
    return select(Pipeline.summary_success).where(Pipeline.solution_id == Solution.id).order_by(Pipeline.id.desc()).limit(1).scalar_subquery()
  @hybrid_property
  def status(self):
    return self.pipelines[0].status if self.pipelines else None
  @status.expression
  def status(cls):
    return select(Pipeline.status).where(Pipeline.solution_id == Solution.id).order_by(Pipeline.id.desc()).limit(1).scalar_subquery()
  @hybrid_property
  def num_pipelines(self):
    return len(self.pipelines)
  @num_pipelines.expression
  def num_pipelines(cls):
    return select(func.count(Pipeline.id)).where(Pipeline.solution_id == Solution.id).scalar_subquery()
  def __repr__(self):
    return f'{self.exercise.name}@{self.last_activity_at} ({self.student.name})'

class DiscardedPipeline(db.Model):
  id: Mapped[int] = mapped_column(Integer, primary_key=True)

class Pipeline(db.Model):
  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  solution_id: Mapped[int] = mapped_column(ForeignKey('solution.id', ondelete='CASCADE'))
  solution: Mapped[Solution] = relationship(back_populates='pipelines')
  status: Mapped[str] = mapped_column(String, nullable=False)
  created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
  sha: Mapped[str] = mapped_column(String, nullable=False)
  summary_count: Mapped[int] = mapped_column(Integer)
  summary_success: Mapped[int] = mapped_column(Integer)
  summary_failed: Mapped[int] = mapped_column(Integer)
  summary_skipped: Mapped[int] = mapped_column(Integer)
  summary_error: Mapped[int] = mapped_column(Integer)
  jobs: Mapped[List['Job']] = relationship(back_populates='pipeline', cascade='all, delete', passive_deletes=True)
  def __repr__(self):
    return f'{self.solution} @ {self.created_at}'

class Job(db.Model):
  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  pipeline_id: Mapped[int] = mapped_column(ForeignKey('pipeline.id', ondelete='CASCADE'))
  pipeline: Mapped[Pipeline] = relationship(back_populates='jobs')
  status: Mapped[str] = mapped_column(String, nullable=False)
  name: Mapped[str] = mapped_column(String, nullable=False)
  runner: Mapped[str] = mapped_column(String, nullable=True)
  duration: Mapped[int] = mapped_column(Integer, nullable=True)
  def __repr__(self):
    return f'{self.name} {self.status}'