/*jshint multistr: true */
/*jshint esversion: 6 */
/*global $:false, jQuery:false */
/* jshint node: true */
/* jshint strict: false */

var hrrref = "";
var activeJob = null;
var actionType = null;
$(document).ready(function () {
    //get the value
    var seen = checkCookie();
    if (seen == null) {
        /*have not agreed to understanding the risks, show modal*/
        hrrref = "entryWarn";
        $('div .modal-title').html("<p class=\"text-center text-danger\">WARNING");
        $('div.modal-body').html('<p class="text-center bg-danger text-white">This can be dangerous if you don\'t know what you\'re doing. <br> \
									You could delete all your of your database entries if you\'re not careful!!! <br> \
									Be careful!<br><br> Are you sure you want to continue ?</p>');
        $('#exampleModal').modal('show');
        $('#save-get-success').addClass('d-none');
        $('#save-get-failed').addClass('d-none');
        $('#message3').addClass('d-none');
        $('#message1').addClass('d-none');
    }
    $("#save-get-success").bind('click', function () {
        // Add the spinner to let them know we are loading
        $('#exampleModal').modal('show');
        $('.modal-title').text("Loading...");
        $('.modal-body').html("");
        $(".modal-body").append('<div class="d-flex justify-content-center">' +
            '<div class="spinner-border" role="status">' +
            '<span class="sr-only">Loading...</span>' +
            '</div>' +
            '</div>');
        hrrref = '/json?mode=getsuccessful';
        $.get(hrrref, function (data) {
            //console.log(data)
            if (data['success'] === true) {
                $('.card-deck').html('')
                var size = Object.keys(data['results']).length;
                console.log("length = " + size);
                if (size > 0) {
                    $.each(data['results'], function (index, value) {
                        z = addJobItem(value)
                        $('.card-deck').append(z);
                    });
                    console.log(data)
                } else {
                    $("#message1 .alert-heading").html("I couldn't find any results matching that title")
                    $('#message1').removeClass('d-none');
                    $('#exampleModal').modal('toggle');
                }
                $('#exampleModal').modal('hide');
            } else {
                $('#message3').removeClass('d-none');
                $('#message1').addClass('d-none');
                $('#message2').addClass('d-none');
                $('#exampleModal').modal('hide');
            }
        }, "json");
    });
    $("#save-get-failed").bind('click', function () {
        // Add the spinner to let them know we are loading
        $('#exampleModal').modal('show');
        $('.modal-title').text("Loading...");
        $('.modal-body').html("");
        $(".modal-body").append('<div class="d-flex justify-content-center">\
									<div class="spinner-border" role="status">\
									<span class="sr-only">Loading...</span>\
									</div>\
									</div>');
        hrrref = '/json?mode=getfailed';
        $.get(hrrref, function (data) {
            if (data['success'] === true) {
                $('.card-deck').html('');
                var size = Object.keys(data['results']).length;
                console.log("length = " + size);
                if (size > 0) {
                    $.each(data['results'], function (index, value) {
                        z = addJobItem(value);
                        $('.card-deck').append(z);
                    });
                    console.log(data)
                } else {
                    $("#message1 .alert-heading").html("I couldn't find any results for failed jobs");
                    $('#message1').removeClass('d-none');
                }
            } else {
                $('#message3').removeClass('d-none');
                $('#message1').addClass('d-none');
                $('#message2').addClass('d-none');
            }
            // Need to set as timeout because modal shows too slow for the ajax request to trigger its hide
            setTimeout(
                function () {
                    $('#exampleModal').modal("hide");
                },
                3000
            );
        }, "json");
    });
    $("#searchquery").on("keydown", function (event) {
        if (event.which == 13)
            $("#save-yes").click();
    });
    $("#save-yes").bind('click', function () {
        console.log(hrrref)
        // Check we have the searchquery element & it must be more than 3 chars
        if ($("input#searchquery").length) {
            var search_query = $("input#searchquery").val().length;
            if (search_query < 3) {
                $("#searchquery").addClass("is-invalid");
                return false;
            }
        }
        if (hrrref != "") {
            // Add the spinner to let them know we are loading
            $("#m-body").append('<div class="d-flex justify-content-center">\
										<div class="spinner-border" role="status">\
										<span class="sr-only">Loading...</span>\
										</div>\
										</div>');
            if (actionType === "search") {
                console.log("searching");
                console.log("q=" + $('#searchquery').val());
                hrrref = hrrref + $('#searchquery').val();
                console.log("href=" + hrrref);
            }
            if (hrrref === "entryWarn") {
                setCookie("understands", "yes", 66);
                $('#exampleModal').modal('toggle');
                $('#save-get-success').removeClass('d-none');
                $('#save-get-failed').removeClass('d-none');
                hrrref = "";
            }
            $.get(hrrref, function (data) {
                console.log(data['success']); // John
                console.log("#jobId" + activeJob)
                if (data['success'] === true) {
                    if (data['mode'] === "delete") {
                        $("#jobId" + activeJob).remove();
                        $("#message1 .alert-heading").html("Job was successfully deleted")
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
                    if (data['mode'] === "abandon") {
                        $("#status" + activeJob).attr("src", "static/img/fail.png")
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
                    if (data['mode'] === "logfile") {
                        $(this).find('.modal-title').text("Logfile")
                        $("#message1 .alert-heading").html("Here is the logfile you requested")
                        $('div .card-deck').html('<div class="bg-info card-header row no-gutters justify-content-center col-md-12 mx-auto">\
								<strong>' + data['job_title'] + '</strong></div><pre class="text-white bg-secondary"><code>' + data['log'] + '</code></pre>')
                        window.scrollTo({top: 0, behavior: 'smooth'});
                        $('#exampleModal').modal('toggle');
                        $('#message1').removeClass('d-none');
                        $('#message2').addClass('d-none');
                        $('#message3').addClass('d-none');
                    }
                    if (data['mode'] === "search") {
                        $(this).find('.modal-title').text("searching....")
                        $('.card-deck').html('')
                        var size = Object.keys(data['results']).length;
                        console.log("length = " + size);
                        if (size > 0) {
                            $.each(data['results'], function (index, value) {
                                z = addJobItem(value)
                                $('.card-deck').append(z);
                            });
                            console.log(data)
                            $("#message1 .alert-heading").html("Here are the jobs i found matching your query")
                            $('#m-body').addClass('bd-example-modal-lg')
                            $('#m-body').modal('handleUpdate')
                            $('#exampleModal').modal('toggle');
                            $('#message1').removeClass('d-none').removeClass('alert-danger').addClass('alert-success');
                            ;
                            $('#message2').addClass('d-none');
                            $('#message3').addClass('d-none');
                        } else {
                            $("#message1 .alert-heading").html("I couldnt find any results matching that title")
                            $('#message1').removeClass('d-none').removeClass('alert-success').addClass('alert-danger');
                            $('#exampleModal').modal('toggle');
                        }
                    }
                    if (data['mode'] === "fixperms") {
                        $("#jobId" + activeJob).addClass("alert-success")
                        $("#message1 .alert-heading").html("Permissions fixed")
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

    //Simple function to check if we have already agreed
    function checkCookie() {
        var understands = getCookie("understands");
        if (understands != "" && understands != null) {
            return true;
        } else {
            return null;
        }
    }

    //Get only the understands cookie
    function getCookie(cname) {
        var name = cname + "=";
        var decodedCookie = decodeURIComponent(document.cookie);
        var ca = decodedCookie.split(';');
        for (var i = 0; i < ca.length; i++) {
            var c = ca[i];
            while (c.charAt(0) == ' ') {
                c = c.substring(1);
            }
            if (c.indexOf(name) == 0) {
                return c.substring(name.length, c.length);
            }
        }
    }

    //Set out cookie so we dont need the dialog popping up
    function setCookie(cname, cvalue, exdays) {
        var d = new Date();
        d.setTime(d.getTime() + (exdays * 24 * 60 * 60 * 1000));
        var expires = "expires=" + d.toUTCString();
        document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
    }

    $('#exampleModal').on('show.bs.modal', function (event) {
        var button = $(event.relatedTarget) // Button that triggered the modal
        actionType = button.data('type') // Extract info from data-* attributes
        hrrref = button.data('href')
        activeJob = button.data('jobid')
        console.log(hrrref)
        console.log(activeJob)
        console.log(actionType)

        if (actionType === "abandon") {
            var modalTitle = "Abandon This Job ?"
            var modalBody = "This item will be set to abandoned. You cannot set it back to active! Are you sure?"
        } else if (actionType === "delete") {
            var modalTitle = "Delete this job forever ?"
            var modalBody = "This item will be permanently deleted and cannot be recovered. Are you sure?"
        } else if (actionType === "search") {
            var modalTitle = "Search the database"
            var modalBody = '<div class="input-group mb-3">' +
                '<div class="input-group-prepend">' +
                '<span class="input-group-text" id="searchlabel">Search </span>' +
                '</div>' +
                '<input type="text" class="form-control" id="searchquery" aria-label="searchquery" name="searchquery" placeholder="Search...." value="" aria-describedby="searchlabel">' +
                '<div id="validationServer03Feedback" class="invalid-feedback">Search string too short.</div>' +
                '</div>';
        } else if (actionType === "fixperms") {
            var modalTitle = "Fix Folder Permissions"
            var modalBody = "Sometimes ARM fails to set file owner and permissions, would you like ARM to try to fix it ?"
        } else {
            var modalTitle = "Do you want to leave this page ?"
            var modalBody = "To view the log file you need to leave this page. Would you like to leave ?"
        }
        var modal = $(this)
        modal.find('.modal-title').text(modalTitle)
        modal.find('.modal-body').html(modalBody)
        $("#searchquery").on("keydown", function (event) {
            if (event.which === 13)
                $("#save-yes").click();
        });
    })

    function addJobItem(job) {
        var idsplit = job.job_id.split("_");
        var x = '<div class="col-md-4" id="jobId' + job.job_id + '">' +
            '<div class="card mb-3  mx-auto" style="min-height: 420px;">' +
            '<div class="card-header row no-gutters justify-content-center">' +
            '<strong id="jobId' + job.job_id + '_header">';
        if (job.title_manual !== "None") {
            x += job.title_manual + ' (' + job.year + ')';
        } else {
            x += job.title + ' (' + job.year + ')';
        }
        x += '</strong>' +
            '</div>' +
            '<div class="row no-gutters">' +
            '<div class="col-lg-4">' +
            '<a href="jobdetail?job_id=' + idsplit[1] + '">';
        // TODO: Fix above to link the correct server - for now it links to the main server
        if (job.poster_url !== "None" && job.poster_url !== "N/A") {
            x += '<img id="jobId' + job.job_id + '_poster_url" alt="poster img" src="' + job.poster_url + '" width="240px" class="img-thumbnail">';
        } else {
            x += '<img id="jobId' + job.job_id + '_poster_url" alt="poster img" src="/static/img/none.png" width="240px" class="img-thumbnail">';
        }
        x += '</a>' +
            '</div>' +
            '<div class="col-lg-4">' +
            '<div class="card-body px-1 py-1">';

        x += '<div id="jobId' + job.job_id + '_title"><b>' + job.title + '</b></div>';
        x += '<div id="jobId' + job.job_id + '_year"><b>Year: </b>' + job.year + '</div>';
        x += '<div id="jobId' + job.job_id + '_video_type"><b>Type: </b>' + job.video_type + '</div>';
        x += '<div id="jobId' + job.job_id + '_devpath"><b>Device: </b>' + job.devpath + '</div>';
        x += '<div><b>Status: </b><img id="jobId' + job.job_id + '_status" src="static/img/' + job.status + '.png" height="20px" alt="' + job.status + '" title="' + job.status + '"></div>';

        x += '<div id="jobId' + job.job_id + '_progress_section">';
        if (job.status === "transcoding" && job.stage !== '' && job.progress) {
            x += '<div id="jobId' + job.job_id + '_stage"><b>Stage: </b>' + job.stage + '</div>';
            x += '<div id="jobId' + job.job_id + '_progress" >';
            x += '<div class="progress">' +
                '<div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" aria-valuenow="' + job.progress_round + '" aria-valuemin="0" aria-valuemax="100" style="width: ' + job.progress_round + '%">' +
                '<small class="justify-content-center d-flex position-absolute w-100">' + job.progress + '%</small>' +
                '</div>' +
                '</div>' +
                '</div>' +
                '<div id="jobId' + job.job_id + '_eta"><b>ETA: </b>' + job.eta + '</div>';
        }
        x += '</div>' +
            '</div>' +
            '</div>' +
            '<div class="col-lg-4">' +
            '<div class="card-body px-1 py-1">';

        x += '<div id="jobId' + job.job_id + '_RIPPER"><b>Ripper: </b>' + (job.ripper ? job.ripper : (idsplit[0] === "0" ? "Local" : "")) + '</div>';
        x += '<div id="jobId' + job.job_id + '_RIPMETHOD"><b>Rip Method: </b>' + job.config.RIPMETHOD + '</div>';
        x += '<div id="jobId' + job.job_id + '_MAINFEATURE"><b>Main Feature: </b>' + job.config.MAINFEATURE + '</div>';
        x += '<div id="jobId' + job.job_id + '_MINLENGTH"><b>Min Length: </b>' + job.config.MINLENGTH + '</div>';
        x += '<div id="jobId' + job.job_id + '_MAXLENGTH"><b>Max Length: </b>' + job.config.MAXLENGTH + '</div>';

        x += '</div>' +
            '<div class="card-body px-2 py-1">' +
            '<div class="btn-group-vertical" role="group" aria-label="buttons" ' + (idsplit[0] !== '0' ? 'style="display: none;"' : '') + '>' +
            '<button type="button" class="btn btn-primary" data-toggle="modal" data-target="#exampleModal" data-type="abandon" data-jobid="' + idsplit[1] + '" data-href="json?job=' + idsplit[1] + '&mode=abandon">Abandon Job</button>' +
            '<a href="logs?logfile=' + job.logfile + '&mode=full" class="btn btn-primary">View logfile</a>';
        if (job.video_type !== "Music") {
            x += '<a href="titlesearch?job_id=' + idsplit[1] + '" class="btn btn-primary">Title Search</a>' +
                '<a href="customTitle?job_id=' + idsplit[1] + '" class="btn btn-primary">Custom Title</a>' +
                '<a href="changeparams?config_id=' + idsplit[1] + '" class="btn btn-primary">Edit Settings</a>';
        }
        x += '</div>' +
            '</div>' +
            '</div>' +
            '</div>' +
            '</div>' +
            '</div></div>';
        return x;
    }
});