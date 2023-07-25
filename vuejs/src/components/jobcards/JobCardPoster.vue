<template>
  <div class="col-lg-4 poster">
    <router-link :to="{ name: 'job details', params: { job_id: job.job_id } }">
      <img v-if="job.poster_url" v-bind:id="`jobId`+ job.job_id + '_poster_url'" alt="poster img"
           v-bind:src="job.poster_url" width="240px" class="img-thumbnail">
      <img v-else v-bind:id="`jobId`+ job.job_id + '_poster_url'"
           alt="poster img" src="/src/assets/img/none.png" width="240px" class="img-thumbnail">
    </router-link>
  </div>
</template>
<script>
import HomeIcon from "@/components/icons/Home.vue";

export default {
  name: 'JobCardPoster',
  components: {HomeIcon},
  props: {
    job: {}
  }
}
</script>
<style>
div.poster a img{
  width: 240px;
}
</style>