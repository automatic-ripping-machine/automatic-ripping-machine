<script>

import Modal from "@/components/database/Modal.vue";
import HomeScreenGreeting from "@/components/HomeScreenGreeting.vue";
import Messages from "@/components/database/Messages.vue";
import Buttons from "@/components/database/Buttons.vue";
import JobTemplate from "@/components/jobcards/JobTemplate.vue";
import axios from "axios";
import {ref} from "vue";

let joblist;
// @ is an alias to /src
export default {
  name: 'database',
  components: {
    JobTemplate,
    Modal,
    Messages,
    Buttons,
    HomeScreenGreeting
  },
  data() {
    return {
      message: "Joey does’t share food!",
      joblist: {},
      modalOpen: ref(false),
      modalBody: ref(false),
      mode: ref(false),
      currentJob: ref(),
      error: ref(),
      errorMessage: ref(),
      query: '',
      loadingContent: ref(false),
      arm_API: this.armapi
    };
  },
  mounted() {
    this.joblist = this.refreshJobs()
    this.message="First Loaded"
    console.log(this.message);
    this.$nextTick(() => {
      this.message =
          "No data yet....Loading please wait";
      console.log(this.message);
    });
  },
  methods: {
    update: function() {
      console.log("update fired")
      console.log(this.modalOpen)
      this.modalTitle = "Abandon Job"
      this.modalOpen = !this.modalOpen;
      console.log(this.modalOpen)
      this.error = false
      this.errorMessage = ""
    },
    abandon: function(job) {
      console.log("Abandon fired")
      console.log(this.modalOpen)
      console.log(job.job_id)
      this.currentJob = job.job_id
      this.modalTitle = "Abandon Job"
      this.mode = "abandon"
      this.modalBody = "This item will be set to abandoned. You cannot set it back to active! Are you sure?"
      this.modalOpen = !this.modalOpen;
      console.log(this.modalOpen)
    },
    search: function(query="") {
      this.query = query
      console.log(query)
      console.log(this.query)
      console.log("search fired")
      console.log(this.modalOpen)
      this.modalTitle = "Search for jobs..."
      this.modalBody = "Searching......."

      this.mode = "search"
      this.modalOpen = !this.modalOpen;
      console.log(this.modalOpen)
      this.yes()
    },
    getFail: function (){
      console.log("search fired")
      console.log(this.modalOpen)
      this.modalTitle = "Get all failed jobs ?"
      this.mode = "fail"
      this.modalBody = ""

      this.modalOpen = !this.modalOpen;
      console.log(this.modalOpen)
    },
    getSucc: function (){
      console.log("search fired")
      console.log(this.modalOpen)
      this.modalTitle = "Get all successful jobs ?"
      this.mode = "success"
      this.modalBody = ""
      this.modalOpen = !this.modalOpen;
      console.log(this.modalOpen)
    },
    fixPerms: function (job){
      console.log("Fix perms fired")
      console.log(this.modalOpen)
      console.log(job.job_id)
      this.currentJob = job.job_id
      this.modalTitle = "Try to fix this jobs folder permissions ?"
      this.mode = "fix_perms"
      this.modalBody = "This will try to set the chmod values from your arm.yaml. It wont always work, you may need to do this manually"
      this.modalOpen = !this.modalOpen;
      console.log(this.modalOpen)
    },
    yes:function (){
      // Send ping to mode with currentJob id
      let jobURl;
      console.log(this.currentJob)
      this.loadingContent = true
      console.log(this.mode)
      // Search has a diff query use that instead if we need
      if(this.mode === 'search'){
        console.log(this.query)
        jobURl = this.arm_API + '/jobs/search/'+ this.query
      }else if(this.mode === "abandon" || this.mode === "fix_perms"){
        jobURl = this.arm_API + '/jobs/' +this.currentJob + '/'+ this.mode
        console.log(jobURl)
      } else {
        jobURl = this.arm_API + '/database/?mode=' + this.mode
      }
      axios
          .get(jobURl).then((response) => {
        console.log(response.data);
        // Update joblist if we have new list and then close modal
        if(response.data.results){
          this.joblist = response.data.results
          this.update()
        }
        // If we ran into a problem show the error and keep modal open
        if(response.data.Error || !response.data.success){
          this.error = true
          this.errorMessage = response.data.Error ? response.data.Error: "An unknown error occurred!"
        }
      }, (error) => {
        console.log(error);
      });
      this.loadingContent = false
    },
    refreshJobs: function (){
      console.log("Timer" + Math.floor(Math.random() * (25)) + 1)
      axios
          .get(this.arm_API+ '/database').then((response) => {
        console.log(response.data);
        this.message = response.status
        console.log(response.data.data)
        this.joblist = response.data.results
        joblist = JSON.parse(JSON.stringify(this.joblist))
        console.log(JSON.parse(JSON.stringify(this.joblist)));
      }, (error) => {
        console.log("Error!");
        console.log(error.response);
      });
      //.then(response => (messageContainer.message = response))
      return this.joblist
    },
  }
}
</script>

<template>
  <div class="jumbotron m-5 mb-5">
    <!-- Header image -->
    <br>
    <HomeScreenGreeting msg="Database Entries" msg2=""/>
    <!-- Modal -->
    <Modal v-show="modalOpen" v-bind:title="modalTitle" v-bind:mode="mode" v-bind:errorMessage="errorMessage"
           v-bind:loadingContent="loadingContent"
           v-bind:modalBody="modalBody" v-on:update-modal="update" v-on:yes="yes" v-bind:error="error"/>
    <!-- Messages -->
    <Messages/>
    <div class="input-group mb-3">
      <input type="text" class="form-control mt-4 rounded-pill" aria-label="searchquery"
             name="searchquery" placeholder="Search...."
             aria-describedby="searchlabel" @keyup.enter="search(query)"
             v-model="query">
    <Buttons v-on:update-modal="update" v-on:search="search"
             v-on:getFail="getFail" v-on:getSucc="getSucc"/>
    </div>
    <!--PAGINATION-->

    <!-- All jobs -->
    <div class="container-fluid p-4">
    <div class="row align-items-center p-4">
      <div class="col-md-12 mx-auto">
        <div id="joblist" class="card-deck d-flex justify-content-center">
          <JobTemplate v-bind:joblist="joblist" v-on:update-modal="update"
                       v-on:abandon="abandon" v-on:fixPerms="fixPerms"/>
        </div>
    </div>
    </div>
    </div>
  </div>
  <!--PAGINATION-->

</template>

<style>
.card{
  box-shadow: 7px 4px 6px #07070782;
}
.ribbon{
  position: absolute;
  padding: 0 3em;
  font-size: 0.9em;
  margin: 0 0 0 0;
  line-height: 2em;
  color: #e6e2c8;
  min-width: 264px;
  border-radius: 0 1.2em 0.156em 0;
  background: rgb(27, 110, 202);
  box-shadow: -1px 2px 3px rgba(0,0,0,0.5);
  text-overflow: ellipsis;
  max-width: min-content;
}
.PG {
   line-height: 1;
   font-size: 100%;
 }
</style>