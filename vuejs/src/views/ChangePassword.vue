<script>

import HomeScreenGreeting from "@/components/HomeScreenGreeting.vue";
import {defineComponent} from "vue";
import axios from "axios";
import Messages from "@/components/database/Messages.vue";

export default defineComponent({
  components: {Messages, HomeScreenGreeting},
  data() {
    return {
      liveConfig: {
        username: "admin",
        old_password: "",
        new_password: ""
      },
      arm_API: this.armapi,
      wasError: false,
      message: ""
    };
  },

  methods: {
    submit: function () {
      this.liveConfig.username = "admin"
      if(this.liveConfig.new_password.length < 3){
        this.wasError = true
        this.message = "New password too short!"
        return false
      }
      if(this.liveConfig.old_password.length < 3){
        this.wasError = true
        this.message = "old password too short!"
        return false
      }
      this.liveConfig._method = 'PUT'
      axios.put(this.arm_API + "/settings/update_password", this.liveConfig)
          .then((response) => {
            console.log(response)
            if(response.data.success) {
              this.wasError = false
              this.message = ""
              alert("Password was updated!")
            }else{
              this.wasError = true
              this.message = response.data.error
            }
          }, (error) => {
            console.log(error);
          })
    }
  },
})


</script>

<template>
  <div class="container">
    <div class="row">
      <div class="col-12">
        <div class="table-responsive">
          <div class="jumbotron mt-5">
            <HomeScreenGreeting msg="Update The Admin Password" msg2=""/>

            <div v-show="wasError" class="alert alert-danger" role="alert">
              <h4 class="alert-heading">There was a problem with your request</h4>
              <p>{{ message }}</p>
            </div>

            <br>
        <form ref="form" @submit.prevent="submit">
          <div class="input-group mb-3">
            <div class="input-group-prepend">
              <span class="input-group-text" id="usr">Username:</span>
            </div>
            <input type="text" class="form-control" aria-label="username" name="username"
                   placeholder="admin" v-model="liveConfig.username" aria-describedby="usr" readonly>
          </div>
          <div class="input-group mb-3">
            <div class="input-group-prepend">
              <span class="input-group-text" id="basic-addon1">Old Password:</span>
            </div>
            <input type="password" class="form-control" name="password" aria-label="password"
                   aria-describedby="basic-addon1" v-model="liveConfig.old_password">
          </div>

          <div class="input-group mb-3">
            <div class="input-group-prepend">
              <span class="input-group-text" id="basic-addon2">New Password:</span>
            </div>
            <input type="password" class="form-control" name="newpassword" aria-label="newpassword"
                   aria-describedby="basic-addon2" v-model="liveConfig.new_password">
          </div>
          <button class="btn btn-primary btn-lg btn-block" type="submit">Submit
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