from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from typing import List
from gsm import LOG
from sqlalchemy import select, func, text
from sqlalchemy.orm import column_property

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
  solutions: Mapped[List['Solution']] = relationship(back_populates='student')
  def __repr__(self):
    return f'{self.name} ({self.id}@{self.created_at})'
  
class Exercise(db.Model):
  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
  solutions: Mapped[List['Solution']] = relationship(back_populates='exercise')

class Solution(db.Model):
  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  exercise_id: Mapped[int] = mapped_column(ForeignKey('exercise.id'))
  exercise: Mapped[Exercise] = relationship(back_populates='solutions')
  student_id: Mapped[int] = mapped_column(ForeignKey('student.id'))
  student: Mapped[Student] = relationship(back_populates='solutions')
  created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
  pipelines: Mapped[List['Pipeline']] = relationship(back_populates='solution')
  def __repr__(self):
    return f'{self.id} ({self.exercise_id}@{self.created_at})'

Student.num_solutions = column_property(
  select(func.count(Solution.id)).where(Solution.student_id == Student.id).scalar_subquery()
)

class DiscardedPipeline(db.Model):
  id: Mapped[int] = mapped_column(Integer, primary_key=True)

class Pipeline(db.Model):
  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  solution_id: Mapped[int] = mapped_column(ForeignKey('solution.id'))
  solution: Mapped[Solution] = relationship(back_populates='pipelines')
  status: Mapped[str] = mapped_column(String, nullable=False)
  created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
  sha: Mapped[str] = mapped_column(String, nullable=False)
  summary_count: Mapped[int] = mapped_column(Integer)
  summary_success: Mapped[int] = mapped_column(Integer)
  summary_failed: Mapped[int] = mapped_column(Integer)
  summary_skipped: Mapped[int] = mapped_column(Integer)
  summary_error: Mapped[int] = mapped_column(Integer)
  jobs: Mapped[List['Job']] = relationship(back_populates='pipeline')
  def __repr__(self):
    return f'{self.id} ({self.solution_id}@{self.created_at})'

Student.num_pipelines = column_property(
  select(func.count(Pipeline.id)).join(Solution).where(Solution.student_id == Student.id).scalar_subquery()
)

Solution.num_pipelines = column_property(
  select(func.count(Pipeline.id)).where(Pipeline.solution_id == Solution.id).scalar_subquery()
)

class Job(db.Model):
  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  pipeline_id: Mapped[int] = mapped_column(ForeignKey('pipeline.id'))
  pipeline: Mapped[Pipeline] = relationship(back_populates='jobs')
  status: Mapped[str] = mapped_column(String, nullable=False)
  name: Mapped[str] = mapped_column(String, nullable=False)
