/*jshint multistr: true */
/*jshint esversion: 6 */
/*global $:false, jQuery:false */
/* jshint node: true */
/* jshint strict: false */

function getRipperName(job, idsplit) {
    let ripper_name;
    if (job.ripper) {
        ripper_name = job.ripper;
    } else {
        if (idsplit[0] === "0") {
            ripper_name = "Local";
        } else {
            ripper_name = "";
        }
    }
    return ripper_name;
}

function addJobItem(job) {
    // Local server or remote
    const idsplit = job.job_id.split("_");
    console.log(idsplit[1] + " - " + idsplit[0] )
    //Start creating the card with job id and header title
    let x = "<div class=\"col-md-4\" id=\"jobId" + job.job_id + "\"><div class=\"card mb-3  mx-auto\" style=\"min-height: 420px;\">";
    x += "<div class=\"card-header row no-gutters justify-content-center\"><strong id=\"jobId" + job.job_id + "_header\">" + titleManual(job) + "</strong></div>";
    // Main holder for the 3 sections of info - includes 1 section (Poster img)
    // We need to check if idsplit is undefined, database page doesn't have splitid's
    if(idsplit[1] === undefined){
        x += "<div class=\"row no-gutters\"><div class=\"col-lg-4\"><a href=\"/jobdetail?job_id=" + job.job_id + "\">" + posterCheck(job) + "</a></div>";
    }else {
        x += "<div class=\"row no-gutters\"><div class=\"col-lg-4\"><a href=\"" + job.server_url + "/jobdetail?job_id=" + idsplit[1] + "\">" + posterCheck(job) + "</a></div>";
    }
    // Section 2 (Middle)  Contains Job info (status, type, device, start time, progress)
    x += buildMiddleSection(job);
    x += buildRightSection(job, idsplit);
    // Close Job.card
    x += "</div></div></div></div></div></div></div>";
    return x;
}

function transcodingCheck(job) {
    let x="";
    if (job.status === "transcoding" && job.stage !== "" && job.progress) {
        x += "<div id=\"jobId" + job.job_id + "_stage\"><b>Stage: </b>" + job.stage + "</div>";
        x += "<div id=\"jobId" + job.job_id + "_progress\" >";
        x += "<div class=\"progress\">" +
            "<div class=\"progress-bar progress-bar-striped progress-bar-animated\" role=\"progressbar\" aria-valuenow=\"" +
            job.progress_round + "\" aria-valuemin=\"0\" aria-valuemax=\"100\" style=\"width: " + job.progress_round + "%\">" +
            "<small class=\"justify-content-center d-flex position-absolute w-100\">" + job.progress + "%</small>" +
            "</div></div></div>" +
            "<div id=\"jobId" + job.job_id + "_eta\"><b>ETA: </b>" + job.eta + "</div>";
    }
    // YYYY-MM-DD
    const d  = new Date(Date.parse(job.start_time));
    const datestring = d.getFullYear()  + "-" + (d.getMonth()+1) + "-" + d.getDate()

    x += "<strong>Start Date:</strong> " + datestring + "<br>";
    x += "<strong>Start Time:</strong> "+ d.getHours().toString().padStart(2, '0') + ":" + d.getMinutes().toString().padStart(2, '0') + "<br>";
    x += "<strong>Job Time:</strong> " + (job.job_length === undefined ? "Ongoing" : job.job_length) + "<br>";
    return x;
}

function musicCheck(job, idsplit) {
    let x="";
    if (job.video_type !== "Music") {
        x = "<a href=\"titlesearch?job_id=" + idsplit[1] + "\" class=\"btn btn-primary\">Title Search</a>" +
            "<a href=\"customTitle?job_id=" + idsplit[1] + "\" class=\"btn btn-primary\">Custom Title</a>" +
            "<a href=\"changeparams?config_id=" + idsplit[1] + "\" class=\"btn btn-primary\">Edit Settings</a>";
    }
    return x;
}

function posterCheck(job) {
    let x;
    if (job.poster_url !== "None" && job.poster_url !== "N/A") {
        x = "<img id=\"jobId" + job.job_id + "_poster_url\" alt=\"poster img\" src=\"" + job.poster_url + "\" width=\"240px\" class=\"img-thumbnail\">";
    } else {
        x = "<img id=\"jobId" + job.job_id + "_poster_url\" alt=\"poster img\" src=\"/static/img/none.png\" width=\"240px\" class=\"img-thumbnail\">";
    }
    return x;
}

function titleManual(job) {
    let x;
    if (job.title_manual !== "None") {
        x = job.title_manual + "(" + job.year + ")";
    } else {
        x = job.title + "(" + job.year + ")";
    }
    return x;
}

function buildMiddleSection(job) {
    let x;
    x = "<div class=\"col-lg-4\"><div class=\"card-body px-1 py-1\">";
    x += "<div id=\"jobId" + job.job_id + "_year\"><b>Year: </b>" + job.year + "</div>";
    x += "<div id=\"jobId" + job.job_id + "_video_type\"><b>Type: </b>" + job.video_type + "</div>";
    x += "<div id=\"jobId" + job.job_id + "_devpath\"><b>Device: </b>" + job.devpath + "</div>";
    x += "<div><b>Status: </b><img id=\"jobId" + job.job_id + "_status\" src=\"static/img/" + job.status +
        ".png\" height=\"20px\" alt=\"" + job.status + "\" title=\"" + job.status + "\"></div>";
    x += "<div id=\"jobId" + job.job_id + "_progress_section\">" + transcodingCheck(job) + "</div></div></div>";
    return x;
}

function buildRightSection(job, idsplit) {
    let x;
    // idsplit[1] should only be undefined on the /database page
    if (idsplit[1] === undefined){
        console.log("idsplit undefined... fixing");
        idsplit[0] = "0";
        idsplit[1] = job.job_id
    }else{
        console.log("idsplit " + idsplit[0] + " - " + idsplit[1]);
    }
    // Section 3 (Right Top) Contains Config.values
    x = "<div class=\"col-lg-4\"><div class=\"card-body px-1 py-1\">";
    x += "<div id=\"jobId" + job.job_id + "_RIPPER\"><b>Ripper: </b>" + getRipperName(job, idsplit) + "</div>";
    x += "<div id=\"jobId" + job.job_id + "_RIPMETHOD\"><b>Rip Method: </b>" + job.config.RIPMETHOD + "</div>";
    x += "<div id=\"jobId" + job.job_id + "_MAINFEATURE\"><b>Main Feature: </b>" + job.config.MAINFEATURE + "</div>";
    x += "<div id=\"jobId" + job.job_id + "_MINLENGTH\"><b>Min Length: </b>" + job.config.MINLENGTH + "</div>";
    x += "<div id=\"jobId" + job.job_id + "_MAXLENGTH\"><b>Max Length: </b>" + job.config.MAXLENGTH + "</div>";
    x += "</div>";
    // Section 3 (Right Bottom) Contains Buttons for arm json api
    x += "<div class=\"card-body px-2 py-1\">" +
        "<div class=\"btn-group-vertical\" role=\"group\" aria-label=\"buttons\" " + (idsplit[0] !== "0" ? "style=\"display: none;\"" : "") + ">" +
        "<button type=\"button\" class=\"btn btn-primary\" data-toggle=\"modal\" data-target=\"#exampleModal\" data-type=\"abandon\" data-jobid=\"" +
        idsplit[1] + "\" data-href=\"json?job=" + idsplit[1] + "&mode=abandon\">Abandon Job</button>" +
        "<a href=\"logs?logfile=" + job.logfile + "&mode=full\" class=\"btn btn-primary\">View logfile</a>";
    x += musicCheck(job, idsplit);
    x += "<button type=\"button\" class=\"btn btn-primary\" data-toggle=\"modal\" data-target=\"#exampleModal\" data-type=\"fixperms\" data-jobid=\"" +
        idsplit[1]+ "\" data-href=\"json?mode=fixperms&job=" + idsplit[1] + "\">Fix Permissions</button>";
    return x;
}


function updateModal(modal) {
    let modalTitle;
    let modalBody;
    switch (actionType) {
        case "abandon":
            modalTitle = "Abandon This Job ?";
            modalBody = "This item will be set to abandoned. You cannot set it back to active! Are you sure?";
            break;
        case "delete":
        modalTitle = "Delete this job forever ?";
        modalBody = "This item will be permanently deleted and cannot be recovered. Are you sure?";
            break;
        case "search":
        modalTitle = "Search the database";
        modalBody = '<div class="input-group mb-3">' +
            '<div class="input-group-prepend"><span class="input-group-text" id="searchlabel">Search </span></div>' +
            '<input type="text" class="form-control" id="searchquery" aria-label="searchquery" ' +
            'name="searchquery" placeholder="Search...." value="" aria-describedby="searchlabel">' +
            '<div id="validationServer03Feedback" class="invalid-feedback">Search string too short.</div></div>';
            break;
        default:
            modalTitle = "Do you want to leave this page ?";
            modalBody = "To view the log file you need to leave this page. Would you like to leave ?";
    }
    modal.find('.modal-title').text(modalTitle);
    modal.find('.modal-body').html(modalBody);
}


function hideModal() {
    $('#exampleModal').modal('toggle');
    $('#message1').removeClass('d-none');
    $('#message2').addClass('d-none');
    $('#message3').addClass('d-none');
}
