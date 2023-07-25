<template>
  <div class="row">
    <div class="col">
      <strong>Ripper: </strong><p class="PG mr-4">{{ ripperName ? ripperName : 'Unknown Name' }}</p>

      <strong>Rip Method: </strong><p class="PG">{{ job.config.RIPMETHOD  }}</p>
    </div>
  </div>
    <div class="row">
      <div class="col">
        <strong>Main Feature: </strong><p class="PG mr-4">{{ job.config.MAINFEATURE }}</p>
        <strong>Min Length:</strong><p class="PG mr-4">{{ job.config.MINLENGTH  }}</p>
        <strong>Max Length: </strong><p class="PG">{{ job.config.MAXLENGTH }}</p>
      </div>
    </div>
</template>
<script>
export default {
  name: 'JobCardConfig',
  props: {
    job: {},
    ripperName: String
  }
}

</script>