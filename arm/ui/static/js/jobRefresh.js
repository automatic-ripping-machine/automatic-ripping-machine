/*jshint multistr: true */
/*jshint esversion: 6 */
/*global $:false, jQuery:false */
/* jshint node: true */
/* jshint strict: false */

let hrrref = "";
let activeJob = null;
let actionType = null;

$(document).ready(function () {
    pushChildServers();
    refreshJobs();
    activeTab("home");

    $("#save-yes").bind('click', function () {
        console.log(hrrref);
        if (hrrref !== "") {
            // Add the spinner to let them know we are loading
            $("#m-body").append('<div class="d-flex justify-content-center">' +
                                '<div class="spinner-border" role="status">' +
                                '<span class="sr-only">Loading...</span>' +
                                '</div>' +
                                '</div>');
            $.get(hrrref, function (data) {
                console.log(data.success);
                console.log("#jobId" + activeJob);
                if (data.success && data.mode === "abandon") {
                    $("#id" + activeJob).remove();
                    $("#message1 .alert-heading").html("Job was successfully abandoned");
                    $('#exampleModal').modal('toggle');
                    $('#message1').removeClass('d-none');
                    setTimeout(
                        function () {
                            $('#message1').addClass('d-none');
                        },
                        5000
                    );
                }
            }, "json");
        }
    });
    $("#save-no").bind('click', function () {
            $('#exampleModal').modal('toggle');
    });
    $('#exampleModal').on('show.bs.modal', function (event) {
        let button = $(event.relatedTarget); // Button that triggered the modal
        actionType = button.data('type'); // Extract info from data-* attributes
        hrrref = button.data('href');
        activeJob = button.data('jobid');
        const modal = $(this);
        updateModal(modal);
    });
});


function updateProgress(job, oldJob) {
    let subProgressBar = '<div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" ' + 'aria-valuenow="' +
                         job.progress_round + '" aria-valuemin="0" aria-valuemax="100" style="width: ' + job.progress_round + '%">' +
                         '<small class="justify-content-center d-flex position-absolute w-100">' + job.progress + '%</small>' +
                         '</div>' +
                         '</div>';
    let mainProgressBar = '<div id="jobId' + job.job_id + '_stage"><b>Stage: </b>' + job.stage + '</div>' +
                         '<div id="jobId' + job.job_id + '_progress" >' +
                         '<div class="progress">' +
                         subProgressBar +
                         '</div>' +
                         '<div id="jobId' + job.job_id + '_eta"><b>ETA: </b>' + job.eta + '</div>';
    let progressSection = $('#jobId' + job.job_id + '_progress_section');
    let stage = $('#jobId' + job.job_id + '_stage');
    let eta = $('#jobId' + job.job_id + '_eta');
    if (job.status === "transcoding" || job.status === "ripping" && job.stage !== '' && job.progress) {
        if (progressSection[0].innerHTML === "") {
            progressSection[0].innerHTML = mainProgressBar;
        } else {
            if (job.progress_round !== oldJob.progress_round || job.progress !== oldJob.progress) {
                $('#jobId' + job.job_id + '_progress')[0].innerHTML = '<div class="progress">' +
                         subProgressBar;
            }
            updateContents(stage, job, 'stage', 'Stage');
            updateContents(eta, job, 'eta', 'ETA');
        }
    }
}

function updateContents(item, job, changeItem, keyString){
    if (!item[0].innerText.includes(job[changeItem])) {
        item[0].innerHTML = '<b>' + keyString + ': </b>' + job[changeItem];
    }
    console.log("updated:" +changeItem);
}

function updateJobItem(oldJob, job) {
    let cardHeader = $('#jobId' + job.job_id + '_header');
    let posterUrl = $('#jobId' + job.job_id + '_poster_url');
    let jobTitle = $('#jobId' + job.job_id + '_title');
    let jobYear = $('#jobId' + job.job_id + '_year');
    let videoType = $('#jobId' + job.job_id + '_video_type');
    let devPath = $('#jobId' + job.job_id + '_devpath');
    let status = $('#jobId' + job.job_id + '_status');
    let ripMethod = $('#jobId' + job.job_id + '_RIPMETHOD');
    let mainFeature = $('#jobId' + job.job_id + '_MAINFEATURE');
    let minLength = $('#jobId' + job.job_id + '_MINLENGTH');
    let maxLength = $('#jobId' + job.job_id + '_MAXLENGTH');

    if (cardHeader[0].innerText !== job.title + " (" + job.year + ")"){
        cardHeader[0].innerText = job.title + " (" + job.year + ")";
    }
    if (job.poster_url !== posterUrl[0].src && job.poster_url !== "None" && job.poster_url !== "N/A") {
        posterUrl[0].src = job.poster_url;
    }
    // TODO: Check against the auto title
    if (job.title !== jobTitle[0].innerText) {
        jobTitle[0].innerText = job.title;
    }

    updateContents(jobYear, job, 'year', 'Year');
    updateContents(devPath, job, 'devpath', 'Device');
    updateContents(videoType, job, 'video_type', 'Type');
    //  Adding more:  updateContents(devPath, job, 'devpath', 'Device');

    if (job.status !== status[0].title) {
        status[0].src = 'static/img/' + job.status + '.png';
        status[0].alt = job.status;
        status[0].title = job.status;
    }
    updateProgress(job, oldJob);

    if (!ripMethod[0].innerText.includes(job.config.RIPMETHOD)) {
        ripMethod[0].innerHTML = '<b>Rip Method: </b>' + job.config.RIPMETHOD;
    }

    if (!mainFeature[0].innerText.includes(job.config.MAINFEATURE)) {
        mainFeature[0].innerHTML = '<b>Main Feature: </b>' + job.config.MAINFEATURE;
    }

    if (!minLength[0].innerText.includes(job.config.MINLENGTH)) {
        minLength[0].innerHTML = '<b>Min Length: </b>' + job.config.MINLENGTH;
    }

    if (!maxLength[0].innerText.includes(job.config.MAXLENGTH)) {
        maxLength[0].innerHTML = '<b>Max Length: </b>' + job.config.MAXLENGTH;
    }
}

function removeJobItem(job) {
    $('#jobId' + job.job_id).remove();
}

function refreshJobsComplete() {
    console.log(activeJobs);
    $.each(activeJobs, function (index, job) {
        if (typeof (job) !== "undefined" && !job.active) {
            console.log("job isn't active");
            removeJobItem(job);
            activeJobs.splice(index, 1);
        }
    });

    $("#joblist .col-md-4").sort(function (a, b) {
        if (a.id === b.id) {
            return 0;
        }
        return a.id < b.id ? -1 : 1;
    }).each(function () {
        var elem = $(this);
        elem.remove();
        $(elem).appendTo("#joblist");
    });
}

function refreshJobs() {

    let serverCount = activeServers.length;

    $.each(activeServers, function(server_index, server_url) {
        $.each(activeJobs, function (index) {
            activeJobs[index].active = false;
        });

        $.ajax({
            url: server_url+"/json?mode=joblist",
            type: "get",
            timeout: 2000,
            error: function() { --serverCount; },
            complete: function() {
                refreshJobsComplete();
            },
            success: function (data) {
                $.each(data.results, function (_index, job) {
                    job.job_id = server_index+"_"+job.job_id;
                    job.ripper = data.arm_name ? data.arm_name : "";
                    job.server_url = server_url
                    if (activeJobs.some(e => e.job_id === job.job_id)) {
                        var oldJob = activeJobs.find(e => e.job_id === job.job_id);

                        job.active = true;
                        activeJobs[activeJobs.indexOf(oldJob)] = job;

                        updateJobItem(oldJob, job);
                    } else {
                        job.active = true;
                        activeJobs.push(job);

                        $('#joblist').append(addJobItem(job));
                    }
                    serverCount--;
                });
            }
        });
    });
}

function pushChildServers() {
    activeServers.push(location.origin);
    let childs = $("#children");
    let children = childs.text().trim();
    if (children) {
        var childLinks = [];
        var children_arr = children.split(",");
        $.each(children_arr, function (_index, value) {
            activeServers.push(value);
            childLinks.push("<a target='_blank' href='" + value + "'>" + value + "</a>");
        });
        childs.html("Children: <br />" + childLinks.join("<br />"));
    }
}

var activeServers = [];
var activeJobs = [];
const intervalId = window.setInterval(refreshJobs, 5000);