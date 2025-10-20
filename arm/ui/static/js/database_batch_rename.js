/**
 * Batch Rename functionality for Database View
 * Handles multi-select, preview, execution, and rollback of TV series disc renames
 * Uses shared utilities from batch_rename_shared.js
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
    BatchRenameShared.loadDefaultConfig();
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
            BatchRenameShared.showToast('Only completed jobs can be batch renamed', 'warning');
            return;
        }

        // Warn about non-series items but allow them
        if (videoType !== 'series') {
            BatchRenameShared.showToast('Warning: Job ' + jobId + ' is not marked as a TV series. It may not rename correctly.', 'info');
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
        BatchRenameShared.showToast(`Warning: ${nonSeriesCount} non-series items selected. They may not rename correctly.`, 'info');
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

function openBatchRenameModal() {
    if (selectedJobs.size === 0) {
        BatchRenameShared.showToast('Please select at least one completed job', 'warning');
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
    BatchRenameShared.detectSeries(selectedJobs, function(preview) {
        previewData = preview;

        // Check if we need series selection step
        const seriesInfo = preview.series_info || {};
        const hasMultipleSeries = !seriesInfo.consistent || (preview.outliers && preview.outliers.length > 0);

        if (hasMultipleSeries) {
            // Show series selection step
            BatchRenameShared.displaySeriesSelection(preview);
            $('#rename-options-step').hide();
            $('#rename-series-selection-step').show();
        } else {
            // Skip series selection, go straight to preview
            BatchRenameShared.displayPreview(preview);
            $('#rename-options-step').hide();
            $('#rename-preview-step').show();
        }
    });
}

function generatePreviewWithSeries() {
    BatchRenameShared.generatePreviewWithSeries(selectedJobs, function(preview) {
        previewData = preview;
        BatchRenameShared.displayPreview(preview);

        // Move to preview step
        $('#rename-series-selection-step').hide();
        $('#rename-preview-step').show();
    });
}

function executeRename() {
    if (!previewData) {
        BatchRenameShared.showToast('Please generate preview first', 'warning');
        return;
    }

    // Check for conflicts
    if (previewData.conflicts && previewData.conflicts.length > 0) {
        BatchRenameShared.showToast('Cannot execute: conflicts detected', 'danger');
        return;
    }

    BatchRenameShared.executeRename(selectedJobs, function(response) {
        if (response.success) {
            currentBatchId = response.batch_id;
            BatchRenameShared.displayResults(response);

            // Move to step 3
            $('#rename-preview-step').hide();
            $('#rename-results-step').show();

            // Clear selection and refresh page after a delay
            setTimeout(function() {
                deselectAllJobs();
            }, 2000);
        } else {
            BatchRenameShared.showToast('Execution failed: ' + response.message, 'danger');
            if (response.batch_id) {
                currentBatchId = response.batch_id;
            }
        }
    });
}

function rollbackRename() {
    BatchRenameShared.rollbackRename(currentBatchId, function(response) {
        $('#batchRenameModal').modal('hide');

        // Refresh page to show updated folders
        setTimeout(function() {
            location.reload();
        }, 1500);
    });
}
