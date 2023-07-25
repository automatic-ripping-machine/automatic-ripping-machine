<template>
  <link rel="stylesheet" href="/src/assets/css/job-details.css">
  <div class="jumbotron m-5 mb-5">
    <div class="row">
      <div class="col-12">
        <div class="table-responsive">
          <div class="jumbotron">
              <HomeScreenGreeting msg2="" msg="A.R.M Rip History"/><br><br>
            <!-- PAGE NUMBERS -->
            <!-- Main Body -->
            <div class="row">
              <table class="table table-striped">
                <caption>Previous rips</caption>
                <thead class="tablesorterhead thead-dark">
                <tr style="margin: 0 auto">
                  <th scope="col" style="cursor: pointer;">Title</th>
                  <th scope="col" style="cursor: pointer;">Start Time</th>
                  <th scope="col" style="cursor: pointer;">Duration</th>
                  <th scope="col" style="cursor: pointer;">Status</th>
                  <th scope="col" style="cursor: pointer;">Logfile</th>
                </tr>
                </thead>
                <tbody>
                <HistoryLog v-for="job in joblist" :key="job.id" :job="job"/>
                </tbody>
              </table>
            </div>
            <!-- PAGE NUMBERS -->
          </div>
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
    content: "Job Start datetime:\A";
  }

  td:nth-of-type(2):before {
    content: "Duration:";
  }

  td:nth-of-type(2):after {
    content: " (h:mm:ss)";
  }

  td:nth-of-type(3):before {
    content: "Status:";
  }

  td:nth-of-type(4):before {
    content: "Logfile:\A";
  }
}

</style>

<script>
import HistoryLog from "@/components/HistoryLog.vue";
import axios from "axios";
import HomeScreenGreeting from "@/components/HomeScreenGreeting.vue";

export default {
  name: 'History',
  components: {
    HomeScreenGreeting,
    HistoryLog,
  },
  data() {
    return {
      message: "Ripping History",
      joblist: {},
      arm_API: this.armapi
    };
  },

  methods: {
    async getData() {
      try {
        const response = await axios.get(
            this.arm_API + "/json?mode=database"
        );
        // JSON responses are automatically parsed.
        this.joblist = response.data.results;
      } catch (error) {
        console.log(error);
      }
    },
  },

  created() {
    this.getData();
  },
}
</script>