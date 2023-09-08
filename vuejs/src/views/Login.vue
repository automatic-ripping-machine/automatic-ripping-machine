<script>

import {defineComponent, ref} from "vue";
import HomeScreenGreeting from "@/components/HomeScreenGreeting.vue";
import axios from "axios";

export default defineComponent({
  components: {HomeScreenGreeting},
  data() {
    return {
      username: ref(""),
      password: ref(""),
      arm_API: this.armapi,
      access_token: this.access_token,
      error: false,
      errorMessage: ""
    }
  },
  methods:{
    submit: function () {
      console.log(this.username)
      console.log(this.password)
      let params = new URLSearchParams();
      params.append('username', this.username);
      params.append('password', this.password);
      axios.post(this.arm_API + '/token' , params)
          .then((response) => {
            console.log(response.data.access_token)
            axios.defaults.headers.common['Authorization']='Bearer ' + response.data.access_token;
            localStorage.setItem('token', JSON.stringify(response.data.access_token));
            this.error = false
            this.errorMessage = ""
             console.log(response)
           }
          ).catch((error) => {
            this.error = true
            this.errorMessage = error.message
            console.log("error:"+ error)
          })
    },
  }
})
</script>

<template>
  <div class="container">
    <div class="row">
      <div class="col-12">
        <div class="table-responsive">
          <div class="jumbotron mt-5">
            <HomeScreenGreeting msg="Login" msg2=""/>
            <br>
            <div v-show="error" class="alert alert-danger" role="alert">
              <h4 class="alert-heading">{{ errorMessage }}</h4>
            </div>
        <form ref="form" @submit.prevent="submit">
          <div class="input-group mb-3">
            <div class="input-group-prepend">
              <span class="input-group-text" id="usr">Username:</span>
            </div>
            <input type="text" class="form-control" placeholder="username" v-model="username"
                   aria-label="username" aria-describedby="usr">
          </div>
          <div class="input-group mb-3">
            <div class="input-group-prepend">
              <span class="input-group-text" id="basic-addon1">Password:</span>
            </div>
            <input type="password" class="form-control" name="password" placeholder="*******"  v-model="password"
                   aria-label="password" aria-describedby="basic-addon1">
          </div>
          <input class="form-control" name="save" value="save" hidden>
          <button class="btn btn-info btn-lg btn-block" type="submit">Search</button>
        </form>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>

</style>