<template>
  <div class="row d-flex justify-content-end">
    <div class="btn-group btn-group" style="padding: 1.96em !important;">
      <button id="save-get-success" type="button" class="btn btn-secondary btn-success" v-on:click="$emit('getSucc');" >Get all successful
        jobs
      </button>
      <button id="save-get-failed" type="button" class="btn btn-secondary btn-danger" v-on:click="$emit('getFail');">Get all failed jobs
      </button>
    </div>
  </div>
</template>
<script>
export default {
  name: 'Buttons',
  emits: ['update-modal', 'search', 'getSucc', 'getFail'],
}
</script>