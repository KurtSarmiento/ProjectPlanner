$(document).ready(function() {
    // Function to show modal
    function showModal(modalId, message, isError = false) {
        const modal = $('#' + modalId);
        const flashes = $('#modal-flashes');
        flashes.empty();
        if (isError && Array.isArray(message)) {
            message.forEach(function(msg) {
                flashes.append('<li class="error">' + msg + '</li>');
            });
        } else {
            $('#success-message').text(message);
        }
        modal.show();
    }

    // Function to close modal
    function closeModal(modalId) {
        $('#' + modalId).hide();
        $('#modal-flashes').empty();
    }

    // Close modal when clicking the close button
    $('.close-button').click(function() {
        $(this).closest('.modal').hide();
        $('#modal-flashes').empty();
    });

    // Delete task button handler
    $(document).on('click', '.delete-task-btn', function(e) {
        e.preventDefault();
        const taskId = $(this).data('task-id');
        if (confirm('Are you sure you want to delete this task?')) {
            $.ajax({
                url: '/tasks/' + taskId + '/delete',
                type: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRF-Token': $('meta[name="csrf-token"]').attr('content')
                },
                success: function(response) {
                    if (response.success) {
                        $('#task-' + taskId).remove();
                        showModal('successModal', response.message);
                        fetchTasks(projectId); // Assumes projectId is available globally
                    } else {
                        showModal('errorModal', [response.message], true);
                    }
                },
                error: function(xhr) {
                    const message = xhr.responseJSON ? xhr.responseJSON.message : 'Unknown error';
                    showModal('errorModal', [message], true);
                }
            });
        }
    });

    // Edit task form submission
    $('#edit-task-form').submit(function(e) {
        e.preventDefault();
        $.ajax({
            url: $(this).attr('action'),
            type: 'POST',
            data: $(this).serialize(),
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRF-Token': $('meta[name="csrf-token"]').attr('content')
            },
            success: function(response) {
                if (response.success) {
                    showModal('successModal', response.message);
                    setTimeout(function() {
                        window.location.href = '/projects/' + response.project_id;
                    }, 1000);
                } else {
                    showModal('errorModal', response.errors, true);
                }
            },
            error: function(xhr) {
                const message = xhr.responseJSON ? xhr.responseJSON.message : 'Unknown error';
                showModal('errorModal', [message], true);
            }
        });
    });

    // Add task form submission
    $('#add-task-form').submit(function(e) {
        e.preventDefault();
        $.ajax({
            url: $(this).attr('action'),
            type: 'POST',
            data: $(this).serialize(),
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRF-Token': $('meta[name="csrf-token"]').attr('content')
            },
            success: function(response) {
                if (response.success) {
                    showModal('successModal', response.message);
                    setTimeout(function() {
                        window.location.href = '/projects/' + response.project_id;
                    }, 1000);
                } else {
                    showModal('errorModal', response.errors, true);
                }
            },
            error: function(xhr) {
                const message = xhr.responseJSON ? xhr.responseJSON.message : 'Unknown error';
                showModal('errorModal', [message], true);
            }
        });
    });

    // Initialize projectId from URL or hidden input (adjust as needed)
    var projectId = window.location.pathname.split('/')[2]; // Assumes URL is /projects/<project_id>
    fetchTasks(projectId); // Initial fetch to ensure task list and Gantt chart are in sync

    // Comment modal handling
    window.showCommentModal = function(taskId, taskName) {
        if (!taskId || isNaN(parseInt(taskId))) {
            console.warn("Invalid taskId:", taskId, "skipping modal for", taskName, "called from:", new Error().stack);
            return; // Prevent invalid calls and log call origin
        }
        console.log("Opening modal for taskId:", taskId, "name:", taskName);
        $('#commentTaskName').text(taskName).data('task-id', taskId); // Set data-task-id
        $('#taskCommentTextarea').val(''); // Clear textarea
        $.ajax({
            url: '/api/tasks/' + taskId + '/comment',
            type: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRF-Token': $('meta[name="csrf-token"]').attr('content')
            },
            success: function(response) {
                if (response.success) {
                    $('#taskCommentTextarea').val(response.comment || '');
                    $('#commentModal').show();
                } else {
                    showModal('errorModal', [response.message], true);
                }
            },
            error: function(xhr) {
                showModal('errorModal', [xhr.responseJSON ? xhr.responseJSON.message : 'Unknown error'], true);
            }
        });
    };

    // Function to fetch tasks and refresh Gantt chart
    function fetchTasks(projectId) {
        $.ajax({
            url: '/api/projects/' + projectId + '/tasks',
            type: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRF-Token': $('meta[name="csrf-token"]').attr('content')
            },
            success: function(response) {
                if (response.success) {
                    const taskList = $('#task-list');
                    taskList.empty();
                    if (response.tasks.length > 0) {
                        response.tasks.forEach(function(task) {
                            taskList.append(
                                '<li id="task-' + task.id + '">' +
                                task.name +
                                ' (Starts: ' + (task.start_date || 'N/A') +
                                ', Ends: ' + (task.end_date || 'N/A') +
                                ', Progress: ' + task.progress + '%' +
                                ', Status: ' + task.status + ')' +
                                ' <a href="/tasks/' + task.id + '/edit">Edit</a>' +
                                ' <form action="/tasks/' + task.id + '/delete" method="POST" style="display:inline;" class="delete-task-form">' +
                                '<input type="hidden" name="csrf_token" value="' + $('meta[name="csrf-token"]').attr('content') + '">' +
                                '<button type="submit" class="delete-task-btn" data-task-id="' + task.id + '">Delete</button>' +
                                '</form></li>'
                            );
                        });
                    } else {
                        taskList.append('<li>No tasks yet for this project. Add one above!</li>');
                    }
                    if (typeof refreshGantt === 'function') {
                        refreshGantt(response.gantt_tasks);
                    } else {
                        console.warn("refreshGantt not available, retrying...");
                        setTimeout(() => {
                            if (typeof refreshGantt === 'function') {
                                refreshGantt(response.gantt_tasks);
                            }
                        }, 500);
                    }
                } else {
                    showModal('errorModal', [response.message], true);
                }
            },
            error: function(xhr) {
                const message = xhr.responseJSON ? xhr.responseJSON.message : 'Unknown error';
                showModal('errorModal', [message], true);
            }
        });
    }

    // Save comment
    $('#saveCommentButton').click(function() {
        const taskId = $('#commentTaskName').data('task-id'); // Rely on data-task-id set by showCommentModal
        const comment = $('#taskCommentTextarea').val().trim();
        if (!comment) {
            showModal('errorModal', ['Comment cannot be empty'], true);
            return;
        }
        if (!taskId || isNaN(taskId)) {
            showModal('errorModal', ['Invalid task ID'], true);
            return;
        }
        $.ajax({
            url: '/api/tasks/' + taskId + '/comment',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ comment: comment }),
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRF-Token': $('meta[name="csrf-token"]').attr('content')
            },
            success: function(response) {
                if (response.success) {
                    showModal('successModal', response.message);
                    $('#commentModal').hide();
                    fetchTasks(projectId); // Refresh task list
                } else {
                    showModal('errorModal', [response.message], true);
                }
            },
            error: function(xhr) {
                const message = xhr.responseJSON ? xhr.responseJSON.message : 'Unknown error';
                showModal('errorModal', [message], true);
            }
        });
    });
});