<template>
  <div v-if="(job.status === 'transcoding' && job.stage !== '')" v-bind:id="'jobId' + job.job_id + '_progress_section'">
    <div v-bind:id="'jobId' + job.job_id + '_stage'">
      <strong>Stage: </strong>{{ job.stage }}</div>
    <div v-bind:id="'jobId' + job.job_id + '_progress'" >
      <div class="progress">
        <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar"
                                 v-bind:aria-valuenow="job.progress_round" aria-valuemin="0" aria-valuemax="100" v-bind:style="'width: '+ job.progress_round +'%'">
        <small class="justify-content-center d-flex position-absolute w-100">{{ job.progress }}%</small></div></div></div>
    <div v-bind:id="'jobId' + job.job_id + '_eta'"><strong>ETA: </strong> {{ job.eta }}</div>
  </div>
  <strong>Start Date:</strong> {{ job.start_time }}<br>
  <strong>Start Time:</strong> To be filled<br>
  <strong>Job Time:</strong> {{ job.job_length === undefined ? "Ongoing" : job.job_length }} <br>
</template>
<script>

export default {
  name: 'TranscodingStatus',
  props: {
    job: {}
  }
}
</script>
<style>
.progress-bar{
  background-color: #1b6eca;
  box-shadow: 2px 2px 5px rgb(0, 0, 0) inset;
}
.progress{
  background-color: #6c757d;
  box-shadow: 2px 2px 5px rgb(0, 0, 0) inset;

}
</style>