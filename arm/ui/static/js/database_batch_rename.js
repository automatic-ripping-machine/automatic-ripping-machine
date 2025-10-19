/**
 * Batch Rename functionality for Database View
 * Handles multi-select, preview, execution, and rollback of TV series disc renames
 */

let selectedJobs = new Set();
let currentBatchId = null;
let previewData = null;

$(document).ready(function() {
    initializeBatchRename();
});

function initializeBatchRename() {
    // Checkbox selection handlers
    $('.job-select-checkbox').on('change', handleCheckboxChange);
    $('#select-all-btn').on('click', selectAllJobs);
    $('#deselect-all-btn').on('click', deselectAllJobs);
    
    // Batch rename button
    $('#batch-rename-btn').on('click', openBatchRenameModal);
    
    // Modal handlers
    $('#generate-preview-btn').on('click', detectSeries);
    $('#back-from-series-btn').on('click', backToOptionsFromSeries);
    $('#confirm-series-btn').on('click', generatePreviewWithSeries);
    $('#back-to-options-btn').on('click', backToOptions);
    $('#execute-rename-btn').on('click', executeRename);
    $('#rollback-btn').on('click', rollbackRename);
    
    // Modal reset on close
    $('#batchRenameModal').on('hidden.bs.modal', resetModal);
    
    // Load default config values
    loadDefaultConfig();
}

function handleCheckboxChange() {
    const checkbox = $(this);
    const jobId = checkbox.data('job-id');
    const videoType = checkbox.data('video-type');
    const status = checkbox.data('status');
    
    if (checkbox.is(':checked')) {
        // Only allow completed jobs
        if (status !== 'success') {
            checkbox.prop('checked', false);
            showToast('Only completed jobs can be batch renamed', 'warning');
            return;
        }
        
        // Warn about non-series items but allow them
        if (videoType !== 'series') {
            showToast('Warning: Job ' + jobId + ' is not marked as a TV series. It may not rename correctly.', 'info');
        }
        
        selectedJobs.add(jobId);
    } else {
        selectedJobs.delete(jobId);
    }
    
    updateBatchRenameButton();
}

function selectAllJobs() {
    $('.job-select-checkbox').each(function() {
        const checkbox = $(this);
        const videoType = checkbox.data('video-type');
        const status = checkbox.data('status');
        
        // Select all completed jobs (prefer series but allow others)
        if (status === 'success') {
            checkbox.prop('checked', true);
            selectedJobs.add(checkbox.data('job-id'));
        }
    });
    
    updateBatchRenameButton();
    
    // Warn if non-series items selected
    let nonSeriesCount = 0;
    $('.job-select-checkbox:checked').each(function() {
        if ($(this).data('video-type') !== 'series') {
            nonSeriesCount++;
        }
    });
    
    if (nonSeriesCount > 0) {
        showToast(`Warning: ${nonSeriesCount} non-series items selected. They may not rename correctly.`, 'info');
    }
}

function deselectAllJobs() {
    $('.job-select-checkbox').prop('checked', false);
    selectedJobs.clear();
    updateBatchRenameButton();
}

function updateBatchRenameButton() {
    const btn = $('#batch-rename-btn');
    if (selectedJobs.size > 0) {
        btn.prop('disabled', false);
        btn.html(`<i class="fa fa-edit"></i> Batch Rename Selected (${selectedJobs.size})`);
    } else {
        btn.prop('disabled', true);
        btn.html('<i class="fa fa-edit"></i> Batch Rename Selected');
    }
}

function loadDefaultConfig() {
    // Load default values from ARM config if available
    // For now, using hardcoded defaults matching arm.yaml
    $('#naming-style').val('underscore');
    $('#zero-padded').prop('checked', false);
    $('#consolidate').prop('checked', false);
    $('#include-year').prop('checked', true);
}

function openBatchRenameModal() {
    if (selectedJobs.size === 0) {
        showToast('Please select at least one completed job', 'warning');
        return;
    }
    
    // Check for non-series items and show warning
    let nonSeriesCount = 0;
    let nonSeriesJobs = [];
    
    $('.job-select-checkbox:checked').each(function() {
        const videoType = $(this).data('video-type');
        if (videoType !== 'series') {
            nonSeriesCount++;
            nonSeriesJobs.push({
                id: $(this).data('job-id'),
                type: videoType
            });
        }
    });
    
    if (nonSeriesCount > 0) {
        const msg = `You have selected ${nonSeriesCount} non-TV series item(s). ` +
                    `Batch rename is optimized for TV series with disc labels. ` +
                    `These items may not rename correctly. Continue anyway?`;
        
        if (!confirm(msg)) {
            return;
        }
    }
    
    // Reset modal to step 1
    resetModal();
    
    // Show modal
    $('#batchRenameModal').modal('show');
}

function resetModal() {
    // Reset to step 1
    $('#rename-options-step').show();
    $('#rename-series-selection-step').hide();
    $('#rename-preview-step').hide();
    $('#rename-results-step').hide();
    
    // Clear preview data
    previewData = null;
    $('#preview-table-body').empty();
    $('#preview-warnings').hide();
    $('#preview-outliers').hide();
    $('#preview-conflicts').hide();
    
    // Clear series selection
    $('#series-groups-container').empty();
    $('#disc-assignment-container').empty();
    
    // Clear results
    $('#results-content').empty();
    $('#rollback-btn').hide();
}

function detectSeries() {
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
                previewData = response.preview;
                
                // Check if we need series selection step
                const seriesInfo = response.preview.series_info || {};
                const hasMultipleSeries = !seriesInfo.consistent || (response.preview.outliers && response.preview.outliers.length > 0);
                
                if (hasMultipleSeries) {
                    // Show series selection step
                    displaySeriesSelection(response.preview);
                    $('#rename-options-step').hide();
                    $('#rename-series-selection-step').show();
                } else {
                    // Skip series selection, go straight to preview
                    displayPreview(response.preview);
                    $('#rename-options-step').hide();
                    $('#rename-preview-step').show();
                }
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
        
        const groupHtml = `
            <div class="form-check mb-3">
                <input class="form-check-input series-radio" type="radio" name="primarySeries" 
                       id="series-${groupIndex}" value="${key}" ${isChecked}>
                <label class="form-check-label" for="series-${groupIndex}">
                    <strong>${group.name}</strong> ${group.imdb_id ? '(IMDb: ' + group.imdb_id + ')' : ''}
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
        const title = item.title || item.series_name || 'N/A';
        const label = item.label || item.disc_label || 'N/A';
        const outlier = outliers.find(o => o.job_id === jobId);
        
        let assignmentHtml = '';
        if (outlier) {
            assignmentHtml = `
                <select class="form-control form-control-sm disc-assignment" data-job-id="${jobId}">
                    <option value="skip">Skip this disc</option>
                    <option value="force">Include in ${selectedSeries}</option>
                    <option value="auto" selected>Auto (different series)</option>
                </select>
            `;
        } else {
            assignmentHtml = `<span class="badge badge-success">Part of ${selectedSeries}</span>`;
        }
        
        tableHtml += `
            <tr>
                <td>${jobId}</td>
                <td>${title}</td>
                <td>${label}</td>
                <td>${assignmentHtml}</td>
            </tr>
        `;
    });
    
    tableHtml += '</tbody></table>';
    container.html(tableHtml);
}

function backToOptionsFromSeries() {
    $('#rename-series-selection-step').hide();
    $('#rename-options-step').show();
}

function generatePreviewWithSeries() {
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
                previewData = response.preview;
                displayPreview(response.preview);
                
                // Move to preview step
                $('#rename-series-selection-step').hide();
                $('#rename-preview-step').show();
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

function displayPreview(preview) {
    const tbody = $('#preview-table-body');
    tbody.empty();
    
    // Display warnings
    if (preview.warnings && preview.warnings.length > 0) {
        const warningDiv = $('#preview-warnings');
        warningDiv.html('<strong>Warnings:</strong><ul>' + 
            preview.warnings.map(w => '<li>' + w + '</li>').join('') + 
            '</ul>');
        warningDiv.show();
    }
    
    // Display outliers
    if (preview.outliers && preview.outliers.length > 0) {
        const outlierDiv = $('#preview-outliers');
        let outlierHtml = '<strong>Series Outliers Detected:</strong><br>';
        outlierHtml += '<small>The following jobs have different series identifiers:</small><ul>';
        preview.outliers.forEach(outlier => {
            outlierHtml += `<li>Job ${outlier.job_id}: ${outlier.title} (IMDb: ${outlier.imdb_id || 'N/A'})</li>`;
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
            conflictHtml += `<li>${conflict}</li>`;
        });
        conflictHtml += '</ul>';
        conflictHtml += '<strong>Cannot proceed with rename until conflicts are resolved.</strong>';
        conflictDiv.html(conflictHtml);
        conflictDiv.show();
        
        // Disable execute button
        $('#execute-rename-btn').prop('disabled', true);
    } else {
        $('#execute-rename-btn').prop('disabled', false);
    }
    
    // Display preview table
    preview.previews.forEach(item => {
        let statusBadge = '';
        let statusClass = '';
        
        if (item.status === 'skipped') {
            statusBadge = '<span class="badge badge-secondary">Skipped</span>';
            statusClass = 'table-secondary';
        } else if (item.status === 'conflict') {
            statusBadge = '<span class="badge badge-danger">Conflict</span>';
            statusClass = 'table-danger';
        } else if (item.status === 'ok') {
            statusBadge = '<span class="badge badge-success">Ready</span>';
            statusClass = '';
        }
        
        const row = `
            <tr class="${statusClass}">
                <td>${item.job_id}</td>
                <td>${item.title || 'N/A'}</td>
                <td>${item.disc_label || 'N/A'}</td>
                <td><small><code>${item.old_path}</code></small></td>
                <td><small><code>${item.new_path}</code></small></td>
                <td>${statusBadge}</td>
            </tr>
        `;
        tbody.append(row);
    });
}

function backToOptions() {
    $('#rename-preview-step').hide();
    $('#rename-options-step').show();
}

function executeRename() {
    if (!previewData) {
        showToast('Please generate preview first', 'warning');
        return;
    }
    
    // Check for conflicts
    if (previewData.conflicts && previewData.conflicts.length > 0) {
        showToast('Cannot execute: conflicts detected', 'danger');
        return;
    }
    
    const btn = $('#execute-rename-btn');
    btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Executing...');
    
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
            action: 'execute',
            ...options
        }),
        success: function(response) {
            if (response.success) {
                currentBatchId = response.batch_id;
                displayResults(response);
                
                // Move to step 3
                $('#rename-preview-step').hide();
                $('#rename-results-step').show();
                
                // Clear selection and refresh page after a delay
                setTimeout(function() {
                    deselectAllJobs();
                }, 2000);
            } else {
                showToast('Execution failed: ' + response.message, 'danger');
                if (response.batch_id) {
                    currentBatchId = response.batch_id;
                }
            }
        },
        error: function(xhr) {
            let msg = 'Failed to execute rename';
            if (xhr.responseJSON && xhr.responseJSON.message) {
                msg += ': ' + xhr.responseJSON.message;
            }
            showToast(msg, 'danger');
        },
        complete: function() {
            btn.prop('disabled', false).html('<i class="fa fa-check"></i> Execute Batch Rename');
        }
    });
}

function displayResults(response) {
    const resultsDiv = $('#results-content');
    resultsDiv.empty();
    
    let html = '';
    
    if (response.success) {
        html += '<div class="alert alert-success">';
        html += '<h6><i class="fa fa-check-circle"></i> Batch Rename Successful</h6>';
        html += `<p>Batch ID: <code>${response.batch_id}</code></p>`;
        html += `<p>Renamed ${response.renamed_count} folders</p>`;
        
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
        html += `<p>${response.message}</p>`;
        
        if (response.errors && response.errors.length > 0) {
            html += '<p><strong>Errors:</strong></p><ul>';
            response.errors.forEach(error => {
                html += `<li>${error}</li>`;
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

function rollbackRename() {
    if (!currentBatchId) {
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
            batch_id: currentBatchId
        }),
        success: function(response) {
            if (response.success) {
                showToast('Rollback successful: ' + response.rolled_back_count + ' folders restored', 'success');
                $('#batchRenameModal').modal('hide');
                
                // Refresh page to show updated folders
                setTimeout(function() {
                    location.reload();
                }, 1500);
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

function showToast(message, type) {
    // Create toast notification
    const toast = $(`
        <div class="alert alert-${type} alert-dismissible fade show" role="alert" style="position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
            ${message}
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
