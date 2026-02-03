from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, Type, TypeVar
from models.etter import MasterFunction

T = TypeVar('T')


def get_or_create_master_function(
    db: Session,
    high_level_func: str,
    sub_level_func: str
) -> Tuple[MasterFunction, bool]:
    """
    Get existing MasterFunction or create a new one if it doesn't exist.
    
    Args:
        db: Database session
        high_level_func: High level function name
        sub_level_func: Sub level function name
    
    Returns:
        Tuple of (MasterFunction instance, created flag)
        created flag: True if created, False if already existed
    """
    master_function = db.query(MasterFunction).filter(
        MasterFunction.high_level_func == high_level_func,
        MasterFunction.sub_level_func == sub_level_func
    ).first()

    if master_function:
        return master_function, False

    master_function = MasterFunction(
        high_level_func=high_level_func,
        sub_level_func=sub_level_func,
        updated_by=datetime.utcnow()
    )
    db.add(master_function)
    
    try:
        db.flush()
        return master_function, True
    except IntegrityError:
        db.rollback()
        master_function = db.query(MasterFunction).filter(
            MasterFunction.high_level_func == high_level_func,
            MasterFunction.sub_level_func == sub_level_func
        ).first()
        if master_function:
            return master_function, False
        raise


def upsert_master_function(
    db: Session,
    high_level_func: str,
    sub_level_func: str
) -> MasterFunction:
    """
    Upsert MasterFunction - update if exists, create if not.
    
    Args:
        db: Database session
        high_level_func: High level function name
        sub_level_func: Sub level function name
    
    Returns:
        MasterFunction instance
    """
    master_function = db.query(MasterFunction).filter(
        MasterFunction.high_level_func == high_level_func,
        MasterFunction.sub_level_func == sub_level_func
    ).first()

    if master_function:
        master_function.updated_by = datetime.utcnow()
        db.flush()
        return master_function

    master_function = MasterFunction(
        high_level_func=high_level_func,
        sub_level_func=sub_level_func,
        updated_by=datetime.utcnow()
    )
    db.add(master_function)
    db.flush()
    return master_function


def generic_upsert(
    db: Session,
    model_class: Type[T],
    unique_keys: Dict[str, Any],
    update_data: Dict[str, Any],
    commit: bool = False,
    additional_filters: Optional[Dict[str, Any]] = None
) -> Tuple[T, bool]:
    """
    Generic upsert function for any model.
    
    Args:
        db: Database session
        model_class: SQLAlchemy model class
        unique_keys: Dictionary of key-value pairs for unique constraint lookup
        update_data: Dictionary of fields to update/create
        commit: Whether to commit the transaction (default: False)
        additional_filters: Optional additional filters to apply
    
    Returns:
        Tuple of (model instance, created flag)
        created flag: True if created, False if updated
    """
    query = db.query(model_class)
    
    for key, value in unique_keys.items():
        query = query.filter(getattr(model_class, key) == value)
    
    if additional_filters:
        for key, value in additional_filters.items():
            if value is not None:
                query = query.filter(getattr(model_class, key) == value)
    
    instance = query.first()

    if instance:
        for key, value in update_data.items():
            if key not in unique_keys:
                if value is not None:
                    setattr(instance, key, value)
        if hasattr(instance, 'modified_on'):
            instance.modified_on = datetime.utcnow()
        db.flush()
        if commit:
            db.commit()
        return instance, False

    combined_data = {**unique_keys, **update_data}
    if 'created_on' not in combined_data and hasattr(model_class, 'created_on'):
        combined_data['created_on'] = datetime.utcnow()
    
    instance = model_class(**combined_data)
    db.add(instance)
    
    try:
        db.flush()
        if commit:
            db.commit()
        return instance, True
    except IntegrityError:
        db.rollback()
        query = db.query(model_class)
        for key, value in unique_keys.items():
            query = query.filter(getattr(model_class, key) == value)
        if additional_filters:
            for key, value in additional_filters.items():
                if value is not None:
                    query = query.filter(getattr(model_class, key) == value)
        instance = query.first()
        if instance:
            for key, value in update_data.items():
                if key not in unique_keys:
                    if value is not None:
                        setattr(instance, key, value)
            if hasattr(instance, 'modified_on'):
                instance.modified_on = datetime.utcnow()
            db.flush()
            if commit:
                db.commit()
            return instance, False
        raise

