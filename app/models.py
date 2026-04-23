
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.custom_orm import ModelBase

class User(ModelBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Staff(ModelBase):
    __tablename__ = "staff"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    position = Column(String, nullable=True)
    email = Column(String, nullable=True)
    image = Column(String, nullable=True)
    expertise = Column(String, nullable=True)
    type = Column(String, default="faculty") # faculty, executive, support
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Page(ModelBase):
    __tablename__ = "pages"
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text)
    template = Column(String, default="page")
    is_published = Column(Integer, default=0) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class Menu(ModelBase):
    __tablename__ = "menus"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    data_json = Column(Text) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Setting(ModelBase):
    __tablename__ = "settings"
    key = Column(String, primary_key=True)
    value = Column(Text)

class Appeal(ModelBase):
    __tablename__ = "appeals"
    id = Column(Integer, primary_key=True, index=True)
    sender_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    topic = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_anonymous = Column(Integer, default=0)
    status = Column(String, default="pending") 
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Tag(ModelBase):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class News(ModelBase):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    category = Column(String, default="General")
    tags = Column(String, nullable=True) # Comma-separated tags
    event_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Activity(ModelBase):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    category = Column(String, default="Activity") # Added for consistency
    tags = Column(String, nullable=True) # Added for consistency
    event_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class FacultyCV(ModelBase):
    __tablename__ = "faculty_cv"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, nullable=False) # Maps to external DB user_id
    cv_file = Column(String, nullable=False) # Filename in /uploads

class Banner(ModelBase):
    __tablename__ = "banners"
    __table_args__ = {"schema": "api"}
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    subtitle = Column(String, nullable=True)
    video_url = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    is_active = Column(Integer, default=1)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Mission(ModelBase):
    __tablename__ = "missions"
    __table_args__ = {"schema": "api"}
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    desc = Column(Text, nullable=True)
    icon = Column(String, nullable=False) # e.g. 'academic-cap', 'globe'
    color = Column(String, default="green") # green, blue, cyan, etc.
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Course(ModelBase):
    __tablename__ = "courses"
    __table_args__ = {"schema": "api"}
    id = Column(Integer, primary_key=True, index=True)
    title_th = Column(String, nullable=False)
    title_en = Column(String, nullable=True)
    video_url = Column(String, nullable=False) # YouTube ID or URL
    description = Column(Text, nullable=True)
    color_theme = Column(String, default="green")
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Statistic(ModelBase):
    __tablename__ = "statistics"
    __table_args__ = {"schema": "api"}
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, nullable=False)
    value = Column(Integer, nullable=False)
    suffix = Column(String, nullable=True) # e.g. '+'
    icon = Column(String, nullable=True)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Award(ModelBase):
    __tablename__ = "awards"
    __table_args__ = {"schema": "api"}
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String, nullable=True) 
    image_url = Column(String, nullable=True) # Added for full banner images
    color_theme = Column(String, default="yellow") # yellow, blue, purple
    link_url = Column(String, nullable=True)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ContactInfo(ModelBase):
    __tablename__ = "contact_info"
    __table_args__ = {"schema": "api"}
    key = Column(String, primary_key=True) # address, phone, email, facebook, etc.
    value = Column(Text, nullable=True)
    icon = Column(String, nullable=True)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Faculty(ModelBase):
    __tablename__ = "faculty"
    __table_args__ = {"schema": "api"}
    id = Column(Integer, primary_key=True, index=True)
    prefix = Column(String, nullable=True)
    fname = Column(String, nullable=False)
    lname = Column(String, nullable=False)
    fname_en = Column(String, nullable=True)
    lname_en = Column(String, nullable=True)
    position = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    image = Column(String, nullable=True)
    major = Column(String, nullable=True)
    admin_position = Column(String, nullable=True)
    is_expert = Column(Boolean, default=False)
    expertise = Column(JSONB, nullable=True) # Maps precisely to postgres JSONB
    scholar_id = Column(String, nullable=True) # Google Scholar Author ID
    scholar_data = Column(JSONB, nullable=True) 
    cited = Column(JSONB, nullable=True) 
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


