<script>
import HomeScreenGreeting from "@/components/HomeScreenGreeting.vue";
import axios from "axios";
import {ref} from "vue";

// @ is an alias to /src
export default {
  name: 'Send To API',
  components: {
    HomeScreenGreeting
  },
  data() {
    return {
      arm_API: this.armapi,
      loading: ref(false),
      job_list: ref(),
      message: ""
    };
  },
  methods: {
    update(){
      this.loading = !this.loading
      axios
          .get(this.arm_API + '/list/dvds').then((response) => {
        console.log(response.data);
        this.message = response.status
        this.job_list = response.data
        if(response.data === null || response.data.length <1){
          console.log("None found!")
          this.message = "No dvds are able to be sent!"
          this.loading = !this.loading

        }
      }, (error) => {
        console.log("Error!");
        console.log(error);
      });
      return this.files
    }
  }
}
</script>

<template>
  <div class="jumbotron alert-info m-5 p-5">
    <div class="row h-100 mx-auto align-items-center">
      <div class="col text-center" style="flex-wrap: nowrap">
        <HomeScreenGreeting v-bind:msg2="message" msg="Send to remote database"/>
        <p> To use this form you will need an API key for the ARM db.
          You can get one for free from <a href="https://1337server.pythonanywhere.com/request/key">here</a>.
          <br>You will need to add the API key to your arm settings page
        </p>
        <p>By clicking "I understand" you agree to submitting all dvd entries from your own personal database to the ARM
          API.
          <br>
          No personal information is tracked, only the dvd's crc64, Title, Year, imdb id, hasnicetitle and the disc
          label
          <br>
          These are used to help others more easily identify dvds without the need for an external api or any user
          input.</p>
        <form>
          <input class="form-control" name="s" value="1" hidden>
          <button class="btn btn-secondary btn-lg btn-block" form="form1" type="submit" @click.prevent="update">I understand</button>
        </form>
      </div>
    </div>

    <div class="jumbotron mb-5" v-show="loading">
        <div class="row h-100 mx-auto align-items-center">
          <div class="col-sm-12 mx-auto">
            <h5 class="text-center"><strong>These are the movies we tried to send to the ARM API</strong></h5>
          </div>
        </div>
        <div class="row">
          <div class="loading-spinner">
            <div class="d-flex justify-content-center">
              <div class="spinner-border" role="status"><span class="sr-only"></span></div>
              <div id="currentTotal"></div>
            </div>
          </div>
          <div class="col-md-12 mx-auto">
            <div class="card-deck">
            </div>
          </div>
        </div>
      </div>
    </div>
</template>

<style>
@media only screen and (max-width: 1000px) {
.jumbotron{
  margin-top: 10rem !important;
}}
</style>