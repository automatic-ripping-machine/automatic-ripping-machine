<script>
import InfoBlock from "@/components/InfoBlock.vue";
import axios from "axios";

let joblist;
export default {
  name: 'SystemInfo',
  components: {
    InfoBlock,
  },
  data() {
    return {
      message: "Joey does’t share food!",
      server: {},
      serverutil: {},
      hwsupport: {},
      arm_API: this.armapi
    };
  },
  mounted() {
    joblist = this.refreshJobs()
    this.message = "First Loaded"
    console.log(this.message);
    this.$nextTick(() => {
      this.message =
          "No data yet....Loading please wait";
      console.log(this.message);
    });
  },
  methods: {
    refreshJobs: function(){
      console.log("Timer" + Math.floor(Math.random() * (25)) + 1)
      axios
          .get(this.arm_API+ '/json?mode=joblist').then((response) => {
        console.log(response.data);
        this.message = response.status
        this.server = response.data.server
        this.serverutil = response.data.serverutil
        this.hwsupport = response.data.hwsupport
      }, (error) => {
        console.log(error);
      });
      //.then(response => (this.message = response))
      return this
    }
  }
}
</script>

<template>
  <InfoBlock v-bind:server="server" v-bind:serverutil="serverutil" v-bind:hwsupport="hwsupport"/>
</template>

<style scoped>

</style>