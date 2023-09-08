<script>

import Notify from "@/views/Notify.vue";
import {defineComponent} from "vue";
import axios from "axios";
import HomeScreenGreeting from "@/components/HomeScreenGreeting.vue";

export default defineComponent({
  components: {HomeScreenGreeting, Notify},
  data() {
    return {
      notes: {},
      arm_API: this.armapi
    };
  },

  methods: {
    async getData() {
      try {
        const response = await axios.get(
            this.arm_API + "/get_all_notifications"
        );
        // JSON responses are automatically parsed.
        console.log(response.data)
        this.notes = response.data;
      } catch (error) {
        console.log(error);
      }
    },
  },

  created() {
    this.getData();
  },
})

</script>

<template>
  <div class="container">
    <div class="row">
      <div class="col">
        <div class="table-responsive">
          <div class="jumbotron mt-5">
            <HomeScreenGreeting msg="Notifications" msg2=""/>
            <br>
        <div class="card">
          <div class="card-header">
            Clear All <a href="notificationclose">[x]</a>
          </div>
        </div>
        <Notify :notes="notes"/>
      </div>
    </div>
  </div>
    </div></div>
</template>