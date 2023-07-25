<template>
  <tr>
    <th scope="row" class="text-wrap">
      <router-link :to="'job-details/'+ job.job_id">{{ job.title }}</router-link>
    </th>
    <td>{{ job.start_time }}</td>
    <td class="hidden">{{ job.start_time }}</td>
    <td>{{ job.job_length }}</td>
    <td class="{{ job.status }}"><img v-bind:src="'/src/assets/img/'+ job.status +'.png'"
                                      height="30px"
                                      width="30px" alt="{{ job.status }}"
                                      title="{{ job.status }}"></td>
    <td>
      <router-link :to="'logs/'+ job.logfile + '/full/' + job.job_id">{{ job.logfile }}</router-link>
    </td>
  </tr>
</template>
<script setup>
defineProps({
  job: {
    type: Object,
    required: true
  }
})
</script>
<style>
/*
Max width before this PARTICULAR table gets nasty
This query will take effect for any screen smaller than 760px
and also iPads specifically.
*/
@media only screen and (max-width: 760px),
(min-device-width: 768px) and (max-device-width: 1024px) {
  /*
  Label the data
  */
  td:nth-of-type(1):before {
    content: "Job Start datetime:\A";
  }

  td:nth-of-type(2):before {
    content: "Duration:";
  }

  td:nth-of-type(2):after {
    content: " (h:mm:ss)";
  }

  td:nth-of-type(3):before {
    content: "Status:";
  }

  td:nth-of-type(4):before {
    content: "Logfile:\A";
  }
}

.hidden {
  display: none;
}
</style>