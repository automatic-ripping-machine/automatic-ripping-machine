<template>
  <tr v-for="file in files">
    <th scope="row" class="text-wrap">{{ file[0] }}</th>
    <td class="text-wrap">{{ file[2] }}</td>
    <td>{{ file[3] }}</td>
    <td><router-link :to="'/logs/' + file[0] + '/tail/JOB_ID'">tail</router-link></td>
    <td><router-link :to="'/logs/' + file[0] + '/armcat/JOB_ID'">arm</router-link></td>
    <td><router-link :to="'/logs/' + file[0] + '/full/JOB_ID'">full</router-link></td>
    <td><router-link :to="'/logreader?logfile=' + file[0] + '&mode=download'">download</router-link></td>
  </tr>
</template>
<script setup>
defineProps({
  files: {
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
    content: "Creation datetime:\A";
  }

  td:nth-of-type(2):before {
    content: "Size in kilobytes:\A";
  }

  td:nth-of-type(2):after {
    content: " Kb";
  }

  td:nth-of-type(3):before {
    content: "Log link Tail:";
  }

  td:nth-of-type(4):before {
    content: "Log link ARM:";
  }

  td:nth-of-type(5):before {
    content: "Log link Full:";
  }

  td:nth-of-type(6):before {
    content: "Log link Download:";
  }
}
</style>