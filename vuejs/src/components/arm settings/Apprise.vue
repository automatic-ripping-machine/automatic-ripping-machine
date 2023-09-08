<script>
import axios from "axios";
import HomeScreenGreeting from "@/components/HomeScreenGreeting.vue";

export default {
  components: {HomeScreenGreeting},
  data() {
    return {
      liveConfig: [],
      jsoncomments: [],
      arm_API: this.armapi
    };
  },

  methods: {
    async getData() {
      try {
        const response = await axios.get(
            this.arm_API + "/settings/get_apprise"
        );
        // JSON responses are automatically parsed.
        this.liveConfig = response.data.cfg;
        this.jsoncomments = response.data.comments
      } catch (error) {
        console.log(error);
      }
    },//save_apprise_cfg
    submit: function () {
      this.liveConfig._method = 'PUT'
      axios.put(this.arm_API + "/settings/get_apprise", this.liveConfig)
          .then((data) => {
            console.log(data)
          }, (error) => {
            console.log(error);
          })
    }
  },

  created() {
    this.getData();
  },
};
</script>
<template>
  <div class="container">
    <div class="row">
      <div class="col-12">
        <div class="table-responsive">
          <div class="jumbotron mt-5">
            <HomeScreenGreeting msg="Apprise Settings" msg2=""/>
            <br>
            <form ref="form" @submit.prevent="submit">
              <div v-for="(v, k) in liveConfig" key="index" class="input-group mb-3">
                <div class="input-group-prepend">
                  <span class="input-group-text" v-bind:id="k">{{ k }}: </span>
                </div>
                <input type="text" class="form-control" v-bind:aria-label="k" v-model="liveConfig[k]">
                <div class="input-group-append">
                  <span class="input-group-text" id="basic-addon2">
                <a class="popovers" onClick='return false;' href=""
                   v-bind:data-content="jsoncomments[k]" rel="popover"
                   data-placement="top" v-bind:data-original-title="k">
                  <img title="More information" src="/src/assets/img/info.png" width="30px"
                       height="35px" alt="More Info">
                </a>
                  </span></div>
              </div>
              <button class="btn btn-primary btn-lg btn-block" type="submit">Submit
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  </div>

</template>

<style scoped>

</style>