<script setup>
defineProps({
  cddrives: {
    type: Object,
    required: true
  }
})
let formDrive;
</script>

<template>
  <div class="container content">
    <div class="row">
      <div class="col pt-3">
        <div class="card mx-auto">
          <div class="card-header text-center">
            <strong>Disk Drives</strong>
          </div>
          <ul class="list-group list-group-flush">
            {% if drives: %}
            <li v-for="cddrive in cddrives" class="list-group-item">
              <div class="container">
                <div class="row">
                  <div class="col">
                    <form id="systemForm" name="systemForm" action="/systeminfo" method="post">
<!--                      {% if formDrive: %}-->
<!--                      {{ formDrive.hidden_tag() }}-->
<!--                      {% endif %}-->
                      <div class="form-group row my-0">
                        <label class="col-sm-3 col-form-label px-1">Name</label>
                        <label class="col-sm col-form-label px-1">{{ cddrive.name }}</label>
                      </div>
                      <div class="form-group row my-0">
                        <label class="col-sm-3 col-form-label px-1">Type</label>
                        <label class="col-sm col-form-label px-1">{{ cddrive.type }}</label>
                      </div>
                      <div class="form-group row my-0">
                        <label class="col-sm-3 col-form-label px-1 px-1">Mount Path</label>
                        <label class="col-sm col-form-label px-1 small">{{ cddrive.mount }}</label>
                      </div>
                      <div class="form-group row my-0">
                        <label class="col-sm-3 col-form-label px-1">Current Job</label>
                        <div v-if="cddrive.job_current">
                        <label class="col-sm col-form-label px-1"><a
                            href="/jobdetail?job_id={{ cddrive.job_id_current }}">
                          {{ cddrive.job_current.video_type }} - {{ cddrive.job_current.title }} - {{
                            cddrive.job_current.year
                          }} </a></label>
                        </div>

                        <label v-else class="col-sm col-form-label px-1">No current job</label>
                      </div>
                      <div class="form-group row my-0">
                        <label class="col-sm-3 col-form-label px-1 px-1">Previous Job</label>
                        <label v-if="cddrive.job_id_previous" class="col-sm col-form-label px-1">
                          <a v-bind:href="'/jobdetail?job_id=' + cddrive.job_id_previous">
                            {{ cddrive.job_previous.video_type }} - {{ cddrive.job_previous.title }} -
                            {{ cddrive.job_previous.year }} </a></label>
                        <label v-else class="col-sm col-form-label px-1">N/A</label>
                      </div>
                      <div class="form-group row my-0">
                        <label for="driveDescription" class="col-sm-3 col-form-label px-1">Description</label>
                        <div class="col-sm">
                          <div v-if="formDrive">
                          <input class="form-control form-control-sm px-1" type="text" id="description"
                                 name="description" v-bind:value="cddrive.description">
                          <input type="hidden" id="id" name="id" v-bind:value="cddrive.drive_id">
                          </div>
                          <div v-else>
                          <!-- Drives form not defined, no editing available -->
                          <input class="form-control form-control-sm px-1" type="text" id="description"
                                 name="description" v-bind:value="cddrive.description" readonly>
                          <input type="hidden" id="id" name="id" v-bind:value="cddrive.drive_id">
                          </div>
                        </div>
                      </div>
                      <div class="form-group row my-0">
                        <div class="col">
                          <div v-if="formDrive" class="float-right">
                            <button type="submit" class="btn btn-primary btn-sm" name="submit">Update</button>
                            <button type="submit" class="btn btn-outline-danger btn-sm" name="remove">Remove</button>
                          </div>
                        </div>
                      </div>
                    </form>
                  </div>
                  <div class="col-2 d-flex">
                    <div class="row">
                      <a v-if="formDrive" href="#" class="my-0">Edit</a>
                    </div>
                    <div class="row">
                      <a v-if="cddrive.open" v-bind:href="'driveeject/'+ cddrive.drive_id">
                        <img src="/src/assets/img/drive-optical_open.svg" class="p-flex align-items-center"
                             style="max-width:100px; min-width:50px" alt="Drive Open">
                      </a>
                      <a v-else v-bind:href="'driveeject/'+ cddrive.drive_id">
                        <img src="/src/assets/img/drive-optical_closed.svg" class="p-flex align-items-center"
                             style="max-width:100px; min-width:50px" alt="Drive Closed">
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            </li>
            {% else %}
            <li class="list-group-item">
              No drives installed on this system.
            </li>
            {% endif %}
            <li class="list-group-item">
              <a href="systemdrivescan">Scan for Drives</a>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>

</template>

<style scoped>

</style>