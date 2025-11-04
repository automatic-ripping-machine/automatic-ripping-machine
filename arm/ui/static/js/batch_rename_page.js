/**
 * Batch Rename Page functionality
 * Handles multi-select grid view, confirmation, preview, execution, and rollback
 * Uses shared utilities from batch_rename_shared.js
 */

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
    $('#back-from-series-btn').on('click', function() {
        BatchRenameShared.backToOptionsFromSeries();
    });
    $('#confirm-series-btn').on('click', generatePreviewWithSeries);
    $('#back-to-options-btn').on('click', function() {
        BatchRenameShared.backToOptions();
    });
    $('#execute-rename-btn').on('click', executeRename);
    $('#rollback-btn').on('click', rollbackRename);
    
    // Modal reset on close
    $('#batchRenameModal').on('hidden.bs.modal', resetModal);

    // Load default config values
    BatchRenameShared.loadDefaultConfig();
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

function openBatchRenameModal() {
    if (selectedJobs.size === 0) {
        BatchRenameShared.showToast('Please select at least one completed disc', 'warning');
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
        const escapedType = escapeHtml(job.type);
        const typeBadge = job.type === 'movie' ? 
            '<span class="badge badge-primary">Movie</span>' : 
            `<span class="badge badge-secondary">${escapedType}</span>`;
    listHtml += `<li>Job ${escapeHtml(job.id.toString())}: ${escapeHtml(job.title)} ${typeBadge}</li>`;
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
    BatchRenameShared.detectSeries(selectedJobs, function(preview) {
        previewData = preview;

        // Check if series selection is required
        if (preview.requires_series_selection) {
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

    BatchRenameShared.executeRename(selectedJobs, function(response) {
        if (response.success) {
            currentBatchId = response.batch_id;
            BatchRenameShared.displayResults(response);

            // Move to results step
            $('#rename-preview-step').hide();
            $('#rename-results-step').show();

            // Clear selection and reload page after a delay
            setTimeout(function() {
                location.reload();
            }, 3000);
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
        // Reload page after delay
        setTimeout(function() {
            location.reload();
        }, 2000);
    });
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
        BatchRenameShared.showToast('Please select at least one completed disc', 'warning');
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
        const title = escapeHtml(row.find('.title-cell').text().trim());
        const label = escapeHtml(row.find('td:eq(5)').text().trim()); // Label column
        const type = row.data('video-type');
        
        const escapedType = escapeHtml(type);
        const typeBadge = type === 'series' ? 
            '<span class="badge badge-success">TV Series</span>' : 
            type === 'movie' ?
            '<span class="badge badge-primary">Movie</span>' :
            `<span class="badge badge-secondary">${escapedType}</span>`;
        
    html += `<li>Job ${escapeHtml(jobId.toString())}: ${title} ${typeBadge}`;
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
        BatchRenameShared.showToast('Please enter a search query', 'warning');
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
                BatchRenameShared.showToast('No results found for "' + query + '"', 'warning');
            }
        },
        error: function(xhr) {
            let msg = 'Search failed';
            if (xhr.responseJSON && xhr.responseJSON.error) {
                msg += ': ' + xhr.responseJSON.error;
            }
            BatchRenameShared.showToast(msg, 'danger');
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
        
        const posterEsc = escapeHtml(posterUrl);
        const titleEsc = escapeHtml(result.title);
        const yearEsc = escapeHtml(result.year || 'N/A');
        const imdbEsc = escapeHtml(result.imdb_id || 'N/A');
        const cardHtml = `
            <div class="col-xl-3 col-lg-4 col-md-6 mb-3">
                <div class="card h-100 search-result-card" data-index="${escapeHtml(index.toString())}" style="cursor: pointer;">
                    <img src="${posterEsc}" class="card-img-top" alt="Poster" style="height: 300px; object-fit: cover;">
                    <div class="card-body">
                        <h6 class="card-title">${titleEsc}</h6>
                        <p class="card-text small">
                            <strong>Year:</strong> ${yearEsc}<br>
                            <strong>Type:</strong> ${typeBadge}<br>
                            <strong>IMDb:</strong> ${imdbEsc}
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
    
    const posterEsc = escapeHtml(posterUrl);
    const titleEsc = escapeHtml(selectedMatchData.title);
    const yearEsc = escapeHtml(selectedMatchData.year || 'N/A');
    const imdbEsc = escapeHtml(selectedMatchData.imdb_id || 'N/A');
    const matchInfoHtml = `
        <div class="row">
            <div class="col-md-3">
                <img src="${posterEsc}" class="img-fluid rounded" alt="Poster">
            </div>
            <div class="col-md-9">
                <h5>${titleEsc}</h5>
                <p>
                    <strong>Year:</strong> ${yearEsc}<br>
                    <strong>Type:</strong> ${typeBadge}<br>
                    <strong>IMDb ID:</strong> ${imdbEsc}
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
                <td>${escapeHtml(jobId.toString())}</td>
                <td>${escapeHtml(currentTitle)}</td>
                <td>${currentTypeBadge}</td>
                <td>${escapeHtml(label || '-')}</td>
                <td><strong>${escapeHtml(selectedMatchData.title)}</strong></td>
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
        BatchRenameShared.showToast('No match selected', 'warning');
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
                BatchRenameShared.showToast('Failed to apply custom identification: ' + response.error, 'danger');
            }
        },
        error: function(xhr) {
            let msg = 'Failed to apply custom identification';
            if (xhr.responseJSON && xhr.responseJSON.error) {
                msg += ': ' + xhr.responseJSON.error;
            }
            BatchRenameShared.showToast(msg, 'danger');
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
    html += `<p>Updated <strong>${escapeHtml(response.updated_count.toString())}</strong> disc(s) with:</p>`;
    html += '<ul>';
    html += `<li><strong>Title:</strong> ${escapeHtml(selectedMatchData.title)}</li>`;
    html += `<li><strong>Year:</strong> ${escapeHtml(selectedMatchData.year || 'N/A')}</li>`;
    html += `<li><strong>Type:</strong> ${escapeHtml(selectedMatchData.type)}</li>`;
    html += `<li><strong>IMDb ID:</strong> ${escapeHtml(selectedMatchData.imdb_id || 'N/A')}</li>`;
        html += '</ul>';
        
        if (response.errors && response.errors.length > 0) {
            html += '<p><strong>Errors:</strong></p><ul>';
            response.errors.forEach(error => {
                html += `<li class="text-danger">${escapeHtml(error)}</li>`;
            });
            html += '</ul>';
        }
        
        html += '<p class="mb-0"><small>Page will reload in 3 seconds...</small></p>';
        html += '</div>';
    } else {
        html += '<div class="alert alert-danger">';
        html += '<h6><i class="fa fa-exclamation-circle"></i> Custom Identification Failed</h6>';
    html += `<p>${escapeHtml(response.error)}</p>`;
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
