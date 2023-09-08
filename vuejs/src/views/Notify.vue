<template>
  <div v-for="notification in notes" class="card m-1 mt-3">
    <div class="card-body" :class="{ 'alert-danger': !notification.seen }">
      <h5 class="card-title"><b> {{ notification.title }}</b></h5>
      <h6 class="card-subtitle mb-2 text-muted">{{ notification.diff_time }}({{
        notification.trigger_time }})</h6>
      <p class="card-text"> {{ notification.message }}</p>
    </div>
  </div>
</template>
<script>
export default {
  name: 'Notify',
  props: {
    notes: {
      type: Object,
      required: true
    }
  }
}
</script>