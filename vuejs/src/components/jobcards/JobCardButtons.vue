<script>
export default {
  name: 'JobCardButtons',
  emits: ['abandon', 'fixPerms'],
  props: {
    job: {},
    modalOpen: Boolean
  },
}
</script>
<template>
  <div class="btn-group job-buttons" role="group" aria-label="buttons">
    <a type="button" class="btn btn-primary" data-toggle="modal" data-target="#exampleModal"
       data-type="abandon" v-bind:data-jobid="job.job_id.split('_')[0]"
       v-bind:data-href="'json?job=' + job.job_id.split('_')[0] + '&mode=abandon'"
       v-on:click="$emit('abandon');console.log('Job Card emit')">Abandon Job
    </a>
    <router-link class="btn btn-primary" :to="'/logs/' + job.logfile + '/full/'+ job.job_id">View logfile</router-link>
    <router-link class="btn btn-primary" v-if="job.video_type !== 'Music'" :to="'titlesearch/'+ job.job_id.split('_')[0]">Title Search</router-link>
    <router-link class="btn btn-primary" v-if="job.video_type !== 'Music'" :to="'customTitle/'+ job.job_id.split('_')[0]">Custom Title</router-link>
    <router-link class="btn btn-primary" v-if="job.video_type !== 'Music'" :to="'changeparams/'+ job.job_id.split('_')[0]">Edit Settings</router-link>

    <a type="button" class="btn btn-primary" data-toggle="modal" data-target="#exampleModal"
       data-type="fixperms" v-on:click="$emit('fixPerms')"
       v-bind:data-jobid="job.job_id.split('_')[0]"
       v-bind:data-href="'json?mode=fixperms&job='+ job.job_id.split('_')[0]">Fix Permissions
    </a>
  </div>
</template>

<style scoped>
.job-buttons{
  position: inherit;
}
</style>