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
        const seriesGroups = seriesInfo.series_groups || [];

        // Display series groups with custom lookup badges
        const container = $('#series-groups-container');
        container.empty();

        if (seriesGroups.length === 0) {
            container.html('<p class="text-muted">No series information available.</p>');
            return;
        }

        let groupIndex = 0;
        seriesGroups.forEach(group => {
            const isChecked = groupIndex === 0 ? 'checked' : '';
            const groupNameEsc = escapeHtml(group.display_name);
            const groupImdbEsc = group.imdb_id ? ' (' + escapeHtml(group.imdb_id) + ')' : '';
            
            // Badge for custom lookup
            const customBadge = group.has_manual_title ? 
                '<span class="badge badge-success ml-2">Custom Lookup</span>' : '';
            
            const groupHtml = `
                <div class="form-check mb-3">
                    <input class="form-check-input series-radio" type="radio" name="primarySeries"
                           id="series-${groupIndex}" value="${escapeHtml(group.key)}" 
                           data-series-name="${escapeHtml(group.display_name)}"
                           ${isChecked}>
                    <label class="form-check-label" for="series-${groupIndex}">
                        <strong>${groupNameEsc}</strong>${groupImdbEsc}
                        <span class="badge badge-info ml-2">${group.job_count} disc(s)</span>
                        ${customBadge}
                    </label>
                </div>
            `;
            container.append(groupHtml);
            groupIndex++;
        });

        // Display warning message
        const warningContainer = $('#series-selection-warning');
        if (warningContainer.length) {
            const selectedRadio = $('input[name="primarySeries"]:checked');
            const selectedName = selectedRadio.data('series-name') || 'this series';
            warningContainer.html(
                `<strong><i class="fa fa-exclamation-triangle"></i> Warning:</strong> ` +
                `All selected discs will be renamed using "<strong>${escapeHtml(selectedName)}</strong>" as the series name. ` +
                `This will affect ${seriesGroups.reduce((sum, g) => sum + g.job_count, 0)} disc(s).`
            );
        }

        // Update warning when selection changes
        $('.series-radio').on('change', function() {
            const selectedName = $(this).data('series-name') || 'this series';
            const warningContainer = $('#series-selection-warning');
            if (warningContainer.length) {
                warningContainer.html(
                    `<strong><i class="fa fa-exclamation-triangle"></i> Warning:</strong> ` +
                    `All selected discs will be renamed using "<strong>${escapeHtml(selectedName)}</strong>" as the series name. ` +
                    `This will affect ${seriesGroups.reduce((sum, g) => sum + g.job_count, 0)} disc(s).`
                );
            }
        });
    }

    /**
     * Display disc assignment table - simplified version
     */
    function displayDiscAssignment(items, outliers, seriesInfo) {
        // This function is kept for compatibility but simplified
        // The new series selection UI handles this differently
        const container = $('#disc-assignment-container');
        container.empty();
        
        // Show a simple message
        container.html(
            '<p class="text-muted small">Note: All discs will use the selected series name above.</p>'
        );
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
                // API returns preview object directly, not wrapped in {success, preview}
                if (response && (response.success === false || response.error)) {
                    // Explicit error response
                    const errorMsg = response.error || response.message || 'Unknown error';
                    showToast('Series detection failed: ' + errorMsg, 'danger');
                } else if (response && (response.items || response.previews || response.series_info)) {
                    // Valid preview response
                    callback(response);
                } else {
                    showToast('Series detection failed: Invalid response', 'danger');
                }
            },
            error: function(xhr) {
                let msg = 'Failed to detect series';
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    msg += ': ' + xhr.responseJSON.error;
                } else if (xhr.responseJSON && xhr.responseJSON.message) {
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

        // Get selected series key
        const selectedSeriesKey = $('input[name="primarySeries"]:checked').val();
        
        if (!selectedSeriesKey) {
            showToast('Please select a series before continuing', 'warning');
            btn.prop('disabled', false).html('<i class="fa fa-check"></i> Confirm and Preview');
            return;
        }

        // Mark all jobs as using the selected series (force override)
        const outlierResolution = {};
        $('input[name="primarySeries"]').each(function() {
            const radioKey = $(this).val();
            if (radioKey !== selectedSeriesKey) {
                // All jobs from non-selected series should use selected series
                const seriesInfo = $(this).closest('.form-check').data('series-info') || {};
                // This will be handled by backend based on selected_series_key
            }
        });

        const options = {
            job_ids: Array.from(selectedJobs),
            naming_style: $('#naming-style').val(),
            zero_padded: $('#zero-padded').is(':checked'),
            consolidate: $('#consolidate').is(':checked'),
            include_year: $('#include-year').is(':checked'),
            selected_series_key: selectedSeriesKey,
            force_series_override: true  // Force all jobs to use selected series
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
                // API returns preview object directly, not wrapped in {success, preview}
                if (response && (response.success === false || response.error)) {
                    // Explicit error response
                    const errorMsg = response.error || response.message || 'Unknown error';
                    showToast('Preview failed: ' + errorMsg, 'danger');
                } else if (response && (response.items || response.previews || response.series_info)) {
                    // Valid preview response
                    callback(response);
                } else {
                    showToast('Preview failed: Invalid response', 'danger');
                }
            },
            error: function(xhr) {
                let msg = 'Failed to generate preview';
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    msg += ': ' + xhr.responseJSON.error;
                } else if (xhr.responseJSON && xhr.responseJSON.message) {
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
