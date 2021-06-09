var hrrref = "";
var wedeleted = "{{ success }}";
var activeJob = null;
var actionType = null;
$(document).ready(function () {
    $("#save-yes").bind('click', function () {
        console.log(hrrref)
        if (hrrref != "") {
            // Add the spinner to let them know we are loading
            $("#m-body").append('<div class="d-flex justify-content-center">\
										<div class="spinner-border" role="status">\
										<span class="sr-only">Loading...</span>\
										</div>\
										</div>');
            $.get(hrrref, function (data) {
                console.log(data['success']);
                console.log("#jobId" + activeJob)
                if (data['success'] === true) {
                    if (data['mode'] === "abandon") {
                        $("#id" + activeJob).remove()
                        $("#message1 .alert-heading").html("Job was successfully abandoned")
                        $('#exampleModal').modal('toggle');
                        $('#message1').removeClass('d-none');
                        $('#message2').addClass('d-none');
                        $('#message3').addClass('d-none');
                        setTimeout(
                            function () {
                                $('#message1').addClass('d-none');
                            },
                            5000
                        );
                    }
                } else {
                    $('#message3').removeClass('d-none');
                    $('#message1').addClass('d-none');
                    $('#message2').addClass('d-none');
                    $('#exampleModal').modal('toggle');
                    setTimeout(
                        function () {
                            $('#message3').addClass('d-none');
                        },
                        5000
                    );
                }
            }, "json");
        }
    });
    $("#save-no").bind('click', function () {
        if (hrrref == "entryWarn") {
            console.log("use wants to go away");
            window.location.href = "/";
            return false;
        } else {

            console.log("user shouldnt be here...");
            $('#exampleModal').modal('toggle');
        }
    });
    $('#exampleModal').on('show.bs.modal', function (event) {
        var button = $(event.relatedTarget) // Button that triggered the modal
        actionType = button.data('type') // Extract info from data-* attributes
        hrrref = button.data('href')
        activeJob = button.data('jobid')
        //jobId = job.job_id
        console.log(hrrref)
        console.log(activeJob)
        console.log(actionType)

        if (actionType == "abandon") {
            var modalTitle = "Abandon This Job ?"
            var modalBody = "This item will be set to abandoned. You cannot set it back to active! Are you sure?"
        } else if (actionType == "delete") {
            var modalTitle = "Delete this job forever ?"
            var modalBody = "This item will be permanently deleted and cannot be recovered. Are you sure?"
        } else if (actionType == "search") {
            var modalTitle = "Search the database"
            //var modalBody = '<input type="email" class="form-control" id="searchquery" placeholder="Search titles">'
            var modalBody = '<div class="input-group mb-3">\
								<div class="input-group-prepend">\
									<span class="input-group-text" id="searchlabel">Search </span>\
								</div>\
								<input type="text" class="form-control" id="searchquery" aria-label="searchquery" name="searchquery" placeholder="Search...." value="" aria-describedby="searchlabel">\
								      <div id="validationServer03Feedback" class="invalid-feedback">\
										Search string too short.\
									  </div>\
								</div>';
        } else {
            var modalTitle = "Do you want to leave this page ?"
            var modalBody = "To view the log file you need to leave this page. Would you like to leave ?"
        }
        var modal = $(this)
        modal.find('.modal-title').text(modalTitle)
        modal.find('.modal-body').html(modalBody)
    })
});

function addJobItem(job) {
    // TODO: this needs converted to the new format seen on database page
    var x = '<div class="col-md-4" id="jobId' + job["job_id"] + '">\
    <div class="card mb-3  mx-auto">\
                <div class="card-header row no-gutters justify-content-center">\
                    <strong>';
    if (job['title_manual'] !== "None") {
        x += job["title_manual"] + ' ('+job['year']+')';
    }else{
        x += job["title"] + ' (' + job['year'] + ')';
    }
    x += '</strong>\
          </div>\
          <div class="row no-gutters">\
          <div class="col-lg-4">\
	      <a href="jobdetail?job_id=' + job["job_id"] + '">';
    if(job["poster_url"] !== "None") {
        x += '<img id="jobId' + job["job_id"] + '_poster_url" src="' + job["poster_url"] + '" width="240px" class="img-thumbnail">';
    }else{
        x += '<img id="jobId' + job["job_id"] + '_poster_url" src="/static/img/none.png" width="240px" class="img-thumbnail">';
    }
    x+='      </a>\
          </div>\
          <div class="col-lg-4">\
          <div class="card-body px-1 py-1">'

    x += '<div id="jobId' + job["job_id"] + '_title"><b>' + job["title"] + '</b></div>'
	x += '<div id="jobId' + job["job_id"] + '_year"><b>Year: </b>' + job["year"] +'</div>'
    x += '<div id="jobId' + job["job_id"] + '_video_type"><b>Type: </b>' + job['video_type'] + '</div>'
    x += '<div id="jobId' + job["job_id"] + '_devpath"><b>Device: </b>' + job['devpath'] + '</div>'
    x += '<div><b>Status: </b><img id="jobId' + job["job_id"] + '_status" src="static/img/' + job['status'] + '.png" height="20px" alt="' + job['status'] + '" title="' + job['status'] + '"></div>';

    x += '<div id="jobId' + job["job_id"] + '_progress_section">'
    if (job['status'] === "transcoding" && job['stage'] != '' && job['progress']) {
        x += '<div id="jobId' + job["job_id"] + '_stage"><b>Stage: </b>' + job['stage'] + '</div>'
        x += '<div id="jobId' + job["job_id"] + '_progress" >'
        x += '<div class="progress">\
			      <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" aria-valuenow="' + job['progress_round'] + '" aria-valuemin="0" aria-valuemax="100" style="width: ' + job['progress_round'] + '%">\
			          <small class="justify-content-center d-flex position-absolute w-100">' + job['progress'] + '%</small>\
                  </div>\
			  </div>\
			  </div>\
              <div id="jobId' + job["job_id"] + '_eta"><b>ETA: </b>' + job["eta"] + '</div>';
    }
    x += '</div>\
          </div>\
          </div>\
          <div class="col-lg-4">\
              <div class="card-body px-1 py-1">'

    x += '<div id="jobId' + job["job_id"] + '_RIPMETHOD"><b>Rip Method: </b>' + job['config']['RIPMETHOD'] + '</div>'
    x += '<div id="jobId' + job["job_id"] + '_MAINFEATURE"><b>Main Feature: </b>' + job['config']['MAINFEATURE'] + '</div>'
    x += '<div id="jobId' + job["job_id"] + '_MINLENGTH"><b>Min Length: </b>' + job['config']['MINLENGTH'] + '</div>'
    x += '<div id="jobId' + job["job_id"] + '_MAXLENGTH"><b>Max Length: </b>' + job['config']['MAXLENGTH'] + '</div>'

    x += '</div>\
                                <div class="card-body px-2 py-1">\
									<div class="btn-group-vertical" role="group" aria-label="buttons">\
										<button type="button" class="btn btn-primary" data-toggle="modal" data-target="#exampleModal" data-type="abandon" data-jobid="' + job["job_id"] + '" data-href="json?job=' + job["job_id"] + '&mode=abandon">Abandon Job</button>\
										<a href="logs?logfile=' + job['logfile'] + '&mode=full" class="btn btn-primary">View logfile</a>';
    if (job['video_type'] !== "Music") {
        x += '<a href="titlesearch?job_id=' + job['job_id'] + '" class="btn btn-primary">Title Search</a>\
                      <a href="customTitle?job_id=' + job['job_id'] + '" class="btn btn-primary">Custom Title</a>\
                      <a href="changeparams?config_id=' + job['job_id'] + '" class="btn btn-primary">Change Settings</a>';
    }
    x += '</div>\
                                </div>\
                            </div>\
                        </div>\
                    </div>\
                </div></div>';
    return x
}

function updateJobItem(oldJob, job) {
    if (job['poster_url'] !== $('#jobId' + job["job_id"] + '_poster_url')[0].src && job['poster_url'] !== "None") {
        $('#jobId' + job["job_id"] + '_poster_url')[0].src = job['poster_url'];
    }

    if (job["title"] !== $('#jobId' + job["job_id"] + '_title')[0].innerText) {
        $('#jobId' + job["job_id"] + '_title')[0].innerText = job["title"];
    }

    if (!$('#jobId' + job["job_id"] + '_year')[0].innerText.includes(job["year"])) {
        $('#jobId' + job["job_id"] + '_year')[0].innerHTML = '<b>Year: </b>' + job["year"];
    }

    if (!$('#jobId' + job["job_id"] + '_video_type')[0].innerText.includes(job["video_type"])) {
        $('#jobId' + job["job_id"] + '_video_type')[0].innerHTML = '<b>Type: </b>' + job["video_type"];
    }

    if (!$('#jobId' + job["job_id"] + '_devpath')[0].innerText.includes(job["devpath"])) {
        $('#jobId' + job["job_id"] + '_devpath')[0].innerHTML = '<b>Device: </b>' + job['devpath'];
    }

    if (job["status"] !== $('#jobId' + job["job_id"] + '_status')[0].title) {
        $('#jobId' + job["job_id"] + '_status')[0].src = 'static/img/' + job['status'] + '.png';
        $('#jobId' + job["job_id"] + '_status')[0].alt = job['status'];
        $('#jobId' + job["job_id"] + '_status')[0].title = job['status'];
    }

    if (job['status'] === "transcoding" && job.stage != '' && job.progress) {
        if ($('#jobId' + job["job_id"] + '_progress_section')[0].innerHTML === "") {
            var x = '<div id="jobId' + job["job_id"] + '_stage"><b>Stage: </b>' + job['stage'] + '</div>\
                <div id="jobId' + job["job_id"] + '_progress" >\
                <div class="progress">\
			      <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" aria-valuenow="' + job['progress_round'] + '" aria-valuemin="0" aria-valuemax="100" style="width: ' + job['progress_round'] + '%">\
			          <small class="justify-content-center d-flex position-absolute w-100">' + job['progress'] + '%</small>\
                  </div>\
			  </div>\
			  </div>\
              <div id="jobId' + job["job_id"] + '_eta"><b>ETA: </b>' + job["eta"] + '</div>';
            $('#jobId' + job["job_id"] + '_progress_section')[0].innerHTML = x;
        } else {
            if (!$('#jobId' + job["job_id"] + '_stage')[0].innerText.includes(job["stage"])) {
                $('#jobId' + job["job_id"] + '_stage')[0].innerHTML = '<b>Device: </b>' + job['stage'];
            }

            if (job["progress_round"] !== oldJob["progress_round"] || job["progress"] !== oldJob["progress"]) {
                $('#jobId' + job["job_id"] + '_progress')[0].innerHTML = '<div class="progress">\
			      <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" aria-valuenow="' + job['progress_round'] + '" aria-valuemin="0" aria-valuemax="100" style="width: ' + job['progress_round'] + '%">\
			          <small class="justify-content-center d-flex position-absolute w-100">' + job.progress + '%</small>\
                  </div>\
			  </div>';
            }

            if (!$('#jobId' + job["job_id"] + '_eta')[0].innerText.includes(job["eta"])) {
                $('#jobId' + job["job_id"] + '_eta')[0].innerHTML = '<b>ETA: </b>' + job["eta"];
            }
        }
    }

    if (!$('#jobId' + job["job_id"] + '_RIPMETHOD')[0].innerText.includes(job['config']['RIPMETHOD'])) {
        $('#jobId' + job["job_id"] + '_RIPMETHOD')[0].innerHTML = '<b>Rip Method: </b>' + job['config']['RIPMETHOD'];
    }

    if (!$('#jobId' + job["job_id"] + '_MAINFEATURE')[0].innerText.includes(job['config']['MAINFEATURE'])) {
        $('#jobId' + job["job_id"] + '_MAINFEATURE')[0].innerHTML = '<b>Main Feature: </b>' + job['config']['MAINFEATURE'];
    }

    if (!$('#jobId' + job["job_id"] + '_MINLENGTH')[0].innerText.includes(job['config']['MINLENGTH'])) {
        $('#jobId' + job["job_id"] + '_MINLENGTH')[0].innerHTML = '<b>Min Length: </b>' + job['config']['MINLENGTH'];
    }

    if (!$('#jobId' + job["job_id"] + '_MAXLENGTH')[0].innerText.includes(job['config']['MAXLENGTH'])) {
        $('#jobId' + job["job_id"] + '_MAXLENGTH')[0].innerHTML = '<b>Max Length: </b>' + job['config']['MAXLENGTH'];
    }
}

function removeJobItem(job) {
    $('#jobId' + job["job_id"]).remove();
}

function refreshJobs() {
    $.ajax({
        url: "json?mode=joblist",
        type: "get",
        success: function (data) {
            //$('.card-deck').html('')
            $.each(activeJobs, function (index, job) {
                activeJobs[index].active = false;
            });
            var size = Object.keys(data['results']).length;
            if (size > 0) {
                $.each(data['results'], function (index, job) {
                    //console.log(job);
                    if (activeJobs.some(e => e.job_id === job['job_id'])) {
                        var oldJob = activeJobs.find(e => e.job_id === job['job_id']);

                        job.active = true;
                        activeJobs[activeJobs.indexOf(oldJob)] = job;

                        updateJobItem(oldJob, job);
                    } else {
                        job.active = true;
                        activeJobs.push(job);

                        $('.card-deck').append(addJobItem(job));
                    }
                });
                //console.log($("#joblist").html());
                //console.log($("#tempjoblist").html());
                //console.log($("#joblist").html() !== $("#tempjoblist").html());
            }
            $.each(activeJobs, function (index, job) {
                if (!job.active) {
                    removeJobItem(job);
                    activeJobs.splice(index, 1);
                }
            });
        }
    });
}

var activeJobs = [];

refreshJobs();
activeTab("home");
var intervalId = window.setInterval(refreshJobs, 5000);