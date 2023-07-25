<script>

import HomeScreenGreeting from "@/components/HomeScreenGreeting.vue";
import {defineComponent, ref} from "vue";
import axios from "axios";

let job;
export default defineComponent({
  components: {HomeScreenGreeting},
  props: {
    job: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      job: ref(),
      arm_API: this.armapi
    };
  },
  methods: {
    async getData(jobid) {
      try {
        const response = await axios.get(
            this.arm_API + "/json?mode=get_job_details&job_id=" + jobid
        );
        // JSON responses are automatically parsed.
        console.log(response.data)
        this.job = response.data.jobs
        this.config = response.data.jobs.config;
        // Convert python bool string into js bool
        this.config.MAINFEATURE = this.config.MAINFEATURE === "False" ? false: true;
      } catch (error) {
        console.log(error);
      }
    },
    submit: function () {
      const formData = new FormData(this.$refs['form']); // reference to form element
      const data = {}; // need to convert it before using not with XMLHttpRequest
      let getURL = ""
      for (let [key, val] of formData.entries()) {
        Object.assign(data, { [key]: val })
        getURL += key + "=" + val + "&"
      }
      // If MAINFEATURE doesn't exist set it to false
      data['MAINFEATURE'] = !data['MAINFEATURE'] ? false : true;
      console.log(getURL);
      axios.get(this.arm_API + '/json?' + getURL + '&MAINFEATURE=' + data['MAINFEATURE'], data)
          .then(res => console.log(res.request.response))
    }
  },
  created() {
    this.job = {'config': {}}
    this.getData(this.$route.params.job);
  },
})
</script>

<template>
  <div class="container justify-content-center jumbotron m-auto">
    <div class="col justify-content-center" style="flex-wrap: nowrap">
      <HomeScreenGreeting msg="Change Job Parameters" msg2=""/>
    </div>
    <div class="row justify-content-center" style="flex-wrap: nowrap">
      <div class="col-7">
        <form ref="form" @submit.prevent="submit">
          <!-- RIPMETHOD -->
          <div class="input-group mb-3 flex-nowrap">
            <div class="input-group mb-3">
              <div class="input-group-prepend">
                <label class="input-group-text" for="inputGroupSelect01">Rip Method: </label>
              </div>
              <select class="custom-select" v-model="job.config.RIPMETHOD" name="RIPMETHOD">
                <option selected>Choose...</option>
                <option value="mkv">mkv</option>
                <option value="backup">backup</option>
              </select>
            </div>

          </div>
          <!-- disctype -->
          <div class="input-group mb-3 flex-nowrap">
            <div class="input-group mb-3">
              <div class="input-group-prepend">
                <label class="input-group-text" for="inputGroupSelect01">Disc Type: </label>
              </div>
              <select class="custom-select" v-model="job.disctype" name="DISCTYPE">
                <option selected>Choose...</option>
                <option value="dvd">Dvd</option>
                <option value="bluray">Blu-ray</option>
                <option value="music">Music</option>
                <option value="data">Data</option>
              </select>
            </div>
          </div>
          <!-- MAINFEATURE -->
          <div class="input-group mb-3 flex-nowrap">
            <div class="input-group mb-3">
              <div class="input-group-append w-100">
                <span class="input-group-text">
                  <label for="MAINFEATURE">Main Feature: {{ job.config.MAINFEATURE }} </label></span>
                <div class="input-group-text w-100">
                  <input class="switch" v-model="job.config.MAINFEATURE" name="MAINFEATURE"
                         type="checkbox" v-bind:checked="job.config.MAINFEATURE">
                </div>
              </div>
            </div>
          </div>
          <!-- MINLENGTH -->
          <div class="input-group mb-3 flex-nowrap">
            <div class="input-group input-group-sm mb-3">
              <div class="input-group-prepend">
                <span class="input-group-text" id="inputGroup-sizing-sm">Minimum Length: </span>
              </div>
              <input type="text" class="form-control" v-bind:value="job.config.MINLENGTH" name="MINLENGTH"
                     aria-label="Sizing example input" aria-describedby="inputGroup-sizing-sm">
            </div>

            <div class="invalid-tooltip" id="MINLENGTH_INVALID">
              errors
            </div>
          </div>
          <!-- MAXLENGTH -->
          <div class="input-group mb-3 flex-nowrap">
            <div class="input-group input-group-sm mb-3">
              <div class="input-group-prepend">
                <span class="input-group-text" id="inputGroup-sizing-sm">Maximum Length: </span>
              </div>
              <input type="text" class="form-control" v-bind:value="job.config.MAXLENGTH" name="MAXLENGTH"
                     aria-label="Sizing example input" aria-describedby="inputGroup-sizing-sm">
            </div>

            <div id="MAXLENGTH_INVALID" class="invalid-tooltip">
              Title can't be blank
            </div>
          </div>

          <input name="mode" value="change_job_params" hidden>
          <input name="config_id" v-bind:value="job.job_id" hidden>
          <button class="btn btn-info btn-lg btn-block" type="submit">Submit</button>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
div input {
  display: block;
  width: 100%;
  height: initial;
  padding: .375rem .75rem;
  font-size: 1rem;
  font-weight: 400;
  line-height: 1.5;
  color: #495057;
  background-color: #fff;
  background-clip: padding-box;
  border: 1px solid #ced4da;
  -webkit-border-top-right-radius: 3px;
  -webkit-border-bottom-right-radius: 3px;
  -moz-border-radius-topright: 3px;
  -moz-border-radius-bottomright: 3px;
  border-top-right-radius: 3px;
  border-bottom-right-radius: 3px;
  transition: border-color .15s ease-in-out, box-shadow .15s ease-in-out;
}

div.input-group input, div.input-group select {
  position: relative;
  -ms-flex: 1 1 auto;
  flex: 1 1 auto;
  width: 1%;
  min-width: 0;
  margin-bottom: 0;
  display: block;
  padding: .375rem .75rem;
  font-size: 1rem;
  font-weight: 400;
  line-height: 1.5;
  color: #495057;
  background-color: #fff;
  background-clip: padding-box;
  border: 1px solid #ced4da;
  transition: border-color .15s ease-in-out, box-shadow .15s ease-in-out;
}
</style>