<template>
  <div id="message1" class="alert alert-success d-none" role="alert">
    <h4 class="alert-heading">Job was deleted successfully</h4>
  </div>
  <div id="message2" class="alert alert-danger text-center">
    <strong>WARNING: </strong>There is no undo here!
    <br>Be careful!
  </div>
  <div id="message3" class="alert alert-danger d-none" role="alert">
    <h4 class="alert-heading">There was a problem with your request</h4>
    <p>There was a problem with your request. Check the ARMui log for more details.</p>
  </div>
</template>
<script>
export default {
  name: 'Messages'
}
</script>
<style>
#message3, #message1 {
  float: left;
  position: fixed;
  z-index: 1000000000;
  top: 200px;
  left: 200px;
}
</style>