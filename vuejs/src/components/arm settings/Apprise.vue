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
            this.arm_API + "/json?mode=get_apprise"
        );
        // JSON responses are automatically parsed.
        this.liveConfig = response.data.cfg;
        this.jsoncomments = response.data.comments
      } catch (error) {
        console.log(error);
      }
    },//save_apprise_cfg
    submit: function () {
      const formData = new FormData(this.$refs['form']); // reference to form element
      const data = {}; // need to convert it before using not with XMLHttpRequest
      let postData = {}
      for (let [key, val] of formData.entries()) {
        Object.assign(data, {[key]: val})
        postData[key] = '"' + val + '"'
      }
      console.log(postData)
      axios.post(this.arm_API + '/save_apprise_cfg', postData)
          .then(function (response) {
            console.log(response);
          })
          .catch(function (error) {
            console.log(error);
          });
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
            <form ref="form" @submit.prevent="submit" id="my-form">
              <div v-for="(v, k) in liveConfig" key="index" class="input-group mb-3">
                <div class="input-group-prepend">
                  <span class="input-group-text" v-bind:id="k">{{ k }}: </span>
                </div>
                <input type="text" class="form-control" v-bind:aria-label="k" v-bind:name="k" v-bind:placeholder="v"
                       v-bind:value="v" v-bind:aria-describedby="k">
                <a class="popovers input-group-text" onClick='return false;' href=""
                   v-bind:data-content="jsoncomments[k]" rel="popover"
                   data-placement="top" v-bind:data-original-title="k">
                  <img title="More information" src="/src/assets/img/info.png" width="30px"
                       height="35px" alt="More Info">
                </a>
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