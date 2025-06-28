from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from .extensions import db
from .models import Task, User, Project
import json
from datetime import datetime
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash

bp = Blueprint('main', __name__)

# --- Forms ---
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# --- Authentication Routes ---
@bp.route('/')
def index():
    return render_template("index.html")

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.tasks'))
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        new_user = User(username=username)
        new_user.set_password(password)  # Ensure this sets password_hash
        db.session.add(new_user)
        db.session.commit()
        print("User before commit:", new_user.__dict__)  # Debug print moved here
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('main.login'))
    # Debug form errors if validation fails
    if form.errors:
        print("Form errors:", form.errors)
    return render_template('register.html', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.tasks'))
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):  # Assuming check_password verifies the hash
            login_user(user)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.tasks'))
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

# --- Project Management Routes ---
@bp.route('/projects', methods=['GET', 'POST'])
@login_required
def projects():
    if request.method == 'POST':
        project_name = request.form.get('project_name')
        project_description = request.form.get('description')
        if not project_name:
            flash('Project name is required!', 'error')
        else:
            new_project = Project(name=project_name, description=project_description, user=current_user)
            db.session.add(new_project)
            db.session.commit()
            flash(f'Project "{project_name}" created successfully!', 'success')
            return redirect(url_for('main.projects'))
    user_projects = Project.query.filter_by(user=current_user).order_by(Project.name).all()
    return render_template('projects.html', projects=user_projects)

@bp.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        flash('You do not have permission to delete this project.', 'error')
        return redirect(url_for('main.projects'))
    try:
        # Delete all tasks associated with the project
        Task.query.filter_by(project_id=project_id).delete()
        db.session.delete(project)
        db.session.commit()
        flash('Project and its tasks deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the project.', 'error')
        print("Delete project error:", str(e))
    return redirect(url_for('main.projects'))

@bp.route('/projects/<int:project_id>')
@login_required
def view_project(project_id):
    project = Project.query.filter_by(id=project_id, user=current_user).first_or_404()
    project_tasks = Task.query.filter_by(project=project).order_by(Task.name).all()
    gantt_tasks_data = []
    task_name_to_id = {task.name.strip(): str(task.id) for task in project_tasks}  # Strip whitespace
    print("Task name to ID mapping:", task_name_to_id)  # Debug mapping
    for task in project_tasks:
        start_date_formatted = task.start_date.strftime('%Y-%m-%d') if task.start_date else ''
        end_date_formatted = task.end_date.strftime('%Y-%m-%d') if task.end_date else ''
        if start_date_formatted and end_date_formatted:
            custom_class = 'bar-blue'
            if task.status == 'Completed':
                custom_class = 'bar-green'
            elif task.status == 'In Progress':
                custom_class = 'bar-yellow'
            elif task.status == 'Blocked':
                custom_class = 'bar-red'
            gantt_task_item = {
                'id': str(task.id),
                'name': task.name,
                'start': start_date_formatted,
                'end': end_date_formatted,
                'progress': task.progress,
                'custom_class': custom_class,
                'comment': task.comment if task.comment else 'No comment',
            }
            print(f"Task {task.id} raw dependency (name): {task.dependencies}")  # Debug raw value
            if task.dependencies and task.dependencies != 'None':
                dep_id = task_name_to_id.get(task.dependencies.strip())
                print(f"Converted dependency for task {task.id}: {dep_id}")  # Debug conversion
                if dep_id:
                    gantt_task_item['dependencies'] = str(dep_id)  # Ensure string format
            gantt_tasks_data.append(gantt_task_item)
    # Sort by start date
    gantt_tasks_data.sort(key=lambda x: datetime.strptime(x['start'], '%Y-%m-%d'))
    gantt_tasks_json = json.dumps(gantt_tasks_data)
    print("Gantt tasks JSON:", gantt_tasks_json)  # Debug final JSON
    return render_template('tasks.html', project=project, tasks=project_tasks, gantt_tasks_json=gantt_tasks_json)

# --- Task Management Routes ---
@bp.route('/projects/<int:project_id>/add_task', methods=['GET', 'POST'])
@login_required
def add_task_to_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'You do not have permission to add tasks to this project.'}), 403
        flash('You do not have permission to add tasks to this project.', 'error')
        return redirect(url_for('main.projects'))
    if request.method == 'POST':
        task_name = request.form.get('task_name') or request.form.get('task_name_other')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        progress = request.form.get('progress', '0')  # Default to 0 if not set
        status = request.form.get('status')
        dependencies = request.form.getlist('dependencies')  # Multiple values
        errors = []
        if not task_name:
            errors.append('Task name is required.')
        if not status:
            errors.append('Status is required.')
        try:
            progress = int(progress)
            if not (0 <= progress <= 100):
                errors.append('Progress must be between 0 and 100.')
        except ValueError:
            errors.append('Progress must be a valid number.')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        if start_date and end_date and start_date > end_date:
            errors.append('End date cannot be before start date.')
        dependencies_str = ','.join(dependencies) if dependencies and 'None' not in dependencies else None
        if errors:
            print("Add task errors:", errors)  # Debug
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'errors': errors}), 400
            for error in errors:
                flash(error, 'error')
            return render_template('add_task_to_project.html', project=project), 400
        new_task = Task(
            name=task_name,
            start_date=start_date,
            end_date=end_date,
            progress=progress,
            status=status,
            dependencies=dependencies_str,
            project_id=project.id,
            user_id=current_user.id
        )
        db.session.add(new_task)
        db.session.commit()
        print("New task added:", new_task.id, new_task.name, "dependency:", new_task.dependencies)  # Debug
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Task added successfully!', 'task_id': new_task.id, 'project_id': project.id}), 201
        flash('Task added successfully!', 'success')
        return redirect(url_for('main.view_project', project_id=project.id))
    return render_template('add_task_to_project.html', project=project)

@bp.route('/tasks', methods=['GET'])
@login_required
def tasks():
    flash("Please select a project to view/manage tasks.", "info")
    return redirect(url_for('main.projects'))

@bp.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.project.user_id != current_user.id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'You do not have permission to edit this task.'}), 403
        flash('You do not have permission to edit this task.', 'error')
        return redirect(url_for('main.projects'))
    if request.method == 'POST':
        task_name = request.form.get('task_name') or request.form.get('task_name_other')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        progress = request.form.get('progress')
        status = request.form.get('status')
        dependencies = request.form.getlist('dependencies')  # Multiple values
        comment = request.form.get('comment')
        errors = []
        if not task_name:
            errors.append('Task name is required.')
        if not status:
            errors.append('Status is required.')
        try:
            progress = int(progress)
            if not (0 <= progress <= 100):
                errors.append('Progress must be between 0 and 100.')
        except ValueError:
            errors.append('Progress must be a valid number.')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        if start_date and end_date and start_date > end_date:
            errors.append('End date cannot be before start date.')
        if errors:
            print("Edit task errors:", errors)  # Debug
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'errors': errors}), 400
            for error in errors:
                flash(error, 'error')
            return render_template('edit_task.html', task=task, current_project=task.project), 400
        task.name = task_name
        task.start_date = start_date
        task.end_date = end_date
        task.progress = progress
        task.status = status
        task.dependencies = ','.join(dependencies) if dependencies and 'None' not in dependencies else None
        task.comment = comment
        db.session.commit()
        print("Task updated:", task.id, task.name, "dependency:", task.dependencies)  # Debug
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Task updated successfully!', 'task_id': task.id, 'project_id': task.project_id}), 200
        flash('Task updated successfully!', 'success')
        return redirect(url_for('main.view_project', project_id=task.project_id))
    return render_template('edit_task.html', task=task, current_project=task.project)

@bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    print(f"DEBUG: Delete request for task {task_id}. Is AJAX: {is_ajax}")
    if task.project.user_id != current_user.id:
        if is_ajax:
            return jsonify({'success': False, 'message': 'You do not have permission to delete this task.'}), 403
        flash('You do not have permission to delete this task.', 'error')
        return redirect(url_for('main.view_project', project_id=task.project_id))
    try:
        db.session.delete(task)
        db.session.commit()
        if is_ajax:
            return jsonify({'success': True, 'message': 'Task deleted successfully!'}), 200
        flash('Task deleted successfully!', 'success')
        return redirect(url_for('main.view_project', project_id=task.project_id))
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting task: {e}")
        if is_ajax:
            return jsonify({'success': False, 'message': 'An unexpected server error occurred while deleting the task.'}), 500
        flash('An unexpected error occurred while deleting the task.', 'error')
        return redirect(url_for('main.view_project', project_id=task.project_id))

@bp.route('/projects/<int:project_id>/update_comment/<int:task_id>', methods=['POST'])
@login_required
def update_comment(project_id, task_id):
    task = Task.query.get_or_404(task_id)
    if task.project.user_id != current_user.id or task.project_id != project_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    comment = request.get_json().get('comment')  # Handle JSON
    if comment:
        task.comment = comment.strip()
        try:
            db.session.commit()
            return jsonify({'success': True, 'message': 'Comment updated!'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
    return jsonify({'success': False, 'message': 'No comment'}), 400

@bp.route('/api/projects/<int:project_id>/tasks', methods=['GET'])
@login_required
def api_get_project_tasks(project_id):
    print("--- DEBUG: api_get_project_tasks function was called! ---")
    project = Project.query.filter_by(id=project_id, user=current_user).first_or_404()
    project_tasks = Task.query.filter_by(project=project).order_by(Task.start_date.asc()).all()
    print(f"Tasks fetched for project {project_id}, ordered by start_date:")
    for task in project_tasks:
        print(f"  Task ID: {task.id}, Name: {task.name}, Start Date: {task.start_date}, Comment: {task.comment}")
    tasks_data = []
    gantt_tasks_data = []
    for task in project_tasks:
        tasks_data.append({
            'id': task.id,
            'name': task.name,
            'start_date': task.start_date.strftime('%Y-%m-%d') if task.start_date else '',
            'end_date': task.end_date.strftime('%Y-%m-%d') if task.end_date else '',
            'progress': task.progress,
            'status': task.status,
            'comment': task.comment if task.comment else ''  # Add comment here
        })
        start_date_formatted = task.start_date.strftime('%Y-%m-%d') if task.start_date else ''
        end_date_formatted = task.end_date.strftime('%Y-%m-%d') if task.end_date else ''
        custom_class = 'bar-blue'
        if task.status == 'Completed':
            custom_class = 'bar-green'
        elif task.status == 'In Progress':
            custom_class = 'bar-yellow'
        elif task.status == 'Blocked':
            custom_class = 'bar-red'
        gantt_task_item = {
            'id': str(task.id),
            'name': task.name,
            'start': start_date_formatted,
            'end': end_date_formatted,
            'progress': task.progress,
            'custom_class': custom_class,
            'comment': task.comment if task.comment else ''  # Add comment here
        }
        if task.dependencies:
            gantt_task_item['dependencies'] = task.dependencies
        gantt_tasks_data.append(gantt_task_item)
    return jsonify({
        'success': True,
        'tasks': tasks_data,
        'gantt_tasks': gantt_tasks_data,
        'messages': []
    })

@bp.route('/api/tasks/<int:task_id>/comment', methods=['GET', 'POST'])
@login_required
def task_comment_api(task_id):
    task = Task.query.get_or_404(task_id)
    if task.project.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'comment': task.comment if task.comment else ''
        })
    elif request.method == 'POST':
        data = request.get_json()
        new_comment = data.get('comment', '').strip()
        task.comment = new_comment
        try:
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Comment updated successfully!',
                'comment': task.comment
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Error saving comment: {str(e)}'}), 500

@bp.route('/test_gantt')
def test_gantt():
    return render_template('test_gantt.html')