<script>
export default {
  name: 'JobCardButtons',
  emits: ['abandon', 'fixPerms'],
  props: {
    job: {},
    modalOpen: Boolean
  },
  methods: {
    splitId: function (id) {
      id = JSON.stringify(id)
      return id.split('_')[0]
    }
  }
}
</script>
<template>
  <div class="btn-group job-buttons" role="group" aria-label="buttons">
    <a type="button" class="btn btn-primary" data-toggle="modal" data-target="#exampleModal"
       data-type="abandon" v-bind:data-jobid="splitId(job.job_id)"
       v-bind:data-href="'json?job=' + splitId(job.job_id) + '&mode=abandon'"
       v-on:click="$emit('abandon');console.log('Job Card emit')">Abandon Job
    </a>
    <router-link class="btn btn-primary" :to="'/logs/' + job.logfile + '/full/'+ job.job_id">View logfile</router-link>
    <router-link class="btn btn-primary" v-if="job.video_type !== 'Music'" :to="'titlesearch/'+ splitId(job.job_id)">Title Search</router-link>
    <router-link class="btn btn-primary" v-if="job.video_type !== 'Music'" :to="'customTitle/'+ splitId(job.job_id)">Custom Title</router-link>
    <router-link class="btn btn-primary" v-if="job.video_type !== 'Music'" :to="'changeparams/'+ splitId(job.job_id)">Edit Settings</router-link>

    <a type="button" class="btn btn-primary" data-toggle="modal" data-target="#exampleModal"
       data-type="fixperms" v-on:click="$emit('fixPerms')"
       v-bind:data-jobid="splitId(job.job_id)"
       v-bind:data-href="'/jobs/'+ splitId(job.job_id) + '/fixperms'">Fix Permissions
    </a>
  </div>
</template>

<style scoped>
.job-buttons{
  position: inherit;
}
</style>