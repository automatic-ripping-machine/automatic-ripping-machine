<script>
import axios from "axios";
import HomeScreenGreeting from "@/components/HomeScreenGreeting.vue";

export default {
  components: {HomeScreenGreeting},
  data() {
    return {
      ui_settings: [],
      jsoncomments: [],
      arm_API: this.armapi
    };
  },

  methods: {
    async getData() {
      try {
        const response = await axios.get(
            this.arm_API + "/json?mode=get_ui_conf"
        );
        // JSON responses are automatically parsed.
        this.ui_settings = response.data.cfg;
        this.jsoncomments = response.data.comments
      } catch (error) {
        console.log(error);
      }
    },
    submit: function () {
      const formData = new FormData(this.$refs['form']); // reference to form element
      const data = {}; // need to convert it before using not with XMLHttpRequest
      let postData = {}
      for (let [key, val] of formData.entries()) {
        Object.assign(data, {[key]: val})
        postData[key] = '"'+ val + '"'
      }
      console.log(postData)
      axios.post(this.arm_API + '/save_ui_settings', postData)
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
            <HomeScreenGreeting msg="Change UI Settings" msg2=""/>
            <br>
            <form ref="form" @submit.prevent="submit" id="my-form">
              <!-- INDEX REFRESH -->
              <div class="input-group mb-3">
                <div class="input-group-prepend">
                  <span class="input-group-text" id="index_refresh">index_refresh: </span>
                </div>
                <input type="text" class="form-control" aria-label="index_refresh"
                       name="index_refresh" placeholder="" v-bind:value="ui_settings.index_refresh"
                       aria-describedby="index_refresh">
                <a class="popovers m-auto p-2" onClick='return false;' href=""
                   v-bind:data-content="jsoncomments['index_refresh']"
                   rel="popover"
                   data-placement="top" data-original-title="index_refresh">
                  <img title="More information" src="/src/assets/img/info.png" width="30px"
                       height="35px" alt="More info">
                </a>
              </div>
              <!-- NOTIFICATION TIMEOUT -->
              <div class="input-group mb-3">
                <div class="input-group-prepend">
                  <span class="input-group-text" id="notify_refresh">Notification Timeout: </span>
                </div>
                <input type="text" class="form-control" aria-label="notify_refresh"
                       name="notify_refresh" placeholder="" v-bind:value="ui_settings.notify_refresh"
                       aria-describedby="notify_refresh">
                <a class="popovers p-2" onClick='return false;' href=""
                   v-bind:data-content="jsoncomments['notify_refresh']"
                   rel="popover"
                   data-placement="top" data-original-title="notify_refresh">
                  <img title="More information" src="/src/assets/img/info.png" width="30px"
                       height="35px" alt="More info">
                </a>
              </div>
              <!-- USE ICONS -->
              <div class="input-group mb-3">
                <div class="input-group-prepend">
                  <span class="input-group-text" id="use_icons">use_icons: </span>
                </div>
                <input type="text" class="form-control" aria-label="use_icons" name="use_icons"
                       v-bind:value="ui_settings.use_icons" disabled>

                <a class="popovers p-2" onClick='return false;' href=""
                   v-bind:data-content="jsoncomments['use_icons']" rel="popover"
                   data-placement="top" data-original-title="use_icons">
                  <img title="More information" src="/src/assets/img/info.png" width="30px"
                       height="35px" alt="More info">
                </a>
              </div>
              <!-- SAVE REMOTE IMAGES-->
              <div class="input-group mb-3">
                <div class="input-group-prepend">
                    <span class="input-group-text"
                          id="save_remote_images">save_remote_images: </span>
                </div>
                <input type="text" class="form-control" aria-label="save_remote_images"
                       name="save_remote_images" v-bind:value="ui_settings.save_remote_images" disabled>
                <a class="popovers p-2" onClick='return false;' href=""
                   v-bind:data-content="jsoncomments['save_remote_images']"
                   rel="popover"
                   data-placement="top" data-original-title="save_remote_images">
                  <img title="More information" src="/src/assets/img/info.png" width="30px"
                       height="35px" alt="More info">
                </a>
              </div>
              <!-- BOOTSTRAP SKIN -->
              <div class="input-group mb-3">
                <div class="input-group-prepend">
                  <span class="input-group-text" id="bootstrap_skin">bootstrap_skin: </span>
                </div>
                <input type="text" class="form-control" aria-label="bootstrap_skin"
                       name="bootstrap_skin" placeholder="" v-bind:value="ui_settings.bootstrap_skin"
                       aria-describedby="bootstrap_skin">
                <a class="popovers p-2" onClick='return false;' href=""
                   v-bind:data-content="jsoncomments['bootstrap_skin']"
                   rel="popover"
                   data-placement="top" data-original-title="bootstrap_skin">
                  <img title="More information" src="/src/assets/img/info.png" width="30px"
                       height="35px" alt="More info">
                </a>
              </div>
              <!-- LANGUAGE -->
              <div class="input-group mb-3">
                <div class="input-group-prepend">
                  <span class="input-group-text" id="language">language: </span>
                </div>
                <input type="text" class="form-control" aria-label="language" name="language"
                       placeholder="" v-bind:value="ui_settings.language"
                       aria-describedby="language" disabled>
                <a class="popovers p-2" onClick='return false;' href=""
                   v-bind:data-content="jsoncomments['language']" rel="popover"
                   data-placement="top" data-original-title="language">
                  <img title="More information" src="/src/assets/img/info.png" width="30px"
                       height="35px" alt="More info">
                </a>
              </div>
              <!-- DATABASE LIMIT -->
              <div class="input-group mb-3">
                <div class="input-group-prepend">
                  <span class="input-group-text" id="database_limit">database_limit: </span>
                </div>
                <input type="text" class="form-control" aria-label="database_limit"
                       name="database_limit" placeholder="" v-bind:value="ui_settings.database_limit"
                       aria-describedby="database_limit">
                <a class="popovers p-2" onClick='return false;' href=""
                   v-bind:data-content="jsoncomments['database_limit']"
                   rel="popover"
                   data-placement="top" data-original-title="database_limit">
                  <img title="More information" src="/src/assets/img/info.png" width="30px"
                       height="35px" alt="More info">
                </a>
              </div>
              <button class="btn btn-primary btn-lg btn-block" type="submit">
                Submit
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