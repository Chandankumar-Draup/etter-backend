from sqlalchemy.orm import Session
from contextlib import contextmanager
from typing import Generator

from api.s3.infra.db.repositories import (
    DocumentRepository,
    DocumentPartRepository,
    AuditEventRepository,
    IdempotencyKeyRepository
)


class UnitOfWork:
    def __init__(self, db: Session):
        self.db = db
        self.documents = DocumentRepository(db)
        self.parts = DocumentPartRepository(db)
        self.audit_events = AuditEventRepository(db)
        self.idempotency_keys = IdempotencyKeyRepository(db)

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

    def flush(self):
        self.db.flush()


@contextmanager
def unit_of_work(db: Session) -> Generator[UnitOfWork, None, None]:
    uow = UnitOfWork(db)
    try:
        yield uow
        uow.commit()
    except Exception:
        uow.rollback()
        raise

