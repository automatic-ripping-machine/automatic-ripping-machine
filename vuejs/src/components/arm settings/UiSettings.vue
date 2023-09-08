<script>
import axios from "axios";
import HomeScreenGreeting from "@/components/HomeScreenGreeting.vue";

export default {
  components: {HomeScreenGreeting},
  data() {
    return {
      ui_settings: [],
      jsoncomments: [],
      arm_API: this.armapi,
      form: {
        _method: 'PUT',
        index_refresh: '',
        notify_refresh: '',
        use_icons: '',
        save_remote_images: '',
        bootstrap_skin: '',
        language: '',
        database_limit: ''
      }
    };
  },

  methods: {
    async getData() {
      try {
        const response = await axios.get(
            this.arm_API + "/settings/get_ui_conf"
        );
        // JSON responses are automatically parsed.
        this.form = response.data.cfg;
        this.jsoncomments = response.data.comments
      } catch (error) {
        console.log(error);
      }
    },
    submit: function () {
      axios.put(this.arm_API + "/settings/get_ui_conf", this.form)
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
            <HomeScreenGreeting msg="Change UI Settings" msg2=""/>
            <br>
            <form ref="form" @submit.prevent="submit">
              <!-- INDEX REFRESH -->
              <div class="input-group mb-3">
                <div class="input-group-prepend">
                  <span class="input-group-text" id="index_refresh">index_refresh: </span>
                </div>

                <input type="text" class="form-control" aria-label="index_refresh"
                       name="index_refresh" placeholder=""
                       aria-describedby="index_refresh" v-model="form.index_refresh">
                <div class="input-group-append">
                  <span class="input-group-text" id="basic-addon2">
                    <a class="popovers m-auto" onClick='return false;' href=""
                       v-bind:data-content="jsoncomments['index_refresh']"
                       rel="popover"
                       data-placement="top" data-original-title="index_refresh">
                  <img title="More information" src="/src/assets/img/info.png" width="30px"
                       height="35px" alt="More info">
                </a>
                </span>
                </div>
              </div>
              <!-- NOTIFICATION TIMEOUT -->
              <div class="input-group mb-3">
                <div class="input-group-prepend">
                  <span class="input-group-text" id="notify_refresh">Notification Timeout: </span>
                </div>
                <input type="text" class="form-control" aria-label="notify_refresh"
                       name="notify_refresh" placeholder=""
                       aria-describedby="notify_refresh" v-model="form.notify_refresh">
                <div class="input-group-append">
                  <span class="input-group-text" id="basic-addon2">
                <a class="popovers" onClick='return false;' href=""
                   v-bind:data-content="jsoncomments['notify_refresh']"
                   rel="popover"
                   data-placement="top" data-original-title="notify_refresh">
                  <img title="More information" src="/src/assets/img/info.png" width="30px"
                       height="35px" alt="More info">
                </a>
                  </span>
                </div>
              </div>
              <!-- USE ICONS -->
              <div class="input-group mb-3">
                <div class="input-group-prepend">
                  <span class="input-group-text" id="use_icons">use_icons: </span>
                </div>
                <input type="text" class="form-control" aria-label="use_icons" name="use_icons"
                       v-model="form.use_icons">
                <div class="input-group-append">
                  <span class="input-group-text" id="basic-addon2">
                <a class="popovers" onClick='return false;' href=""
                   v-bind:data-content="jsoncomments['use_icons']" rel="popover"
                   data-placement="top" data-original-title="use_icons">
                  <img title="More information" src="/src/assets/img/info.png" width="30px"
                       height="35px" alt="More info">
                </a>
                    </span>
                </div>
              </div>
              <!-- SAVE REMOTE IMAGES-->
              <div class="input-group mb-3">
                <div class="input-group-prepend">
                    <span class="input-group-text"
                          id="save_remote_images">save_remote_images: </span>
                </div>
                <input type="text" class="form-control" aria-label="save_remote_images"
                       name="save_remote_images" v-model="form.save_remote_images">
                <div class="input-group-append">
                  <span class="input-group-text" id="basic-addon2">
                <a class="popovers" onClick='return false;' href=""
                   v-bind:data-content="jsoncomments['save_remote_images']"
                   rel="popover"
                   data-placement="top" data-original-title="save_remote_images">
                  <img title="More information" src="/src/assets/img/info.png" width="30px"
                       height="35px" alt="More info">
                </a>
                                        </span>
                </div>
              </div>
              <!-- BOOTSTRAP SKIN -->
              <div class="input-group mb-3">
                <div class="input-group-prepend">
                  <span class="input-group-text" id="bootstrap_skin">bootstrap_skin: </span>
                </div>
                <input type="text" class="form-control" aria-label="bootstrap_skin"
                       name="bootstrap_skin" placeholder="" v-model="form.bootstrap_skin"
                       aria-describedby="bootstrap_skin">
                <div class="input-group-append">
                  <span class="input-group-text" id="basic-addon2">
                <a class="popovers" onClick='return false;' href=""
                   v-bind:data-content="jsoncomments['bootstrap_skin']"
                   rel="popover"
                   data-placement="top" data-original-title="bootstrap_skin">
                  <img title="More information" src="/src/assets/img/info.png" width="30px"
                       height="35px" alt="More info">
                </a>
                                        </span>
                </div>
              </div>
              <!-- LANGUAGE -->
              <div class="input-group mb-3">
                <div class="input-group-prepend">
                  <span class="input-group-text" id="language">language: </span>
                </div>
                <input type="text" class="form-control" aria-label="language" name="language"
                       placeholder="" v-model="form.language"
                       aria-describedby="language">
                <div class="input-group-append">
                  <span class="input-group-text" id="basic-addon2">
                <a class="popovers" onClick='return false;' href=""
                   v-bind:data-content="jsoncomments['language']" rel="popover"
                   data-placement="top" data-original-title="language">
                  <img title="More information" src="/src/assets/img/info.png" width="30px"
                       height="35px" alt="More info">
                </a>
                                        </span>
                </div>
              </div>
              <!-- DATABASE LIMIT -->
              <div class="input-group mb-3">
                <div class="input-group-prepend">
                  <span class="input-group-text" id="database_limit">database_limit: </span>
                </div>
                <input type="text" class="form-control" aria-label="database_limit"
                       name="database_limit" placeholder="" v-model="form.database_limit"
                       aria-describedby="database_limit">
                <div class="input-group-append">
                  <span class="input-group-text" id="basic-addon2">
                <a class="popovers" onClick='return false;' href=""
                   v-bind:data-content="jsoncomments['database_limit']"
                   rel="popover"
                   data-placement="top" data-original-title="database_limit">
                  <img title="More information" src="/src/assets/img/info.png" width="30px"
                       height="35px" alt="More info">
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
    </div>
  </div>

</template>

<style scoped>

</style>