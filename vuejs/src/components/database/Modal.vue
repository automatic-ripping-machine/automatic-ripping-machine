<template>
  <div class="modal" aria-labelledby="exampleModalCenterTitle"
       v-on:click="$emit('update-modal');console.log('Job Card emit')">
    <div class="modal-dialog modal-lg modal-dialog-centered" role="document" @click.stop="">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="exampleModalLongTitle">{{ title }}</h5>
          <button type="button" class="close" data-dismiss="modal" aria-label="Close"
                  v-on:click="$emit('update-modal');console.log('Job Card emit')">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div class="modal-body">
          <div v-show="error" class="alert alert-danger" role="alert">
            {{ errorMessage }}
          </div>
          <div class="input-group mb-3" v-if="mode==='search'">
            <div class="input-group-prepend">
              <span class="input-group-text" id="searchlabel">Search </span>
            </div>
            <input type="text" class="form-control" id="searchquery" aria-label="searchquery"
                   name="searchquery" placeholder="Search...." @keyup.enter="$emit('yes')"
                   @input="$emit('update:modelValue', $event.target.value)" :value="modelValue"
                   aria-describedby="searchlabel">
            <div id="validationServer03Feedback" class="invalid-feedback">
              Search string too short.
            </div>
          </div>
          <div v-else>
            {{ modalBody }}
          </div>
          <div v-if="loadingContent" class="d-flex justify-content-center">
            <div class="spinner-border" role="status"><span class="sr-only">Loading...</span></div>
          </div>
        </div>
        <div class="modal-footer">
          <button id="save-no" v-on:click="$emit('update-modal');console.log('Job Card emit')"
                  type="button" class="btn btn-secondary" data-dismiss="modal">No
          </button>
          <button id="save-yes" type="button" class="btn btn-primary" v-on:click="$emit('yes')">Yes</button>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
defineProps({
  title: {
    type: String,
    required: false
  },
  mode: {
    type: String,
    required: false
  },
  modalBody: {
    type: String,
    required: false
  },
  error: {
    type: Boolean,
    required: false
  },
  errorMessage: {
    type: String,
    required: false
  },
  modelValue: {
    type: String,
    required: false
  },
  loadingContent:{
    type: Boolean,
    required: false
  }
})
defineEmits(['update-modal', 'update:modelValue', 'yes'])
</script>
<style>
.modal {
  position: fixed;
  z-index: 1050;
  display: flex;
  background-color: rgba(0, 0, 0, 0.95);
}

.modal-content {
  z-index: 500000;
}
</style>