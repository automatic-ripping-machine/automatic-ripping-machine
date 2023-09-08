<script>
import axios from "axios";
import HomeScreenGreeting from "@/components/HomeScreenGreeting.vue";

export default {
  components: {HomeScreenGreeting},
  data() {
    return {
      liveConfig: {},
      jsoncomments: [],
      arm_API: this.armapi
    };
  },

  methods: {
    async getData() {
      try {
        const response = await axios.get(
            this.arm_API + "/settings/ripper"
        );
        // JSON responses are automatically parsed.
        this.liveConfig = response.data.cfg;
        this.jsoncomments = response.data.comments
      } catch (error) {
        console.log(error);
      }
    },
    submit: function () {
      this.liveConfig._method = 'PUT'
      axios.put(this.arm_API + "/settings/ripper", this.liveConfig)
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
  <div class="container justify-content-center jumbotron mt-4">
    <div class="col justify-content-center" style="flex-wrap: nowrap">
      <HomeScreenGreeting msg="Change Ripper Settings" msg2=""/>
    </div>
    <div class="row justify-content-center" style="flex-wrap: nowrap">
      <div class="col-10">
        <form ref="form" @submit.prevent="submit">
          <div v-for="(v, k) in liveConfig" key="index" class="input-group mb-3">
            <div class="input-group-prepend">
              <span class="input-group-text">{{ k }}: </span>
            </div>
            <input type="text" class="form-control" v-bind:aria-label="k" v-model="liveConfig[k]">
            <div class="input-group-append">
                  <span class="input-group-text" id="basic-addon2">
            <a class="popovers m-auto" onClick='return false;' href=""
               v-bind:data-content="jsoncomments[k]" rel="popover"
               data-placement="top" v-bind:data-original-title="k">
              <img title="More information" src="/src/assets/img/info.png" width="30px"
                   height="35px" alt="More Info">
            </a>
                  </span>
            </div>
          </div>
          <button class="btn btn-primary btn-lg btn-block" type="submit">
            Submit
          </button>
        </form>
      </div>
    </div>
  </div>

</template>

<style scoped>

</style>