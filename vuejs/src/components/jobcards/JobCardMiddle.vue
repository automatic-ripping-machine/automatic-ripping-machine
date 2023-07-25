<template>
  <div class="col-lg-4">
    <div class="card-body px-1 py-1">
      <div v-bind:id="'jobId' + job.job_id + '_year'"><strong>Year: </strong>{{ job.year }}</div>
      <div v-bind:id="'jobId' + job.job_id + '_video_type'"><strong>Type: </strong>{{ job.video_type }}</div>
      <div v-bind:id="'jobId' + job.job_id + '_devpath'"><strong>Device: </strong>{{ job.devpath }}</div>
      <div><strong>Status: </strong>
        <img v-bind:id="'jobId' + job.job_id + '_status'"
             v-bind:src="'/src/assets/img/' + job.status + '.png'"
             v-bind:alt="''+job.status + ''"
             v-bind:title="''+job.status+ ''">
      </div>
      <TranscodingStatus :job="job"/>
    </div>
  </div>
</template>
<script>
import TranscodingStatus from "@/components/jobcards/TranscodingStatus.vue";

export default {
  name: 'JobCardMiddle',
  components: {TranscodingStatus},
  props: {
    job: {}
  }
}
</script>