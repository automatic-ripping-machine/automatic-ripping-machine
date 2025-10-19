/**
 * Batch Rename Page functionality
 * Handles multi-select grid view, confirmation, preview, execution, and rollback
 */

let selectedJobs = new Set();
let currentBatchId = null;
let previewData = null;
let hasNonSeries = false;

$(document).ready(function() {
    // Setup CSRF token for AJAX requests
    const csrfToken = $('meta[name="csrf-token"]').attr('content');
    if (csrfToken) {
        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", csrfToken);
                }
            }
        });
    }
    
    initializeBatchRenamePage();
});

function initializeBatchRenamePage() {
    // Table and checkbox handlers
    $('.batch-checkbox').on('change', handleCheckboxChange);
    $('.batch-table-row').on('click', handleRowClick);
    $('#select-all-btn').on('click', selectAllJobs);
    $('#select-all-checkbox').on('change', handleSelectAllCheckbox);
    $('#deselect-all-btn').on('click', deselectAllJobs);
    $('#filter-series-btn').on('click', toggleSeriesFilter);
    
    // Batch rename button
    $('#batch-rename-btn').on('click', openBatchRenameModal);
    
    // Modal step handlers
    $('#confirm-continue-btn').on('click', proceedToOptions);
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

function handleRowClick(e) {
    // Don't toggle if clicking checkbox directly or action buttons
    if ($(e.target).hasClass('batch-checkbox') || 
        $(e.target).closest('a').length > 0 ||
        $(e.target).is('input[type="checkbox"]')) {
        return;
    }
    
    const row = $(this);
    const checkbox = row.find('.batch-checkbox');
    checkbox.prop('checked', !checkbox.prop('checked')).trigger('change');
}

function handleCheckboxChange() {
    const checkbox = $(this);
    const row = checkbox.closest('.batch-table-row');
    const jobId = checkbox.data('job-id');
    const videoType = checkbox.data('video-type');
    
    if (checkbox.is(':checked')) {
        selectedJobs.add(jobId);
        row.addClass('selected');
    } else {
        selectedJobs.delete(jobId);
        row.removeClass('selected');
    }
    
    updateSelectionUI();
    updateSelectAllCheckbox();
}

function handleSelectAllCheckbox() {
    const checkbox = $(this);
    if (checkbox.is(':checked')) {
        selectAllJobs();
    } else {
        deselectAllJobs();
    }
}

function updateSelectAllCheckbox() {
    const totalRows = $('.job-table-row:visible').length;
    const checkedRows = $('.job-table-row:visible').find('.batch-checkbox:checked').length;
    
    const selectAllCheckbox = $('#select-all-checkbox');
    if (checkedRows === 0) {
        selectAllCheckbox.prop('checked', false);
        selectAllCheckbox.prop('indeterminate', false);
    } else if (checkedRows === totalRows) {
        selectAllCheckbox.prop('checked', true);
        selectAllCheckbox.prop('indeterminate', false);
    } else {
        selectAllCheckbox.prop('checked', false);
        selectAllCheckbox.prop('indeterminate', true);
    }
}

function selectAllJobs() {
    const filterActive = $('#filter-series-btn').hasClass('active');
    
    $('.job-table-row:visible').each(function() {
        const row = $(this);
        const videoType = row.data('video-type');
        
        // If filter active, only select series
        if (filterActive && videoType !== 'series') {
            return;
        }
        
        const checkbox = row.find('.batch-checkbox');
        checkbox.prop('checked', true);
        row.addClass('selected');
        selectedJobs.add(checkbox.data('job-id'));
    });
    
    updateSelectionUI();
    updateSelectAllCheckbox();
}

function deselectAllJobs() {
    $('.batch-checkbox').not('#select-all-checkbox').prop('checked', false);
    $('.batch-table-row').removeClass('selected');
    selectedJobs.clear();
    updateSelectionUI();
    updateSelectAllCheckbox();
}

function toggleSeriesFilter() {
    const btn = $('#filter-series-btn');
    btn.toggleClass('active');
    
    if (btn.hasClass('active')) {
        // Hide non-series rows
        $('.job-table-row').each(function() {
            if ($(this).data('video-type') !== 'series') {
                $(this).hide();
            }
        });
        btn.html('<i class="fa fa-filter"></i> Show All');
    } else {
        // Show all rows
        $('.job-table-row').show();
        btn.html('<i class="fa fa-filter"></i> TV Series Only');
    }
    
    updateSelectAllCheckbox();
}

function updateSelectionUI() {
    const count = selectedJobs.size;
    $('#selection-count').text(count);
    
    // Update Batch Rename button
    const renameBtn = $('#batch-rename-btn');
    if (count > 0) {
        renameBtn.prop('disabled', false);
        renameBtn.html(`<i class="fa fa-edit"></i> Batch Rename Selected (${count})`);
    } else {
        renameBtn.prop('disabled', true);
        renameBtn.html('<i class="fa fa-edit"></i> Batch Rename Selected');
    }
    
    // Update Custom Lookup button
    const lookupBtn = $('#custom-lookup-btn');
    if (count > 0) {
        lookupBtn.prop('disabled', false);
        lookupBtn.html(`<i class="fa fa-search"></i> Lookup by Custom Name (${count})`);
    } else {
        lookupBtn.prop('disabled', true);
        lookupBtn.html('<i class="fa fa-search"></i> Lookup by Custom Name');
    }
}

function loadDefaultConfig() {
    $('#naming-style').val('underscore');
    $('#zero-padded').prop('checked', false);
    $('#consolidate').prop('checked', false);
    $('#include-year').prop('checked', true);
}

function openBatchRenameModal() {
    if (selectedJobs.size === 0) {
        showToast('Please select at least one completed disc', 'warning');
        return;
    }
    
    // Check for non-series items
    hasNonSeries = false;
    let nonSeriesJobs = [];
    
    selectedJobs.forEach(jobId => {
        const checkbox = $(`.batch-checkbox[data-job-id="${jobId}"]`);
        const videoType = checkbox.data('video-type');
        const row = checkbox.closest('.job-table-row');
        const title = row.find('.title-cell').attr('title') || row.find('.title-cell').text().trim();
        
        if (videoType !== 'series') {
            hasNonSeries = true;
            nonSeriesJobs.push({
                id: jobId,
                type: videoType,
                title: title
            });
        }
    });
    
    // Reset modal and show appropriate first step
    resetModal();
    
    if (hasNonSeries) {
        // Show confirmation step with details
        displayNonSeriesWarning(nonSeriesJobs);
        $('#rename-confirmation-step').show();
    } else {
        // Skip confirmation, go straight to options
        $('#rename-confirmation-step').hide();
        $('#rename-options-step').show();
    }
    
    $('#batchRenameModal').modal('show');
}

function displayNonSeriesWarning(nonSeriesJobs) {
    $('#non-series-count').text(nonSeriesJobs.length);
    
    const listDiv = $('#non-series-list');
    listDiv.empty();
    
    let listHtml = '<ul class="mb-0">';
    nonSeriesJobs.forEach(job => {
        const typeBadge = job.type === 'movie' ? 
            '<span class="badge badge-primary">Movie</span>' : 
            `<span class="badge badge-secondary">${job.type}</span>`;
        listHtml += `<li>Job ${job.id}: ${job.title} ${typeBadge}</li>`;
    });
    listHtml += '</ul>';
    
    listDiv.html(listHtml);
}

function proceedToOptions() {
    $('#rename-confirmation-step').hide();
    $('#rename-options-step').show();
}

function resetModal() {
    // Reset all steps
    $('#rename-confirmation-step').hide();
    $('#rename-options-step').hide();
    $('#rename-series-selection-step').hide();
    $('#rename-preview-step').hide();
    $('#rename-results-step').hide();
    
    // Clear data
    previewData = null;
    $('#preview-table-body').empty();
    $('#preview-warnings').hide();
    $('#preview-outliers').hide();
    $('#preview-conflicts').hide();
    $('#series-groups-container').empty();
    $('#disc-assignment-container').empty();
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
                const hasMultipleSeries = !seriesInfo.consistent || 
                    (response.preview.outliers && response.preview.outliers.length > 0);
                
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
            if (typeof conflict === 'string') {
                conflictHtml += `<li>${conflict}</li>`;
            } else {
                conflictHtml += `<li>Job ${conflict.job_id}: ${conflict.reason}</li>`;
            }
        });
        conflictHtml += '</ul>';
        conflictHtml += '<strong>Conflicts will be resolved with timestamps during execution.</strong>';
        conflictDiv.html(conflictHtml);
        conflictDiv.show();
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
        } else if (conflictByJob[jobId] || conflictByJob[newPath]) {
            statusBadge = '<span class="badge badge-warning">Conflict (will add timestamp)</span>';
            statusClass = 'table-warning';
        } else {
            statusBadge = '<span class="badge badge-success">Ready</span>';
            statusClass = '';
        }
        
        const row = `
            <tr class="${statusClass}">
                <td>${jobId}</td>
                <td>${title}</td>
                <td>${discLabel}</td>
                <td><small><code>${oldPath}</code></small></td>
                <td><small><code>${newPath}</code></small></td>
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
            if (response.success) {
                currentBatchId = response.batch_id;
                displayResults(response);
                
                // Move to results step
                $('#rename-preview-step').hide();
                $('#rename-results-step').show();
                
                // Clear selection and reload page after a delay
                setTimeout(function() {
                    location.reload();
                }, 3000);
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
        
        html += '<p class="mb-0"><small>Page will reload in 3 seconds...</small></p>';
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
                
                // Reload page after delay
                setTimeout(function() {
                    location.reload();
                }, 2000);
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
        <div class="alert alert-${type} alert-dismissible fade show" role="alert" 
             style="position: fixed; top: 80px; right: 20px; z-index: 9999; min-width: 300px; max-width: 500px;">
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


/**
 * =============================================================================
 * Custom Lookup Functionality
 * Allows users to search and apply custom identification to misidentified discs
 * =============================================================================
 */

let customLookupData = null;
let selectedMatchData = null;

// Initialize custom lookup handlers
$(document).ready(function() {
    initializeCustomLookup();
});

function initializeCustomLookup() {
    // Custom lookup button
    $('#custom-lookup-btn').on('click', openCustomLookupModal);
    
    // Search step handlers
    $('#search-custom-btn').on('click', performCustomSearch);
    $('#custom-search-query').on('keypress', function(e) {
        if (e.which === 13) { // Enter key
            performCustomSearch();
        }
    });
    
    // Navigation handlers
    $('#back-to-search-btn').on('click', backToSearch);
    $('#back-to-results-btn').on('click', backToResults);
    $('#execute-lookup-btn').on('click', applyCustomLookup);
    
    // Modal reset on close
    $('#customLookupModal').on('hidden.bs.modal', resetCustomLookupModal);
}

function openCustomLookupModal() {
    if (selectedJobs.size === 0) {
        showToast('Please select at least one completed disc', 'warning');
        return;
    }
    
    // Reset modal
    resetCustomLookupModal();
    
    // Display selected discs
    displaySelectedDiscs();
    
    // Show modal
    $('#customLookupModal').modal('show');
}

function displaySelectedDiscs() {
    $('#lookup-disc-count').text(selectedJobs.size);
    
    const container = $('#lookup-selected-discs');
    container.empty();
    
    let html = '<ul class="mb-0">';
    selectedJobs.forEach(jobId => {
        const row = $(`.batch-table-row[data-job-id="${jobId}"]`);
        const title = row.find('.title-cell').text().trim();
        const label = row.find('td:eq(5)').text().trim(); // Label column
        const type = row.data('video-type');
        
        const typeBadge = type === 'series' ? 
            '<span class="badge badge-success">TV Series</span>' : 
            type === 'movie' ?
            '<span class="badge badge-primary">Movie</span>' :
            `<span class="badge badge-secondary">${type}</span>`;
        
        html += `<li>Job ${jobId}: ${title} ${typeBadge}`;
        if (label && label !== '-') {
            html += ` - Label: ${label}`;
        }
        html += '</li>';
    });
    html += '</ul>';
    
    container.html(html);
}

function performCustomSearch() {
    const query = $('#custom-search-query').val().trim();
    const videoType = $('#custom-video-type').val();
    
    if (!query) {
        showToast('Please enter a search query', 'warning');
        return;
    }
    
    const btn = $('#search-custom-btn');
    btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Searching...');
    
    $.ajax({
        url: '/batch_custom_lookup',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            action: 'search',
            query: query,
            video_type: videoType
        }),
        success: function(response) {
            if (response.success && response.results && response.results.length > 0) {
                customLookupData = response;
                displaySearchResults(response.results);
                
                // Move to results step
                $('#lookup-search-step').hide();
                $('#lookup-results-step').show();
            } else {
                showToast('No results found for "' + query + '"', 'warning');
            }
        },
        error: function(xhr) {
            let msg = 'Search failed';
            if (xhr.responseJSON && xhr.responseJSON.error) {
                msg += ': ' + xhr.responseJSON.error;
            }
            showToast(msg, 'danger');
        },
        complete: function() {
            btn.prop('disabled', false).html('<i class="fa fa-search"></i> Search');
        }
    });
}

function displaySearchResults(results) {
    const container = $('#search-results-container');
    container.empty();
    
    results.forEach((result, index) => {
        const posterUrl = result.poster_url && result.poster_url !== 'N/A' ? 
            result.poster_url : 'static/img/none.png';
        
        const typeBadge = result.type === 'series' ? 
            '<span class="badge badge-success">TV Series</span>' : 
            '<span class="badge badge-primary">Movie</span>';
        
        const cardHtml = `
            <div class="col-xl-3 col-lg-4 col-md-6 mb-3">
                <div class="card h-100 search-result-card" data-index="${index}" style="cursor: pointer;">
                    <img src="${posterUrl}" class="card-img-top" alt="Poster" style="height: 300px; object-fit: cover;">
                    <div class="card-body">
                        <h6 class="card-title">${result.title}</h6>
                        <p class="card-text small">
                            <strong>Year:</strong> ${result.year || 'N/A'}<br>
                            <strong>Type:</strong> ${typeBadge}<br>
                            <strong>IMDb:</strong> ${result.imdb_id || 'N/A'}
                        </p>
                        <button class="btn btn-success btn-sm btn-block select-result-btn" data-index="${index}">
                            <i class="fa fa-check"></i> Select This
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        container.append(cardHtml);
    });
    
    // Add click handlers
    $('.select-result-btn').on('click', function(e) {
        e.stopPropagation();
        const index = $(this).data('index');
        selectSearchResult(index);
    });
    
    $('.search-result-card').on('click', function() {
        const index = $(this).data('index');
        selectSearchResult(index);
    });
}

function selectSearchResult(index) {
    if (!customLookupData || !customLookupData.results) {
        return;
    }
    
    selectedMatchData = customLookupData.results[index];
    
    // Display confirmation step
    displayCustomLookupConfirmation();
    
    // Move to confirmation step
    $('#lookup-results-step').hide();
    $('#lookup-confirm-step').show();
}

function displayCustomLookupConfirmation() {
    if (!selectedMatchData) {
        return;
    }
    
    // Display selected match info
    const posterUrl = selectedMatchData.poster_url && selectedMatchData.poster_url !== 'N/A' ? 
        selectedMatchData.poster_url : 'static/img/none.png';
    
    const typeBadge = selectedMatchData.type === 'series' ? 
        '<span class="badge badge-success">TV Series</span>' : 
        '<span class="badge badge-primary">Movie</span>';
    
    const matchInfoHtml = `
        <div class="row">
            <div class="col-md-3">
                <img src="${posterUrl}" class="img-fluid rounded" alt="Poster">
            </div>
            <div class="col-md-9">
                <h5>${selectedMatchData.title}</h5>
                <p>
                    <strong>Year:</strong> ${selectedMatchData.year || 'N/A'}<br>
                    <strong>Type:</strong> ${typeBadge}<br>
                    <strong>IMDb ID:</strong> ${selectedMatchData.imdb_id || 'N/A'}
                </p>
            </div>
        </div>
    `;
    
    $('#selected-match-info').html(matchInfoHtml);
    $('#confirm-disc-count').text(selectedJobs.size);
    
    // Build comparison table
    const tbody = $('#lookup-confirm-table-body');
    tbody.empty();
    
    selectedJobs.forEach(jobId => {
        const row = $(`.batch-table-row[data-job-id="${jobId}"]`);
        const currentTitle = row.find('.title-cell').text().trim();
        const currentType = row.data('video-type');
        const label = row.find('td:eq(5)').text().trim(); // Label column
        
        const currentTypeBadge = currentType === 'series' ? 
            '<span class="badge badge-success">TV Series</span>' : 
            currentType === 'movie' ?
            '<span class="badge badge-primary">Movie</span>' :
            `<span class="badge badge-secondary">${currentType}</span>`;
        
        const newTypeBadge = selectedMatchData.type === 'series' ? 
            '<span class="badge badge-success">TV Series</span>' : 
            '<span class="badge badge-primary">Movie</span>';
        
        const rowHtml = `
            <tr>
                <td>${jobId}</td>
                <td>${currentTitle}</td>
                <td>${currentTypeBadge}</td>
                <td>${label || '-'}</td>
                <td><strong>${selectedMatchData.title}</strong></td>
                <td>${newTypeBadge}</td>
            </tr>
        `;
        
        tbody.append(rowHtml);
    });
}

function backToSearch() {
    $('#lookup-results-step').hide();
    $('#lookup-search-step').show();
}

function backToResults() {
    $('#lookup-confirm-step').hide();
    $('#lookup-results-step').show();
}

function applyCustomLookup() {
    if (!selectedMatchData) {
        showToast('No match selected', 'warning');
        return;
    }
    
    const btn = $('#execute-lookup-btn');
    btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Applying...');
    
    $.ajax({
        url: '/batch_custom_lookup',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            action: 'apply',
            job_ids: Array.from(selectedJobs),
            title: selectedMatchData.title,
            year: selectedMatchData.year,
            video_type: selectedMatchData.type,
            imdb_id: selectedMatchData.imdb_id,
            poster_url: selectedMatchData.poster_url
        }),
        success: function(response) {
            if (response.success) {
                displayCustomLookupResults(response);
                
                // Move to results step
                $('#lookup-confirm-step').hide();
                $('#lookup-complete-step').show();
                
                // Reload page after delay
                setTimeout(function() {
                    location.reload();
                }, 3000);
            } else {
                showToast('Failed to apply custom identification: ' + response.error, 'danger');
            }
        },
        error: function(xhr) {
            let msg = 'Failed to apply custom identification';
            if (xhr.responseJSON && xhr.responseJSON.error) {
                msg += ': ' + xhr.responseJSON.error;
            }
            showToast(msg, 'danger');
        },
        complete: function() {
            btn.prop('disabled', false).html('<i class="fa fa-check"></i> Apply Custom Identification');
        }
    });
}

function displayCustomLookupResults(response) {
    const resultsDiv = $('#lookup-results-content');
    resultsDiv.empty();
    
    let html = '';
    
    if (response.success) {
        html += '<div class="alert alert-success">';
        html += '<h6><i class="fa fa-check-circle"></i> Custom Identification Applied Successfully</h6>';
        html += `<p>Updated <strong>${response.updated_count}</strong> disc(s) with:</p>`;
        html += '<ul>';
        html += `<li><strong>Title:</strong> ${selectedMatchData.title}</li>`;
        html += `<li><strong>Year:</strong> ${selectedMatchData.year || 'N/A'}</li>`;
        html += `<li><strong>Type:</strong> ${selectedMatchData.type}</li>`;
        html += `<li><strong>IMDb ID:</strong> ${selectedMatchData.imdb_id || 'N/A'}</li>`;
        html += '</ul>';
        
        if (response.errors && response.errors.length > 0) {
            html += '<p><strong>Errors:</strong></p><ul>';
            response.errors.forEach(error => {
                html += `<li class="text-danger">${error}</li>`;
            });
            html += '</ul>';
        }
        
        html += '<p class="mb-0"><small>Page will reload in 3 seconds...</small></p>';
        html += '</div>';
    } else {
        html += '<div class="alert alert-danger">';
        html += '<h6><i class="fa fa-exclamation-circle"></i> Custom Identification Failed</h6>';
        html += `<p>${response.error}</p>`;
        html += '</div>';
    }
    
    resultsDiv.html(html);
}

function resetCustomLookupModal() {
    // Reset all steps
    $('#lookup-search-step').show();
    $('#lookup-results-step').hide();
    $('#lookup-confirm-step').hide();
    $('#lookup-complete-step').hide();
    
    // Clear data
    customLookupData = null;
    selectedMatchData = null;
    
    // Clear form
    $('#custom-search-query').val('');
    $('#custom-video-type').val('series');
    
    // Clear containers
    $('#lookup-selected-discs').empty();
    $('#search-results-container').empty();
    $('#selected-match-info').empty();
    $('#lookup-confirm-table-body').empty();
    $('#lookup-results-content').empty();
}
