<script>
import axios from "axios";
import HomeScreenGreeting from "@/components/HomeScreenGreeting.vue";

export default {
  components: {HomeScreenGreeting},
  data() {
    return {
      liveConfig: {},
      arm_API: this.armapi
    };
  },

  methods: {
    async getData() {
      try {
        const response = await axios.get(
            this.arm_API + "/settings/get_abcde"
        );
        // JSON responses are automatically parsed.
        this.liveConfig = response.data.config;
      } catch (error) {
        console.log(error);
      }
    },
    submit: function () {
      //this.liveConfig._method = 'PUT'
      axios.put(this.arm_API + "/settings/get_abcde", { "config": this.liveConfig})
          .then((data) => {
            this.liveConfig = data.data.config;
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
      <HomeScreenGreeting msg="Change ABCDE Settings" msg2=""/>
    </div>
    <div class="row justify-content-center" style="flex-wrap: nowrap">
      <div class="col-10">

        <form ref="form" @submit.prevent="submit" id="abcdeSettings" name="abcdeSettings">
          <label for="config">ABCDE Config:</label>
          <textarea id="config" name="config" spellcheck="false"
                    class="w-100 form-control min-vh-100" v-model="liveConfig"></textarea>
          <br>
          <button id="abcdeConfigSubmit" class="btn btn-secondary btn-lg btn-block"
                  form="abcdeSettings">Submit
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>

</style>