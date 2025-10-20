/**
 * Shared Batch Rename Utilities
 * Common functions used by both batch_rename_page.js and database_batch_rename.js
 */

// Shared module namespace
var BatchRenameShared = (function() {
    'use strict';

    /**
     * Escape HTML to prevent XSS attacks
     */
    function escapeHtml(unsafe) {
        if (unsafe == null) return '';
        return String(unsafe)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    /**
     * Load default configuration values for rename options
     */
    function loadDefaultConfig() {
        $('#naming-style').val('underscore');
        $('#zero-padded').prop('checked', false);
        $('#consolidate').prop('checked', false);
        $('#include-year').prop('checked', true);
    }

    /**
     * Display series selection UI for multiple series detection
     */
    function displaySeriesSelection(preview) {
        const seriesInfo = preview.series_info || {};
        const outliers = preview.outliers || [];
        const items = preview.items || preview.previews || [];

        // Build series groups
        const seriesGroups = {};

        // Add primary series
        if (seriesInfo.primary_series) {
            seriesGroups[seriesInfo.primary_series] = {
                name: seriesInfo.primary_series,
                imdb_id: seriesInfo.primary_series_id,
                jobs: []
            };
        }

        // Add outlier series
        outliers.forEach(outlier => {
            const key = outlier.imdb_id || outlier.title;
            if (!seriesGroups[key]) {
                seriesGroups[key] = {
                    name: outlier.title,
                    imdb_id: outlier.imdb_id,
                    jobs: []
                };
            }
        });

        // Assign jobs to series groups
        items.forEach(item => {
            const jobId = item.job_id || item.id;
            const outlier = outliers.find(o => o.job_id === jobId);

            if (outlier) {
                const key = outlier.imdb_id || outlier.title;
                if (seriesGroups[key]) {
                    seriesGroups[key].jobs.push(item);
                }
            } else if (seriesInfo.primary_series && seriesGroups[seriesInfo.primary_series]) {
                seriesGroups[seriesInfo.primary_series].jobs.push(item);
            }
        });

        // Display series groups
        const container = $('#series-groups-container');
        container.empty();

        let groupIndex = 0;
        for (const key in seriesGroups) {
            const group = seriesGroups[key];
            const isChecked = groupIndex === 0 ? 'checked' : '';

            const groupNameEsc = escapeHtml(group.name);
            const groupImdbEsc = group.imdb_id ? '(' + escapeHtml(group.imdb_id) + ')' : '';
            const groupHtml = `
                <div class="form-check mb-3">
                    <input class="form-check-input series-radio" type="radio" name="primarySeries"
                           id="series-${groupIndex}" value="${escapeHtml(key)}" ${isChecked}>
                    <label class="form-check-label" for="series-${groupIndex}">
                        <strong>${groupNameEsc}</strong> ${groupImdbEsc}
                        <span class="badge badge-info">${group.jobs.length} disc(s)</span>
                    </label>
                </div>
            `;
            container.append(groupHtml);
            groupIndex++;
        }

        // Display disc assignment table
        displayDiscAssignment(items, outliers, seriesInfo);

        // Update disc assignment when series selection changes
        $('.series-radio').on('change', function() {
            displayDiscAssignment(items, outliers, seriesInfo);
        });
    }

    /**
     * Display disc assignment table for outlier resolution
     */
    function displayDiscAssignment(items, outliers, seriesInfo) {
        const container = $('#disc-assignment-container');
        container.empty();

        const selectedSeries = $('input[name="primarySeries"]:checked').val();

        let tableHtml = `
            <table class="table table-sm table-bordered">
                <thead>
                    <tr>
                        <th>Job ID</th>
                        <th>Title</th>
                        <th>Label</th>
                        <th>Assignment</th>
                    </tr>
                </thead>
                <tbody>
        `;

        items.forEach(item => {
            const jobId = item.job_id || item.id;
            const titleRaw = item.title || item.series_name || 'N/A';
            const labelRaw = item.label || item.disc_label || 'N/A';
            const outlier = outliers.find(o => o.job_id === jobId);

            let assignmentHtml = '';
            if (outlier) {
                const escapedSeries = escapeHtml(selectedSeries);
                assignmentHtml = `
                    <select class="form-control form-control-sm disc-assignment" data-job-id="${escapeHtml(jobId)}">
                        <option value="skip">Skip this disc</option>
                        <option value="force">Include in ${escapedSeries}</option>
                        <option value="auto" selected>Auto (different series)</option>
                    </select>
                `;
            } else {
                const escapedSeries = escapeHtml(selectedSeries);
                assignmentHtml = `<span class="badge badge-success">Part of ${escapedSeries}</span>`;
            }

            tableHtml += `
                <tr>
                    <td>${jobId}</td>
                    <td>${escapeHtml(titleRaw)}</td>
                    <td>${escapeHtml(labelRaw)}</td>
                    <td>${assignmentHtml}</td>
                </tr>
            `;
        });

        tableHtml += '</tbody></table>';
        container.html(tableHtml);
    }

    /**
     * Display preview of rename operations
     */
    function displayPreview(preview) {
        const tbody = $('#preview-table-body');
        tbody.empty();

        // Display warnings
        if (preview.warnings && preview.warnings.length > 0) {
            const warningDiv = $('#preview-warnings');
            warningDiv.html('<strong>Warnings:</strong><ul>' +
                preview.warnings.map(w => '<li>' + escapeHtml(w) + '</li>').join('') +
                '</ul>');
            warningDiv.show();
        }

        // Display outliers
        if (preview.outliers && preview.outliers.length > 0) {
            const outlierDiv = $('#preview-outliers');
            let outlierHtml = '<strong>Series Outliers Detected:</strong><br>';
            outlierHtml += '<small>The following jobs have different series identifiers:</small><ul>';
            preview.outliers.forEach(outlier => {
                outlierHtml += `<li>Job ${escapeHtml(outlier.job_id.toString())}: ${escapeHtml(outlier.title)} (IMDb: ${escapeHtml(outlier.imdb_id || 'N/A')})</li>`;
            });
            outlierHtml += '</ul>';
            outlierHtml += '<small>These will be skipped unless you override series detection.</small>';
            outlierDiv.html(outlierHtml);
            outlierDiv.show();
        }

        // Display conflicts
        if (preview.conflicts && preview.conflicts.length > 0) {
            const conflictDiv = $('#preview-conflicts');
            let conflictHtml = '<strong>Path Conflicts Detected:</strong><ul>';
            preview.conflicts.forEach(conflict => {
                if (typeof conflict === 'string') {
                    conflictHtml += `<li>${escapeHtml(conflict)}</li>`;
                } else {
                    conflictHtml += `<li>Job ${escapeHtml(conflict.job_id.toString())}: ${escapeHtml(conflict.reason)}</li>`;
                }
            });
            conflictHtml += '</ul>';

            // Different handling based on page context
            if ($('#execute-rename-btn').length) {
                // batch_rename_page.js - conflicts resolved with timestamps
                conflictHtml += '<strong>Conflicts will be resolved with timestamps during execution.</strong>';
                conflictDiv.html(conflictHtml);
                conflictDiv.show();
            } else {
                // database_batch_rename.js - conflicts block execution
                conflictHtml += '<strong>Cannot proceed with rename until conflicts are resolved.</strong>';
                conflictDiv.html(conflictHtml);
                conflictDiv.show();
                $('#execute-rename-btn').prop('disabled', true);
            }
        } else {
            const executeBtn = $('#execute-rename-btn');
            if (executeBtn.length) {
                executeBtn.prop('disabled', false);
            }
        }

        // Display preview table
        const items = preview.items || preview.previews || [];

        // Build quick lookup for conflicts by job_id or new_path
        const conflictByJob = {};
        if (preview.conflicts && preview.conflicts.length) {
            preview.conflicts.forEach(c => {
                if (typeof c === 'string') {
                    return;
                }
                if (c.job_id) {
                    conflictByJob[c.job_id] = c;
                } else if (c.new_path) {
                    conflictByJob[c.new_path] = c;
                }
            });
        }

        items.forEach(item => {
            let statusBadge = '';
            let statusClass = '';

            // Normalize fields across merged versions
            const jobId = item.job_id || item.jobId || item.id;
            const title = item.title || item.series_name || 'N/A';
            const discLabel = item.label || item.disc_label || item.discLabel || 'N/A';
            const oldPath = item.old_path || item.oldPath || item.oldPathname || '';
            const newPath = item.new_path || item.newPath || item.target_path || '';

            // Determine status
            if (item.status === 'skipped' || item.fallback) {
                statusBadge = '<span class="badge badge-secondary">Skipped/Fallback</span>';
                statusClass = 'table-secondary';
            } else if (item.status === 'conflict' || conflictByJob[jobId] || conflictByJob[newPath]) {
                // Check if conflicts are automatically resolved
                if ($('#execute-rename-btn').data('auto-resolve-conflicts')) {
                    statusBadge = '<span class="badge badge-warning">Conflict (will add timestamp)</span>';
                    statusClass = 'table-warning';
                } else {
                    statusBadge = '<span class="badge badge-danger">Conflict</span>';
                    statusClass = 'table-danger';
                }
            } else {
                statusBadge = '<span class="badge badge-success">Ready</span>';
                statusClass = '';
            }

            const row = `
                <tr class="${statusClass}">
                    <td>${escapeHtml(jobId.toString())}</td>
                    <td>${escapeHtml(title)}</td>
                    <td>${escapeHtml(discLabel)}</td>
                    <td><small><code>${escapeHtml(oldPath)}</code></small></td>
                    <td><small><code>${escapeHtml(newPath)}</code></small></td>
                    <td>${statusBadge}</td>
                </tr>
            `;
            tbody.append(row);
        });
    }

    /**
     * Display results of rename operation
     */
    function displayResults(response) {
        const resultsDiv = $('#results-content');
        resultsDiv.empty();

        let html = '';

        if (response.success) {
            html += '<div class="alert alert-success">';
            html += '<h6><i class="fa fa-check-circle"></i> Batch Rename Successful</h6>';
            html += `<p>Batch ID: <code>${escapeHtml(response.batch_id)}</code></p>`;
            html += `<p>Renamed ${escapeHtml(response.renamed_count.toString())} folders</p>`;

            if (response.skipped && response.skipped.length > 0) {
                html += '<p><strong>Skipped jobs:</strong></p><ul>';
                response.skipped.forEach(skip => {
                    html += `<li>Job ${skip.job_id}: ${skip.reason}</li>`;
                });
                html += '</ul>';
            }

            html += '</div>';

            // Show rollback button
            $('#rollback-btn').show();
        } else {
            html += '<div class="alert alert-danger">';
            html += '<h6><i class="fa fa-exclamation-circle"></i> Batch Rename Failed</h6>';
            html += `<p>${escapeHtml(response.message)}</p>`;

            if (response.errors && response.errors.length > 0) {
                html += '<p><strong>Errors:</strong></p><ul>';
                response.errors.forEach(error => {
                    html += `<li>${escapeHtml(error)}</li>`;
                });
                html += '</ul>';
            }

            html += '</div>';

            // Show rollback button if partial success
            if (response.batch_id) {
                $('#rollback-btn').show();
            }
        }

        resultsDiv.html(html);
    }

    /**
     * Navigate back to options step from series selection
     */
    function backToOptionsFromSeries() {
        $('#rename-series-selection-step').hide();
        $('#rename-options-step').show();
    }

    /**
     * Navigate back to options step from preview
     */
    function backToOptions() {
        $('#rename-preview-step').hide();
        $('#rename-options-step').show();
    }

    /**
     * Display toast notification
     */
    function showToast(message, type) {
        const escapedMessage = escapeHtml(message);
        const toast = $(`
            <div class="alert alert-${type} alert-dismissible fade show" role="alert"
                 style="position: fixed; top: 80px; right: 20px; z-index: 9999; min-width: 300px; max-width: 500px;">
                ${escapedMessage}
                <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
        `);

        $('body').append(toast);

        // Auto-dismiss after 5 seconds
        setTimeout(function() {
            toast.alert('close');
        }, 5000);
    }

    /**
     * Perform AJAX request to detect series and generate preview
     */
    function detectSeries(selectedJobs, callback) {
        const btn = $('#generate-preview-btn');
        btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Detecting Series...');

        const options = {
            job_ids: Array.from(selectedJobs),
            naming_style: $('#naming-style').val(),
            zero_padded: $('#zero-padded').is(':checked'),
            consolidate: $('#consolidate').is(':checked'),
            include_year: $('#include-year').is(':checked')
        };

        $.ajax({
            url: '/batch_rename',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                action: 'preview',
                ...options
            }),
            success: function(response) {
                if (response.success) {
                    callback(response.preview);
                } else {
                    showToast('Series detection failed: ' + response.message, 'danger');
                }
            },
            error: function(xhr) {
                let msg = 'Failed to detect series';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    msg += ': ' + xhr.responseJSON.message;
                }
                showToast(msg, 'danger');
            },
            complete: function() {
                btn.prop('disabled', false).html('<i class="fa fa-eye"></i> Generate Preview');
            }
        });
    }

    /**
     * Generate preview with series resolution
     */
    function generatePreviewWithSeries(selectedJobs, callback) {
        const btn = $('#confirm-series-btn');
        btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Generating Preview...');

        // Collect outlier resolution
        const outlierResolution = {};
        $('.disc-assignment').each(function() {
            const jobId = $(this).data('job-id');
            const resolution = $(this).val();
            outlierResolution[jobId] = resolution;
        });

        const options = {
            job_ids: Array.from(selectedJobs),
            naming_style: $('#naming-style').val(),
            zero_padded: $('#zero-padded').is(':checked'),
            consolidate: $('#consolidate').is(':checked'),
            include_year: $('#include-year').is(':checked'),
            outlier_resolution: outlierResolution
        };

        $.ajax({
            url: '/batch_rename',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                action: 'preview',
                ...options
            }),
            success: function(response) {
                if (response.success) {
                    callback(response.preview);
                } else {
                    showToast('Preview failed: ' + response.message, 'danger');
                }
            },
            error: function(xhr) {
                let msg = 'Failed to generate preview';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    msg += ': ' + xhr.responseJSON.message;
                }
                showToast(msg, 'danger');
            },
            complete: function() {
                btn.prop('disabled', false).html('<i class="fa fa-check"></i> Confirm and Preview');
            }
        });
    }

    /**
     * Execute batch rename operation
     */
    function executeRename(selectedJobs, callback) {
        const btn = $('#execute-rename-btn');
        btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Executing...');

        const options = {
            job_ids: Array.from(selectedJobs),
            naming_style: $('#naming-style').val(),
            zero_padded: $('#zero-padded').is(':checked'),
            consolidate: $('#consolidate').is(':checked'),
            include_year: $('#include-year').is(':checked')
        };

        // Include outlier resolution if it exists
        const outlierResolution = {};
        $('.disc-assignment').each(function() {
            const jobId = $(this).data('job-id');
            const resolution = $(this).val();
            outlierResolution[jobId] = resolution;
        });

        if (Object.keys(outlierResolution).length > 0) {
            options.outlier_resolution = outlierResolution;
        }

        $.ajax({
            url: '/batch_rename',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                action: 'execute',
                ...options
            }),
            success: function(response) {
                callback(response);
            },
            error: function(xhr) {
                let msg = 'Failed to execute rename';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    msg += ': ' + xhr.responseJSON.message;
                }
                showToast(msg, 'danger');
                btn.prop('disabled', false).html('<i class="fa fa-check"></i> Execute Batch Rename');
            },
            complete: function() {
                if (btn.prop('disabled')) {
                    btn.prop('disabled', false).html('<i class="fa fa-check"></i> Execute Batch Rename');
                }
            }
        });
    }

    /**
     * Rollback batch rename operation
     */
    function rollbackRename(batchId, callback) {
        if (!batchId) {
            showToast('No batch ID available for rollback', 'danger');
            return;
        }

        if (!confirm('Are you sure you want to rollback this batch rename operation? This will restore the original folder names.')) {
            return;
        }

        const btn = $('#rollback-btn');
        btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Rolling back...');

        $.ajax({
            url: '/batch_rename',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                action: 'rollback',
                batch_id: batchId
            }),
            success: function(response) {
                if (response.success) {
                    showToast('Rollback successful: ' + response.rolled_back_count + ' folders restored', 'success');
                    callback(response);
                } else {
                    showToast('Rollback failed: ' + response.message, 'danger');
                }
            },
            error: function(xhr) {
                let msg = 'Failed to rollback';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    msg += ': ' + xhr.responseJSON.message;
                }
                showToast(msg, 'danger');
            },
            complete: function() {
                btn.prop('disabled', false).html('<i class="fa fa-undo"></i> Rollback This Operation');
            }
        });
    }

    // Public API
    return {
        loadDefaultConfig: loadDefaultConfig,
        displaySeriesSelection: displaySeriesSelection,
        displayDiscAssignment: displayDiscAssignment,
        displayPreview: displayPreview,
        displayResults: displayResults,
        backToOptionsFromSeries: backToOptionsFromSeries,
        backToOptions: backToOptions,
        showToast: showToast,
        detectSeries: detectSeries,
        generatePreviewWithSeries: generatePreviewWithSeries,
        executeRename: executeRename,
        rollbackRename: rollbackRename
    };
})();
