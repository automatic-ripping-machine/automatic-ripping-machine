<script setup>
defineProps({
  server: {
    type: Object,
    required: true
  },
  serverutil: {
    type: Object,
    required: true
  },
  hwsupport: {
    type: Object,
    required: true
  }
})
</script>

<template>
  <div class="container content m-auto">
    <div class="row">
      <!-- System -->
      <div class="col pt-3">
        <div class="card mx-auto">
          <div class="card-header text-center">
            <strong>System</strong>
          </div>
          <ul class="list-group list-group-flush">
            <li class="list-group-item">
              Name: {{ server.name }}
            </li>
            <li class="list-group-item">
              {{ server.description }}
            </li>
            <li class="list-group-item">
              CPU: {{ server.cpu }}
            </li>
            <li class="list-group-item">
              <section v-if="serverutil.cpu_temp" v-bind:class="serverutil.cpu_temp">CPU
                Temp: {{ serverutil.cpu_temp }}&#176;C
              </section>
              <section v-else> Temp: not reported</section>
            </li>
            <li class="list-group-item">
              <h6 class="progress-label" style="float: left;margin-right: 1em;">Usage: </h6>
              <div class="progress">
                <div v-bind:class="'progress-bar ' + serverutil.cpu_util "
                     role="progressbar"
                     v-bind:style="'width: '+ serverutil.cpu_util + '%;'"
                     v-bind:aria-valuenow="serverutil.cpu_util" aria-valuemin="0" aria-valuemax="100">
                  <small class="justify-content-center d-flex position-absolute w-50">{{  serverutil.cpu_util }}%</small>
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>
      <!-- System Memory -->
      <div class="col pt-3">
        <div class="card mx-auto">
          <div class="card-header text-center">
            <strong>System Memory</strong>
          </div>
          <ul class="list-group list-group-flush">
            <li class="list-group-item">
              Total: {{ server.mem_total }} GB
              <br>Free: {{  serverutil.memory_free }} GB
              <br>Used: {{  serverutil.memory_used }} GB
            </li>
            <li class="list-group-item">
              <h6 class="progress-label" style="float: left;margin-right: 1em;">Usage: </h6>
              <div class="progress">
                <div v-bind:class="'progress-bar ' + serverutil.memory_percent "
                     role="progressbar"
                     v-bind:style="'width: '+ serverutil.memory_percent + '%;'"
                     v-bind:aria-valuenow="serverutil.memory_percent" aria-valuemin="0"
                     aria-valuemax="100">
                  <small class="justify-content-center d-flex position-absolute w-50">{{  serverutil.memory_percent }}%</small>
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>
      <!-- Storage -->
      <div class="col pt-3">
        <div class="card mx-auto">
          <div class="card-header text-center">
            <strong>Storage</strong>
          </div>
          <ul class="list-group list-group-flush">
            <li class="list-group-item">
              <div v-if="serverutil.storage_transcode_free">
              <h6 class="progress-label" style="float: left;margin-right: 1em;">Transcode: </h6>
              <div class="progress">
                <div v-bind:class="'progress-bar ' + serverutil.storage_transcode_percent "
                     role="progressbar"
                     v-bind:style="'width: ' + serverutil.storage_transcode_percent +'%;'"
                     aria-valuenow="{{  serverutil.storage_transcode_percent }}"
                     aria-valuemin="0"
                     aria-valuemax="100">
                  <small class="justify-content-center d-flex position-absolute w-50">{{  serverutil.storage_transcode_percent }}%</small>
                </div>
              </div>
              <br> Free Space: {{  serverutil.storage_completed_free }} GB
              </div>
              <div v-else>
              Transcode: Unable to get data on path
              </div>
              <br>Path: {{  server.arm_path }}
            </li>
            <li class="list-group-item">
              <div v-if="serverutil.storage_completed_free">
              <h6 class="progress-label" style="float: left;margin-right: 1em;">Completed: </h6>
              <div class="progress">
                <div v-bind:class="'progress-bar '+ serverutil.storage_completed_percent "
                     role="progressbar"
                     v-bind:style="'width: ' + serverutil.storage_completed_percent +'%;'"
                     aria-valuenow="{{  serverutil.storage_completed_percent }}"
                     aria-valuemin="0"
                     aria-valuemax="100">
                  <small class="justify-content-center d-flex position-absolute w-50">{{  serverutil.storage_completed_percent }}%</small>
                </div>
              </div>
              <br> Free Space: {{ serverutil.storage_completed_free }} GB
              </div>
              <div v-else>
              Completed: Unable to get data on path
              </div>
              <br>Path: {{ media_path }}
            </li>
          </ul>
        </div>
      </div>
    </div>
    <!-- HW Transcode support -->
    <div class="row">
      <div class="col pt-3"></div>
      <div class="col pt-3">
        <div class="card mx-auto">
          <div class="card-header text-center">
            <strong>HardWare Transcoding support</strong>
          </div>
          <ul class="list-group list-group-flush">
            <!-- INTEL -->
            <li class="list-group-item text-center">
              Intel QuickSync:
              <img v-if="hwsupport.intel" src="/src/assets/img/success.png"
                   alt="update image" width="20px" height="20px">
              <div v-else class="d-inline">
                <img src="/src/assets/img/fail.png"
                                             alt="update image" width="20px" height="20px">
                <a href="https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/"
                   target=”_blank”>
                  <img title="Get Help from the wiki!"
                       src="/src/assets/img/info.png" width="20px"
                       height="20px" alt="Get Help from the wiki!"></a></div>
            </li>
            <!-- NVIDIA -->
            <li class="list-group-item text-center">
              Nvidia NVENC:
              <img v-if="hwsupport.nvidia" src="/src/assets/img/success.png"
                   alt="update image" width="20px" height="20px">
              <div v-else class="d-inline">
                <img src="/src/assets/img/fail.png"
                     alt="update image" width="20px" height="20px">
                <a href="https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/"
                   target=”_blank”>
                  <img title="Get Help from the wiki!"
                       src="/src/assets/img/info.png" width="20px"
                       height="20px" alt="Get Help from the wiki!"></a></div>
            </li>
            <!-- AMD -->
            <li class="list-group-item text-center">
              AMD VCN:
              <img v-if="hwsupport.amd" src="/src/assets/img/success.png"
                                         alt="update image" width="20px" height="20px">
              <div v-else class="d-inline">
                <img src="/src/assets/img/fail.png"
                     alt="update image" width="20px" height="20px">
                <a href="https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/"
                   target=”_blank”>
                  <img title="Get Help from the wiki!"
                       src="/src/assets/img/info.png" width="20px"
                       height="20px" alt="Get Help from the wiki!"></a></div>
            </li>
          </ul>
        </div>
      </div>
      <div class="col pt-3"></div>
    </div>
  </div>
</template>

<style scoped>
.progress-bar {
  color: white !important;
  padding-top: 4px;
}
.card{
  color: #FFFFFF;
  background-color: rgb(27, 110, 202);
}
.card-header{
  background-color: rgb(27, 110, 202);
  color: transparent;
  text-shadow: 2px 1px 2px rgba(0,0,0,0.9);
  -webkit-background-clip: text;
  -moz-background-clip: text;
  background-clip: text;
  color: #f0f8fff7;
  font-size: 140%;
}
.card-header strong{
  background-color: #565656;
  color: transparent;
  text-shadow: 2px 1px 2px rgba(0,0,0,0.9);
  -webkit-background-clip: text;
  -moz-background-clip: text;
  background-clip: text;
  color: #f0f8fff7;
  font-size: 140%;
}
.list-group-item {
  background-color: #31353d;
}

</style>