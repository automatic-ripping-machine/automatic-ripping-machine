<template>
  <div class="container justify-content-center jumbotron mt-5">
    <Modal v-show="modalOpen" title="Loading search..." @update-modal="modalOpen=!modalOpen"/>
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
                 v-model="title" aria-describedby="searchtitle">
          <div class="invalid-tooltip">
            Search can't be blank
          </div>
          <div class="input-group-prepend">
            <span class="input-group-text" id="basic-addon1">Year</span>
          </div>
          <input type="text" class="form-control" name="year" v-model="year"
                 aria-label="year" aria-describedby="basic-addon1">
        </div>
        <input class="form-control" name="mode" value="search_remote" hidden>
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
      title: "",
      year: "",
      modalOpen: ref(false),
      results: ref(),
      searchResults: false,
      currentLoading: ref(false),
      arm_API: this.armapi
    };
  },
  methods: {
    async getData(jobid) {
      try {
        const response = await axios.get(
            this.arm_API + "/jobs/" + jobid
        );
        // JSON responses are automatically parsed.
        this.job = response.data
        this.title = response.data.title
        this.year = response.data.year
      } catch (error) {
        console.log(error);
      }
    },
    submit: function () {
      // Open the modal to show that data is being loaded
      this.modalOpen = !this.modalOpen;
      // Add the year as null, so it doesn't cause the api to error out
      this.year = (this.year == null || this.year === "") ? 'null' : this.year
      axios.get(this.arm_API + '/search_remote/' + this.title + "/" + this.year+ "/" + this.job.job_id)
          .then(res => this.search(res),this.modalOpen = !this.modalOpen).catch(
              error => console.log("error:"+ error),
              this.modalOpen = !this.modalOpen
       )
    },
    search: function (response) {
      console.log(response.data)
      if(response.data.success){
        this.searchResults = true
        this.currentLoading = false
        this.job.title = response.data.title
        this.job.year = response.data.year
        this.results = response.data.search_results.Search
        // Only close the modal when we have results
        if(this.results){
          this.modalOpen = !this.modalOpen
        }
      }
    }
  },
  created() {
    this.getData(this.$route.params.job);
  },
})

</script>