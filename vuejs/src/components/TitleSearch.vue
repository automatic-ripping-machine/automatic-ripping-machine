<template>
  <div class="container justify-content-center jumbotron mt-5">
    <Modal v-show="currentLoading" title="Loading search..." v-bind:loadingContent="currentLoading"/>
    <div class="row justify-content-center" style="flex-wrap: nowrap">
      <HomeScreenGreeting msg="Search for Title" msg2="Search the api for correct title match"/>
    </div>
    <div class="row justify-content-center" style="flex-wrap: nowrap">
      <form ref="form" @submit.prevent="submit">
        <div class="input-group mb-3">
          <div class="input-group-prepend">
            <span class="input-group-text" id="searchtitle">Title</span>
          </div>
          <input type="text" class="form-control" aria-label="searchtitle" name="title"
                 v-bind:value="job.title" aria-describedby="searchtitle">
          <div class="invalid-tooltip">
            Search can't be blank
          </div>
          <div class="input-group-prepend">
            <span class="input-group-text" id="basic-addon1">Year</span>
          </div>
          <input type="text" class="form-control" name="year" v-bind:value="job.year"
                 aria-label="year" aria-describedby="basic-addon1">
        </div>
        <input class="form-control" name="mode" value="search_remote" hidden>
        <input class="form-control" name="job_id" v-bind:value="job.job_id" hidden>
        <button class="btn btn-info btn-lg btn-block" type="submit">Search</button>
      </form>
    </div>
    <br>
    <br>
    <div v-show="searchResults" class="row">
      <RemoteAPISearch :job="job" :results="results"/>
    </div>
  </div>
</template>

<script>

import HomeScreenGreeting from "@/components/HomeScreenGreeting.vue";
import {defineComponent, ref} from "vue";
import axios from "axios";
import RemoteAPISearch from "@/components/RemoteAPISearch.vue";
import Modal from "@/components/database/Modal.vue";

export default defineComponent({
  components: {Modal, RemoteAPISearch, HomeScreenGreeting},
  props: {
    job: {
      type: Object,
      required: true
    }
  },

  data() {
    return {
      job: {},
      results: ref(),
      searchResults: ref(false),
      currentLoading: ref(false),
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
        this.joblist = response.data.results;
      } catch (error) {
        console.log(error);
      }
    },
    submit: function () {
      this.currentLoading = true
      const formData = new FormData(this.$refs['form']); // reference to form element
      const data = {}; // need to convert it before using not with XMLHttpRequest
      let getURL = ""
      for (let [key, val] of formData.entries()) {
        Object.assign(data, { [key]: val })
        getURL += key + "=" + val + "&"
      }
      console.log(getURL);
      axios.get(this.arm_API + '/json?' + getURL , data)
          .then(res => this.search(res)).catch(
              error => console.log("error:"+ error),
          this.currentLoading = false)
    },
    search: function (response) {
      console.log(response.data.success)
      if(response.data.success){
        this.searchResults = true
        this.currentLoading = false
        this.job.title = response.data.title
        this.job.year = response.data.year
        this.results = response.data.search_results.Search
      }
    }
  },
  created() {
    this.getData(this.$route.params.job);
  },
})

</script>