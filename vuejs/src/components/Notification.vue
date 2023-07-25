<script setup>
defineProps({
  notes: {
    type: Object,
    required: false
  }
})
defineEmits(['seenNote'])

</script>
<template>
  <div class="main-notes">
    <div v-for="note in notes">
      <div class="toast show m-3" role="alert" aria-live="assertive"
           aria-atomic="true" data-autohide="true" data-animation="true" style="z-index:1000">
        <div class="toast-header">
          <img src="/src/assets/img/success.png" class="rounded mr-2" alt="arm message" height="20px" width="20px">
          <strong class="mr-auto">{{ note.title }} </strong>
          <small class="text-muted"> {{ note.trigger_time }}</small>
          <button type="button" class="ml-2 mb-1 close" data-dismiss="toast" aria-label="Close"
                  @click="$emit('seenNote', note.id); console.log('Note id=' + note.id)">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div class="toast-body">
          {{ note.message }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.main-notes{
  position: fixed;
  top: 10%;
  right: 10%;
  z-index: 1000;
}
.toast.show{
  border-color: rgb(161, 70, 70);
  box-shadow: 0 0 10px 2px rgb(217, 39, 66);
}
</style>