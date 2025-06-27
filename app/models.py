from .extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    # Relationship: A User can have many Projects
    projects = db.relationship('Project', backref='user', lazy=True, cascade="all, delete-orphan") # <--- NEW
    # Relationship: A User can have many Tasks (if you want tasks to be directly owned by users too, uncomment below)
    # tasks = db.relationship('Task', backref='user', lazy=True, cascade="all, delete-orphan") # <--- OPTIONAL: If tasks are directly user-owned

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

# NEW: Project Model
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True) # Optional: for project details

    # Foreign Key to User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # <--- Project belongs to a User

    # Relationship: A Project can have many Tasks
    tasks = db.relationship('Task', backref='project', lazy=True, cascade="all, delete-orphan") # <--- NEW

    def __repr__(self):
        return f'<Project {self.id}: {self.name}>'

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    progress = db.Column(db.Integer, default=0, nullable=False)
    dependencies = db.Column(db.String(255), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

    status = db.Column(db.String(50), default='To Do', nullable=False) # <--- NEW: Status field

    def __repr__(self):
        return f'<Task {self.id}: {self.name}>'