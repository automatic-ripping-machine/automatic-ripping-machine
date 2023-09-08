<script>

import HomeScreenGreeting from "@/components/HomeScreenGreeting.vue";
import {defineComponent, ref} from "vue";
import axios from "axios";

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
      job: {},
      arm_API: this.armapi
    };
  },
  methods: {
    async getData(jobid) {
      try {
        const response = await axios.get(
            this.arm_API +"/jobs/" + jobid
        );
        // JSON responses are automatically parsed.
        console.log(response.data)
        this.job = response.data
        this.joblist = response.data.results;
      } catch (error) {
        console.log(error);
      }
    },
  },
  created() {
    this.getData(this.$route.params.job);
  },
})
</script>

<template>
  <div class="container justify-content-center m-auto jumbotron">
    <div class="col justify-content-center" style="flex-wrap: nowrap">
      <h1 class="alert-danger">This will not save</h1>
      <HomeScreenGreeting msg="Custom Title" msg2="This is intended for DVDs or for TV Series that have more than one disk"/>
    </div>
    <div class="row">
      <div class="justify-content-center m-auto">
        <form method="post">
          <div class="input-group mb-3 flex-nowrap">
            <div class="input-group-prepend">
              <span class="input-group-text" id="searchtitle">Title</span>
            </div>
            <input type="text" class="form-control" aria-label="searchtitle" name="title" placeholder="title..."
                   v-bind:value="job.title"
                   aria-describedby="searchtitle">
            <div class="invalid-tooltip">
              Title can't be blank
            </div>
          </div>
          <div class="input-group mb-3 flex-nowrap">
            <div class="input-group-prepend">
              <span class="input-group-text" id="basic-addon1">Year</span>
            </div>
            <input type="text" class="form-control" name="year" aria-label="year" v-bind:value="job.year" aria-describedby="basic-addon1">
          </div>
          <input class="form-control" name="job_id" v-bind:value="job.job_id" hidden>
          <button class="btn btn-info btn-lg btn-block" type="button" @click.prevent="update">Set Custom Title</button>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>

</style>