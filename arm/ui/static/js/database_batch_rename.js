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
    $('#generate-preview-btn').on('click', generatePreview);
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
        // Only allow TV series that are complete
        if (videoType !== 'series') {
            checkbox.prop('checked', false);
            showToast('Only TV series can be batch renamed', 'warning');
            return;
        }
        if (status !== 'success') {
            checkbox.prop('checked', false);
            showToast('Only completed jobs can be batch renamed', 'warning');
            return;
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
        
        if (videoType === 'series' && status === 'success') {
            checkbox.prop('checked', true);
            selectedJobs.add(checkbox.data('job-id'));
        }
    });
    
    updateBatchRenameButton();
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
        showToast('Please select at least one TV series job', 'warning');
        return;
    }
    
    // Reset modal to step 1
    resetModal();
    
    // Show modal
    $('#batchRenameModal').modal('show');
}

function resetModal() {
    // Reset to step 1
    $('#rename-options-step').show();
    $('#rename-preview-step').hide();
    $('#rename-results-step').hide();
    
    // Clear preview data
    previewData = null;
    $('#preview-table-body').empty();
    $('#preview-warnings').hide();
    $('#preview-outliers').hide();
    $('#preview-conflicts').hide();
    
    // Clear results
    $('#results-content').empty();
    $('#rollback-btn').hide();
}

function generatePreview() {
    const btn = $('#generate-preview-btn');
    btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Generating Preview...');
    
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
                displayPreview(response.preview);
                
                // Move to step 2
                $('#rename-options-step').hide();
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
            btn.prop('disabled', false).html('<i class="fa fa-eye"></i> Generate Preview');
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
