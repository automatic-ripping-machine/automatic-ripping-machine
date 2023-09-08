<template>
  <NavView/>
  <router-view/>
</template>
<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  min-height: inherit;
  background-color: #181818;
}

/* Enter and leave animations can use different */
/* durations and timing functions.              */
.slide-fade-enter-active {
  transition: all .3s ease;
}
.slide-fade-leave-active {
  transition: all .8s cubic-bezier(1.0, 0.5, 0.8, 1.0);
}
.slide-fade-enter, .slide-fade-leave-to
  /* .slide-fade-leave-active below version 2.1.8 */ {
  transform: translateX(10px);
  opacity: 0;
}
</style>
<script>
import axios from "axios";
const token = JSON.parse( localStorage.getItem('token') );
if( token ){
  axios.defaults.headers.common['Authorization'] = 'Bearer ' + token;
}else{
  // forward to login if not already in
  if (window.location.pathname !== "/login"){
    window.location.href = "/login";
  }
}
import {defineComponent} from "vue";
import NavView from "@/views/NavView.vue";

export default defineComponent({
  components: {NavView},
  data() {
    return {
      arm_API: this.armapi
    };
  },
})
</script>
