# from datetime import datetime
# from sqlalchemy import event
# from sqlmodel import SQLModel

# @event.listens_for(SQLModel, "before_update", propagate=True)
# def timestamp_before_update(mapper, connection, target):
#     if hasattr(target, "updated_at"):
#         target.updated_at = datetime.utcnow()
