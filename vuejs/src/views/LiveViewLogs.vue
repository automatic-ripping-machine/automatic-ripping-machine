<script>
import axios from "axios";
import {ref} from "vue";

let fetchLog;
let job_id;
export default {
  components: {},
  props: ['file', 'mode', 'job'],

  data() {
    return {
      mode: String,
      job: String,
      job_title: ref("String"),
      jsonLog: ref("String"),
      arm_API: this.armapi
    };
  },

  methods: {
    async getData(logUrl, mode, job) {
      try {
        logUrl = this.arm_API + '/logs/'+ mode + '/' + logUrl + '/' + job;
        console.log(logUrl)
        let response = await axios.get(logUrl)
        // JSON responses are automatically parsed.
        this.job_title = response.data.job_title;
        this.escaped = response.data.escaped
        this.job_id = response.data.job
        this.jsonLog = response.data.log
      } catch (error) {
        console.log(error);
      }
    }
  },

  created() {
    this.getData(this.$route.params.file, this.$route.params.mode, this.$route.params.job);
    const file = this.$route.params.file
    const mode = this.$route.params.mode
    const job = this.$route.params.job
    if(mode === 'tail') {
      fetchLog = setInterval(() => {
        this.getData(file, mode, job, this);
        window.scrollTo(0, document.querySelector("#log").scrollHeight);
      }, 3000);
    }
  },
  unmounted() {
    clearInterval(fetchLog);
  }
};
</script>

<template>
  <div class="jumbotron m-5">
    <div class="container-fluid h-100 mx-auto">
      <div class="row">
        <div class="card-deck p-5">
          <div class="bg-info card-header row no-gutters justify-content-center col-md-12 mx-auto text-left">
            <strong class="text-left">{{ job_title }}</strong>
          </div>
          <pre class="text-left text-white bg-secondary col-md-12" id="log"><code>{{ jsonLog }}</code></pre>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
pre{
  white-space: pre-wrap;
  text-overflow: ellipsis;
  padding: 14px;
}
</style>