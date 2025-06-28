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

    // Add project form submission
    $('#add-project-form').submit(function(e) {
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
                        window.location.reload();
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

    // Fetch and render all projects with Gantt charts
    function fetchAndRenderGanttCharts() {
        $.ajax({
            url: '/api/projects',
            type: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRF-Token': $('meta[name="csrf-token"]').attr('content')
            },
            success: function(response) {
                console.log("API Response:", response); // Debug API response
                if (response.success) {
                    const ganttContainer = $('#gantt-charts-container');
                    ganttContainer.empty();
                    if (response.projects && response.projects.length > 0) {
                        response.projects.forEach(function(project) {
                            ganttContainer.append(
                                '<div class="gantt-divider">' +
                                '<h2>' + (project.name || 'Unnamed Project') + '</h2>' +
                                '<hr>' +
                                '<div id="gantt-chart-' + (project.id || 'unknown') + '" class="gantt-chart"></div>' +
                                '</div>'
                            );
                            if (typeof Gantt !== 'undefined' && project.gantt_tasks && project.gantt_tasks.length > 0) {
                                new Gantt("#gantt-chart-" + (project.id || 'unknown'), project.gantt_tasks, {
                                    on_click: function(task) {
                                        window.showCommentModal(parseInt(task.id), task.name);
                                    },
                                    view_mode: 'Week',
                                    date_format: 'YYYY-MM-DD',
                                    custom_popup_html: function(task) {
                                        const comment = project.gantt_tasks.find(t => t.id === task.id)?.comment || 'No comment';
                                        return `${task.name} (Progress: ${task.progress}%)<br>Comment: ${comment}`;
                                    },
                                    popup_trigger: 'click',
                                    on_progress_change: null,
                                    on_date_change: null,
                                    on_drag_start: function() { return false; },
                                    on_resize_start: function() { return false; }
                                });
                            } else {
                                console.warn("Gantt library or tasks not available for project:", project.name || project.id);
                                ganttContainer.append('<p>No Gantt data available for this project.</p>');
                            }
                        });
                    } else {
                        ganttContainer.append('<p>No projects with Gantt data available.</p>');
                    }
                } else {
                    showModal('errorModal', [response.message || 'Failed to load projects'], true);
                }
            },
            error: function(xhr) {
                const message = xhr.responseJSON ? xhr.responseJSON.message : 'Unknown error';
                console.error("API Error:", xhr); // Debug error
                showModal('errorModal', [message], true);
            }
        });
    }

    // Initialize
    fetchAndRenderGanttCharts();
});

// Global comment modal function
window.showCommentModal = function(taskId, taskName) {
    if (!taskId || isNaN(parseInt(taskId))) {
        console.warn("Invalid taskId:", taskId, "skipping modal for", taskName, "called from:", new Error().stack);
        return;
    }
    console.log("Opening modal for taskId:", taskId, "name:", taskName);
    $('#commentTaskName').text(taskName).data('task-id', taskId);
    $('#taskCommentTextarea').val('');
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