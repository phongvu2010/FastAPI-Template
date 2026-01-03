from sqlalchemy.orm import DeclarativeBase

# Định nghĩa Base Class
class Base(DeclarativeBase):
    pass

# Import tất cả các models để chúng được đăng ký với Base
# Trong thực tế, bạn sẽ dùng thư viện như Alembic để quản lý migrations.
from .users import *
from .documents import *
