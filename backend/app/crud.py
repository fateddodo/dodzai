from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas


def get_tasks(session: Session) -> list[models.Task]:
    query = select(models.Task).order_by(models.Task.created_at.desc())
    return list(session.scalars(query))


def get_task(session: Session, task_id: int) -> models.Task | None:
    return session.get(models.Task, task_id)


def create_task(session: Session, task: schemas.TaskCreate) -> models.Task:
    db_task = models.Task(**task.model_dump())
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


def update_task(session: Session, db_task: models.Task, updates: schemas.TaskUpdate) -> models.Task:
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(db_task, field, value)
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


def delete_task(session: Session, db_task: models.Task) -> None:
    session.delete(db_task)
    session.commit()
