<template>
  <link rel="stylesheet" href="/src/assets/css/job-details.css">
  <div class="container">
    <div class="row">
      <div class="col-12">
        <div class="table-responsive">
          <div class="jumbotron mt-5">
            <HomeScreenGreeting msg="A.R.M Logs" msg2=""/>
            <br>
            <div class="row">
              <table class="table table-striped table-hover">
                <caption>Log files in the log directory</caption>
                <thead class="thead-dark">
                <tr>
                  <th scope="col" style="cursor: pointer;">Log file</th>
                  <th scope="col" style="cursor: pointer;">Created Time</th>
                  <th scope="col" style="cursor: pointer;">Size(kb)</th>
                  <th scope="col" colspan="4" style="cursor: default;" class="text-center" data-sorter="false">View
                    modes
                  </th>
                </tr>
                </thead>
                <tbody>
                <ViewLogFiles v-bind:files="files"/>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- Explain -->
    <div class="align-items-center mt-2">
      <div class="card mx-auto">
        <div class="card-header d-flex justify-content-center">
          <strong>View Modes</strong>
        </div>
        <div class="d-flex justify-content-center">
          <p class="p-4" style="line-height: 20pt;">
            <strong>tail:</strong> Output to browser in real time. Similar to 'tail -f'<br/>
            <strong>arm:</strong> Static output of just the ARM log entries<br/>
            <strong>full:</strong> Static output of all of the log including MakeMKV and
            HandBrake<br/>
            <strong>download:</strong> Download the full log file<br/>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
<style>
/*
Max width before this PARTICULAR table gets nasty
This query will take effect for any screen smaller than 760px
and also iPads specifically.
*/
@media only screen and (max-width: 760px),
(min-device-width: 768px) and (max-device-width: 1024px) {

  /*
  Label the data
  */
  td:nth-of-type(1):before {
    content: "Creation datetime:\A";
  }

  td:nth-of-type(2):before {
    content: "Size in kilobytes:\A";
  }

  td:nth-of-type(2):after {
    content: " Kb";
  }

  td:nth-of-type(3):before {
    content: "Log link Tail:";
  }

  td:nth-of-type(4):before {
    content: "Log link ARM:";
  }

  td:nth-of-type(5):before {
    content: "Log link Full:";
  }

  td:nth-of-type(6):before {
    content: "Log link Download:";
  }
}
</style>
<script>
import HomeScreenGreeting from "@/components/HomeScreenGreeting.vue";
import axios from "axios";
import ViewLogFiles from "@/components/ViewLogFiles.vue";

// @ is an alias to /src
export default {
  name: 'viewLogs',
  components: {
    ViewLogFiles,
    HomeScreenGreeting
  },
  data() {
    return {
      message: "Joey does’t share food!",
      files: {},
      arm_API: this.armapi
    };
  },
  mounted() {
    this.files = this.refreshJobs()
    this.message="First Loaded"
    console.log(this.message);
    this.$nextTick(() => {
      this.message =
          "No data yet....Loading please wait";
      console.log(this.message);
    });
  },
  methods: {
    refreshJobs(){
      console.log("Timer" + Math.floor(Math.random() * (25)) + 1)
      axios
          .get(this.arm_API + '/logs').then((response) => {
        console.log(response.data);
        this.message = response.status
        console.log(response.data.results)
        this.files = response.data.files
        if(response.data.files === null){
          console.log("No files found!")
        }
        //console.log(JSON.parse(JSON.stringify(this.files)));
      }, (error) => {
        console.log("Error!");
        console.log(error);
      });
      return this.files
    }
  }
}
</script>