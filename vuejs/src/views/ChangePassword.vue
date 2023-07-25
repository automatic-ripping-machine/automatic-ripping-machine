<script setup>

import HomeScreenGreeting from "@/components/HomeScreenGreeting.vue";
</script>

<template>
  <div class="container">
    <div class="row">
      <div class="col-12">
        <div class="table-responsive">
          <div class="jumbotron mt-5">
            <HomeScreenGreeting msg="Update The Admin Password" msg2=""/>
            <br>
        <form id="form1" name="form1" method="post" action="update_password">
          <div class="input-group mb-3">
            <div class="input-group-prepend">
              <span class="input-group-text" id="usr">Username:</span>
            </div>
            <input type="text" class="form-control" aria-label="username" name="username"
                   placeholder="username" value="user" aria-describedby="usr" readonly>
          </div>
          <div class="input-group mb-3">
            <div class="input-group-prepend">
              <span class="input-group-text" id="basic-addon1">Old Password:</span>
            </div>
            <input type="password" class="form-control" name="password" aria-label="password"
                   aria-describedby="basic-addon1">
          </div>

          <div class="input-group mb-3">
            <div class="input-group-prepend">
              <span class="input-group-text" id="basic-addon2">New Password:</span>
            </div>
            <input type="password" class="form-control" name="newpassword" aria-label="newpassword"
                   aria-describedby="basic-addon2">
          </div>
          <button class="btn btn-secondary btn-lg btn-block" form="form1" type="submit">
            Update User
          </button>
        </form>
          </div>
        </div>
      </div>
    </div>
    </div>
</template>

<style scoped>

</style>