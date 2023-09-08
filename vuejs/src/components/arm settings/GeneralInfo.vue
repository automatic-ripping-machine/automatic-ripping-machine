<script>
import Drives from "@/components/arm settings/Drives.vue";
import axios from "axios";

export default {
  name: 'GeneralInfo',
  components: {
    Drives
  },
  data() {
    return {
      message: "Stats here",
      stats: {},
      drives: {},
      arm_API: this.armapi
    };
  },
  mounted() {
    this.stats = this.fetchStats()
    this.message = "First Loaded"
    console.log(this.message);
    this.$nextTick(() => {
      this.message =
          "No data yet....Loading please wait";
      console.log(this.message);
    });
  },
  methods:{
    fetchStats: function () {
      axios
          .get(this.arm_API + '/settings/stats').then((response) => {
        this.message = response.status
        console.log(response.data)
        this.stats = response.data.stats
        this.drives = response.data.drives
      }, (error) => {
        console.log("Error Getting Stats!");
        console.log(error);
      });
      return this.stats
    }
  }
}
</script>

<template>
  <div class="tab-pane active pt-5" id="home" role="tabpanel" aria-labelledby="home-tab">
    <div class="card-deck m-auto">
      <!--Left Card-->
      <div class="card">
        <div class="card-header">Server details</div>
        <div class="card-body col">
          <ul class="list-group list-group-flush">
            <li class="list-group-item">Python
              version: {{ stats.python_version }}
            </li>
            <li class="list-group-item">A.R.M
              version: {{ stats.arm_version }}
            </li>
            <li class="list-group-item">
              <label class="w-100">Current git version:<br>
                <input disabled v-bind:value="stats.git_commit"
                       class="form-control">
              </label></li>
            <li class="list-group-item">
              <!-- Update A.R.M -->
              <div v-if="stats.updated">
                <img src="/src/assets/img/success.png"
                                             alt="update image" width="20px" height="20px"> You are on the latest
                version
              </div>
              <div v-else>>Update Available:<img src="/src/assets/img/fail.png"
                               alt="update image" width="20px" height="20px">
                <form id="updateArm" name="updateArm" method="post" action="">
                  <button title="Update A.R.M Via git"
                          class="btn btn-primary float-right" type="submit">Update
                    A.R.M
                  </button>
                </form>
                New updates are available!
              </div>
            </li>
            <!-- Rip stats -->
            <li class="list-group-item">Total rips:
              <code>{{ stats['total_rips'] }}</code></li>
            <li class="list-group-item">Movies ripped:
              <code>{{ stats['movies_ripped'] }}</code></li>
            <li class="list-group-item">Series ripped:
              <code>{{ stats['series_ripped'] }}</code></li>
            <li class="list-group-item">Audios ripped:
              <code>{{ stats['cds_ripped'] }}</code></li>
          </ul>
        </div>
      </div>
      <!--Right Card-->
      <div class="card">
        <Drives v-bind:cddrives="drives"/>
      </div>
    </div>
  </div>

</template>

<style scoped>

</style>