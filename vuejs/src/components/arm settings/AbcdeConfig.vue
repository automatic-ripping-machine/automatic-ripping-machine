<script>
import axios from "axios";

export default {
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
            this.arm_API + "/json?mode=get_abcde"
        );
        // JSON responses are automatically parsed.
        this.liveConfig = response.data.cfg;
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
  <div class="tab-pane pt-5" id="abcde" role="tabpanel" aria-labelledby="abcde-tab">
    <div class="row">
      <div class="col-md-8 mx-auto">
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