from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from .extensions import db
from .models import Task, User, Project # <--- IMPORT PROJECT MODEL
import json
from datetime import datetime
from flask_login import login_user, logout_user, login_required, current_user

bp = Blueprint('main', __name__)

# --- Authentication Routes (No Change) ---
@bp.route('/')
def index():
    return render_template("index.html")

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.tasks'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        user = User.query.filter_by(username=username).first()

        if user:
            flash('Username already exists. Please choose a different one.', 'error')
        elif password != confirm_password:
            flash('Passwords do not match.', 'error')
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('main.login'))
    return render_template('register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.tasks'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.tasks')) # Redirect to tasks or prev page
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html')

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
        project_description = request.form.get('project_description')

        if project_name:
            new_project = Project(name=project_name, description=project_description, user=current_user)
            db.session.add(new_project)
            db.session.commit()
            flash(f'Project "{project_name}" created successfully!', 'success')
            return redirect(url_for('main.projects'))
        else:
            flash('Project name is required!', 'error')

    # Only fetch projects belonging to the current user
    user_projects = Project.query.filter_by(user=current_user).order_by(Project.name).all()
    return render_template('projects.html', projects=user_projects)

@bp.route('/projects/<int:project_id>')
@login_required
def view_project(project_id):
    # Get the project, ensure it belongs to the current user
    project = Project.query.filter_by(id=project_id, user=current_user).first_or_404()

    # Get all tasks for THIS project, ordered by name/start_date
    project_tasks = Task.query.filter_by(project=project).order_by(Task.name).all()

    # Prepare tasks for the Gantt chart (only for this project's tasks)
    gantt_tasks_data = []
    for task in project_tasks:
        start_date_formatted = task.start_date.strftime('%Y-%m-%d') if task.start_date else ''
        end_date_formatted = task.end_date.strftime('%Y-%m-%d') if task.end_date else ''

        if start_date_formatted and end_date_formatted:
            custom_class = 'bar-blue' # Default
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
            }
            if task.dependencies:
                gantt_task_item['dependencies'] = task.dependencies
            gantt_tasks_data.append(gantt_task_item)

    try:
        gantt_tasks_json = json.dumps(gantt_tasks_data)
    except TypeError as e:
        print(f"Error serializing Gantt data to JSON: {e}")
        gantt_tasks_json = "[]"

    return render_template('tasks.html',
                           project=project,
                           tasks=project_tasks, # These are the tasks for the current project
                           gantt_tasks_json=gantt_tasks_json)


# --- Task Management Routes (Modified to include project_id) ---

@bp.route('/projects/<int:project_id>/add_task', methods=['GET', 'POST'])
@login_required
def add_task_to_project(project_id):
    project = Project.query.filter_by(id=project_id, user=current_user).first_or_404()
    all_tasks_in_current_project = Task.query.filter_by(project=project).all()

    if request.method == 'POST':
        task_name = request.form.get('task_name')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        progress_str = request.form.get('progress')
        selected_dependencies = request.form.getlist('dependencies')
        status_str = request.form.get('status')

        # Determine if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        errors = []
        if not task_name:
            errors.append("Task name is required!")

        start_date_obj = None
        end_date_obj = None
        try:
            if start_date_str:
                start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            if end_date_str:
                end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            errors.append("Invalid date format.")

        if end_date_obj and start_date_obj and end_date_obj < start_date_obj:
            errors.append("End Date cannot be before Start Date. Please correct the dates.")

        progress_val = 0
        if progress_str is not None:
            try:
                progress_val = int(progress_str)
                if not (0 <= progress_val <= 100):
                    errors.append("Progress must be between 0 and 100.")
                    progress_val = 0 # Reset to default if invalid
            except ValueError:
                errors.append("Invalid progress format.")

        if errors:
            if is_ajax:
                return jsonify({'success': False, 'errors': errors}), 400 # Bad Request
            else:
                for error in errors:
                    flash(error, 'error')
                return render_template('add_task_to_project.html', project=project, all_tasks=all_tasks_in_current_project)

        # If no errors, proceed to add task
        dependencies_str = ",".join(selected_dependencies) if selected_dependencies else None

        new_task = Task(name=task_name,
                        start_date=start_date_obj,
                        end_date=end_date_obj,
                        progress=progress_val,
                        dependencies=dependencies_str,
                        status=status_str,
                        project=project)
        db.session.add(new_task)
        db.session.commit()

        if is_ajax:
            return jsonify({'success': True, 'message': f'Task "{task_name}" added successfully!'})
        else:
            flash(f'Task "{task_name}" added successfully to {project.name}!', 'success')
            return redirect(url_for('main.view_project', project_id=project.id))

    # GET request handling remains the same for initial page load
    return render_template('add_task_to_project.html', project=project, all_tasks=all_tasks_in_current_project)

# Keep the original /tasks route for now, but it will no longer be the primary way
# to add/view tasks once projects are implemented.
# We will likely remove it or refactor it later.
@bp.route('/tasks', methods=['GET']) # Removed POST as add_task_to_project handles it
@login_required
def tasks():
    flash("Please select a project to view/manage tasks.", "info")
    return redirect(url_for('main.projects'))


@bp.route('/tasks/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.project.user != current_user:
        flash("You are not authorized to edit this task.", "error")
        return redirect(url_for('main.projects'))

    all_tasks_in_current_project = Task.query.filter_by(project=task.project).all()

    if request.method == 'POST':
        # Determine if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        original_project_id = task.project.id # Keep this for redirection if not AJAX

        task.name = request.form.get('task_name')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        progress_str = request.form.get('progress')
        selected_dependencies = request.form.getlist('dependencies')
        status_str = request.form.get('status')

        errors = []

        # Date parsing and validation
        try:
            task.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            task.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        except ValueError:
            errors.append("Invalid date format.")

        if task.end_date and task.start_date and task.end_date < task.start_date:
            errors.append("End Date cannot be before Start Date. Please correct the dates.")

        # Progress validation
        if progress_str is not None:
            try:
                task.progress = int(progress_str)
                if not (0 <= task.progress <= 100):
                    errors.append("Progress must be between 0 and 100.")
                    task.progress = 0 # Reset if invalid
            except ValueError:
                errors.append("Invalid progress format.")

        if errors:
            if is_ajax:
                return jsonify({'success': False, 'errors': errors}), 400
            else:
                for error in errors:
                    flash(error, 'error')
                return render_template('edit_task.html', task=task, all_tasks=all_tasks_in_current_project, current_project=task.project)

        # If no errors, proceed to update task
        task.dependencies = ",".join(selected_dependencies) if selected_dependencies else None
        task.status = status_str

        db.session.commit()

        if is_ajax:
            return jsonify({'success': True, 'message': 'Task updated successfully!'})
        else:
            flash('Task updated successfully!', 'success')
            return redirect(url_for('main.view_project', project_id=original_project_id)) # Use original_project_id for non-AJAX

    # GET request handling remains the same
    return render_template('edit_task.html', task=task, all_tasks=all_tasks_in_current_project, current_project=task.project)

@bp.route('/tasks/delete/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.project.user != current_user:
        # If AJAX, return forbidden status
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': "You are not authorized to delete this task."}), 403
        else:
            flash("You are not authorized to delete this task.", "error")
            return redirect(url_for('main.projects'))

    project_id = task.project.id # Store project_id before deleting task
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    try:
        db.session.delete(task)
        db.session.commit()
        if is_ajax:
            return jsonify({'success': True, 'message': 'Task deleted successfully!'})
        else:
            flash('Task deleted successfully!', 'success')
            return redirect(url_for('main.view_project', project_id=project_id))
    except Exception as e:
        db.session.rollback()
        if is_ajax:
            return jsonify({'success': False, 'message': f"Error deleting task: {e}"}), 500
        else:
            flash(f"Error deleting task: {e}", 'error')
            return redirect(url_for('main.view_project', project_id=project_id))
        
# Inside routes.py, define after other routes
@bp.route('/api/projects/<int:project_id>/tasks', methods=['GET'])
@login_required
def api_get_project_tasks(project_id):
    project = Project.query.filter_by(id=project_id, user=current_user).first_or_404()
    project_tasks = Task.query.filter_by(project=project).order_by(Task.name).all()

    tasks_data = []
    gantt_tasks_data = []

    for task in project_tasks:
        # Prepare data for task list rendering
        tasks_data.append({
            'id': task.id,
            'name': task.name,
            'start_date': task.start_date.strftime('%Y-%m-%d') if task.start_date else '',
            'end_date': task.end_date.strftime('%Y-%m-%d') if task.end_date else '',
            'progress': task.progress,
            'status': task.status
        })

        # Prepare data for Gantt chart
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
            'custom_class': custom_class
        }
        if task.dependencies:
            gantt_task_item['dependencies'] = task.dependencies
        gantt_tasks_data.append(gantt_task_item)

    return jsonify({
        'tasks': tasks_data,
        'gantt_data': gantt_tasks_data
    })

# In routes.py
@bp.route('/test_gantt')
def test_gantt():
    return render_template('test_gantt.html')