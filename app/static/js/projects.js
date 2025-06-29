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

    // Function to fetch and render all projects' Gantt charts
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
                        let allTasks = [];
                        response.projects.forEach(function(project) {
                            ganttContainer.append(
                                '<div class="gantt-divider">' +
                                '<h2>' + (project.name || 'Unnamed Project') + '</h2>' +
                                '<hr>' +
                                '<div class="gantt-controls">' +
                                '<button class="view-mode" data-mode="Day">Day</button>' +
                                '<button class="view-mode" data-mode="Week">Week</button>' +
                                '<button class="view-mode" data-mode="Month">Month</button>' +
                                '</div>' +
                                '<div id="gantt-chart-' + (project.id || 'unknown') + '" class="gantt-chart"></div>' +
                                '</div>'
                            );
                            if (project.gantt_tasks && project.gantt_tasks.length > 0) {
                                allTasks = allTasks.concat(project.gantt_tasks.map(task => {
                                    let start = task.start || '';
                                    let end = task.end || '';
                                    if (start && !isNaN(Date.parse(start))) start = new Date(start).toISOString().split('T')[0];
                                    if (end && !isNaN(Date.parse(end))) end = new Date(end).toISOString().split('T')[0];
                                    let dependencies = task.dependencies || '';
                                    if (dependencies && typeof dependencies === 'string') {
                                        dependencies = dependencies.trim().split(' ').map(depName => {
                                            const depTask = project.gantt_tasks.find(t => t.name === depName);
                                            return depTask ? depTask.id : '';
                                        }).filter(id => id).join(' ');
                                    } else if (Array.isArray(dependencies)) {
                                        dependencies = dependencies.map(depName => {
                                            const depTask = project.gantt_tasks.find(t => t.name === depName);
                                            return depTask ? depTask.id : '';
                                        }).filter(id => id).join(' ');
                                    }
                                    return {
                                        id: task.id,
                                        name: task.name,
                                        start: start,
                                        end: end,
                                        progress: task.progress || 0,
                                        dependencies: dependencies,
                                        custom_class: task.custom_class || 'bar-blue',
                                        comment: task.comment || '' // Ensure comment is included
                                    };
                                }).filter(task => task.start && task.end && !isNaN(Date.parse(task.start)) && !isNaN(Date.parse(task.end))));
                            }
                        });
                        console.log("All Tasks:", allTasks); // Debug allTasks
                        if (allTasks.length > 0) {
                            const ganttElement = document.getElementById('gantt-chart-' + (response.projects[0].id || 'unknown'));
                            if (ganttElement && typeof Gantt !== 'undefined') {
                                // Override bind_bar_events (minimal, for locking only)
                                const originalBindBarEvents = Gantt.prototype.bind_bar_events;
                                Gantt.prototype.bind_bar_events = function() {
                                    this.bar_being_dragged = null;
                                    this.bar_being_resized = null;
                                    this.action_in_progress = false;
                                    this.$svg.addEventListener('mousedown', (e) => {
                                        if (e.target.closest('.bar-wrapper, .handle') && e.type !== 'click') {
                                            e.preventDefault();
                                            e.stopPropagation();
                                        }
                                    }, { capture: true });
                                    this.$svg.addEventListener('touchstart', (e) => {
                                        if (e.target.closest('.bar-wrapper, .handle')) {
                                            e.preventDefault();
                                            e.stopPropagation();
                                        }
                                    }, { capture: true });
                                    this.bind_bar_progress = function() { return false; };
                                    this.drag_bar = function() { return false; };
                                    this.resize_bar = function() { return false; };
                                    this.update_bar_position = function() { return false; };
                                };
                                window.gantt = new Gantt(ganttElement, allTasks, {
                                    view_mode: 'Week',
                                    date_format: 'YYYY-MM-DD',
                                    popup_trigger: 'click', // Re-enable click trigger
                                    custom_popup_html: function(task) {
                                        if (!task || typeof task.id === 'undefined') {
                                            console.warn("Invalid task object, falling back to DOM:", task);
                                            const bar = document.querySelector('.bar-wrapper.active') || document.querySelector('.bar-wrapper[data-id]');
                                            const taskId = bar ? bar.getAttribute('data-id') : null;
                                            const foundTask = taskId ? allTasks.find(t => t.id === taskId) : null;
                                            if (foundTask) {
                                                return `${foundTask.name} (Progress: ${foundTask.progress}%)<br>Comment: ${foundTask.comment || 'No comment'}`;
                                            }
                                            return "Unknown Task (Error)";
                                        }
                                        const taskId = task.id;
                                        const foundTask = allTasks.find(t => t.id === taskId);
                                        if (foundTask) {
                                            return `${foundTask.name} (Progress: ${foundTask.progress}%)<br>Comment: ${foundTask.comment || 'No comment'}`;
                                        } else {
                                            console.warn("Task not found in allTasks for ID:", taskId);
                                            return `${task.name || 'Unknown'} (Progress: ${task.progress || 0}%)<br>Comment: ${task.comment || 'No comment'}`;
                                        }
                                    },
                                    on_progress_change: null,
            on_date_change: null,
            on_drag_start: function() { return false; },
            on_resize_start: function() { return false; }
        });
        Gantt.prototype.bind_bar_events = originalBindBarEvents; // Restore original
        // View mode handlers
        $('.view-mode').off('click').on('click', function() {
            const mode = $(this).data('mode');
            if (window.gantt && typeof window.gantt.change_view_mode === 'function') {
                window.gantt.change_view_mode(mode);
                window.gantt.refresh(allTasks);
                console.log("Changed view mode to:", mode);
            } else {
                console.warn("Gantt change_view_mode not available");
            }
        });
        setTimeout(() => window.gantt.refresh(allTasks), 100);
    } else {
        console.warn("Gantt element or library not available");
        ganttContainer.append('<p>Unable to initialize Gantt chart.</p>');
    }
    } else {
        ganttContainer.append('<p>No valid Gantt data available.</p>');
    }
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