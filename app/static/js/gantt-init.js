// gantt-init.js
document.addEventListener('DOMContentLoaded', function() {
    const tasks = JSON.parse(document.getElementById('gantt-tasks-data').textContent);
    console.log("Gantt tasks data:", tasks);
    if (!window.Gantt) {
        console.error("Gantt library not loaded. Check frappe-gantt.min.js inclusion.");
        return;
    }

    // Store the original bind_bar_events if needed for debugging
    const originalBindBarEvents = Gantt.prototype.bind_bar_events;

    // Override bind_bar_events globally for all Gantt instances
    Gantt.prototype.bind_bar_events = function() {
        this.bar_being_dragged = null;
        this.bar_being_resized = null;
        this.action_in_progress = false;

        console.log("bind_bar_events override applied. SVG:", this.$svg); // Debug SVG availability

        // Allow popup on click only (native event listener)
        this.$svg.addEventListener(this.options.popup_trigger, (e) => {
            const bar_wrapper = e.target.closest('.bar-wrapper');
            if (bar_wrapper && !this.action_completed) {
                this.show_popup({
                    target_element: bar_wrapper.querySelector('.bar'),
                    title: bar_wrapper.getAttribute('data-id'),
                    task: this.get_task(bar_wrapper.getAttribute('data-id')),
                    subtitle: ''
                });
                this.unselect_all();
                bar_wrapper.classList.add('active');
                e.stopPropagation();
            }
        }, { capture: true }); // Use capture phase to intercept early

        // Block all drag and resize interactions (native event listeners)
        ['mousedown', 'mousemove', 'mouseup', 'touchstart', 'touchmove', 'touchend'].forEach(event => {
            this.$svg.addEventListener(event, (e) => {
                const target = e.target.closest('.bar-wrapper, .handle');
                if (target && event !== 'click') { // Avoid blocking click for popup
                    e.preventDefault();
                    e.stopPropagation();
                } else if (target && event === 'click') {
                }
            }, { capture: true });
        });

        this.bind_bar_progress = function() {
            // Do nothing to prevent progress bar resizing
        };

        this.drag_bar = function() { return false; };
        this.resize_bar = function() { return false; };
        this.update_bar_position = function() { return false; };
    };

    var gantt = new Gantt("#gantt-chart", tasks, {
        on_click: function(task) {
            console.log("Clicked task:", task);
            if (typeof showCommentModal === 'function') {
                showCommentModal(task.id, task.name);
            } else {
                console.warn("showCommentModal not defined");
            }
        },
        view_mode: 'Week',
        date_format: 'YYYY-MM-DD',
        custom_popup_html: function(task) {
            const comment = tasks.find(t => t.id === task.id).comment || 'No comment';
            return `${task.name} (Progress: ${task.progress}%)<br>Comment: ${comment}`;
        },
        popup_trigger: 'click',
        on_progress_change: null,
        on_date_change: null,
        on_drag_start: function() { return false; },
        on_resize_start: function() { return false; }
    });

    $('.view-mode').click(function() {
        var mode = $(this).data('mode');
        gantt.change_view_mode(mode);
    });

    setTimeout(() => gantt.refresh(tasks), 100);

    // Expose refresh function globally
    window.refreshGantt = function(newTasks) {
        if (gantt && Array.isArray(newTasks)) {
            gantt.refresh(newTasks);
            console.log("Gantt refreshed with:", newTasks);
        } else {
            console.warn("Gantt or tasks data invalid");
        }
    };

    document.querySelector('.close-button').addEventListener('click', closeCommentModal);
    document.getElementById('saveCommentButton')?.addEventListener('click', function() {
        const taskId = tasks.find(t => t.name === document.getElementById('commentTaskName').textContent).id;
        const comment = document.getElementById('taskCommentTextarea').value;
        $.ajax({
            url: '{{ url_for("main.update_comment", task_id=0) }}'.replace('0', taskId),
            method: 'POST',
            data: { csrf_token: $('meta[name="csrf-token"]').attr('content'), comment: comment },
            success: function(response) {
                if (response.success) {
                    $('#modal-flashes').append('<li class="success">Comment saved!</li>');
                    setTimeout(closeCommentModal, 1000);
                    if (typeof fetchTasks === 'function' && window.projectId) {
                        fetchTasks(window.projectId);
                    }
                } else {
                    $('#modal-flashes').append('<li class="error">Error saving comment.</li>');
                }
            },
            error: function() {
                $('#modal-flashes').append('<li class="error">Network error.</li>');
            }
        });
    });

    function closeCommentModal() {
        document.getElementById('commentModal').style.display = 'none';
    }

    window.addEventListener('resize', () => gantt.refresh(tasks));
});