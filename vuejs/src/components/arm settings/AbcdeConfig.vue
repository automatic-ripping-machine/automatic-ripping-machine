<script>
import axios from "axios";
import HomeScreenGreeting from "@/components/HomeScreenGreeting.vue";

export default {
  components: {HomeScreenGreeting},
  data() {
    return {
      liveConfig: [],
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
        this.liveConfig = response.data;
      } catch (error) {
        console.log(error);
      }
    },
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
        <form id="abcdeSettings" name="abcdeSettings" method="post" action="">
          <label for="abcdeConfigText">ABCDE Config:</label>
          <textarea id="abcdeConfigText" name="abcdeConfig" spellcheck="false"
                    class="w-100 form-control min-vh-100" :value="liveConfig">{{ liveConfig }}</textarea>
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