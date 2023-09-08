<script>
import CloseMenuIcon from '../components/icons/CloseMenu.vue'
import HomeIcon from '../components/icons/Home.vue'
import HistoryIcon from '../components/icons/History.vue'
import DatabaseIcon from '../components/icons/Database.vue'
import ArmSettingsIcon from "@/components/icons/ArmSettings.vue";
import SendToApiIcon from "@/components/icons/SendToApi.vue";
import ChangePasswordIcon from "@/components/icons/ChangePassword.vue";
import ViewLogsIcon from "@/components/icons/ViewLogs.vue";
import NaviAccordionSettings from "@/components/NaviAccordionSettings.vue";
import {ref} from 'vue'
import NotificationIcon from "@/components/icons/NotificationIcon.vue";
import {defineComponent} from "vue";
import axios from "axios";

export default defineComponent({
  components: {NotificationIcon,
    NaviAccordionSettings,
    ViewLogsIcon,
    ChangePasswordIcon,
    SendToApiIcon,
    ArmSettingsIcon,
    DatabaseIcon,
    HistoryIcon,
    HomeIcon,
    CloseMenuIcon
  },
  data() {
    return {
      // Main menu open/close
      isShow: ref(true),
      // Sub menu open/close
      isOpen: ref(false),
      // Notification count
      notifyCount: ref(0),
      arm_API: this.armapi
    }
  },
  mounted() {
    let refreshList = setInterval(this.refreshNotes, 5000)
    this.$nextTick(() => {
      this.message = "No data yet....Loading please wait";
      console.log(this.message);
    });
  },
  unmounted() {
    console.log("Clearing timers")
    clearInterval(refreshList);
  },
  methods: {
    refreshNotes: function () {
      console.log("Timer" + Math.floor(Math.random() * (25)) + 1)
      axios
          .get(this.arm_API + '/get_notifications').then((response) => {
        console.log(response.data);
        this.notifyCount = response.data.length
        //response.data
      }, (error) => {
        console.log(error);
      });
      return this
    }
  }
})
</script>
<template>
  <nav>
    <div class="rounded" :class="{ 'd-flex': isShow }">
    <a @click="isShow = !isShow;">
      <div class="rounded nav-icon">
        <CloseMenuIcon/>
      </div>
    </a>
      <router-link class="rounded" to="/notifications" title="View Notifications">
        <div class="rounded nav-icon">
          <NotificationIcon/>
          <span v-show="notifyCount > 0" class="badge badge-light">{{ notifyCount }}</span>
        </div>
      </router-link>
    </div>
    <hr>

    <router-link class="rounded" to="/" title="Home">
      <div class="rounded nav-icon">
        <HomeIcon/>
      </div>
      <span v-show="isShow">Home</span></router-link>
    <router-link class="rounded" to="/history" title="View History">
      <div class="rounded nav-icon">
        <HistoryIcon/>
      </div>
      <span v-show="isShow">History</span></router-link>
    <router-link class="rounded" to="/view_logs" title="View Logs">
      <div class="rounded nav-icon">
        <ViewLogsIcon/>
      </div>
      <span v-show="isShow">View Logs</span></router-link>
    <router-link class="rounded" to="/database" title="Database">
      <div class="rounded nav-icon">
        <DatabaseIcon/>
      </div>
      <span v-show="isShow">Database</span></router-link>
    <a @click="isOpen = !isOpen; console.log('Triggered_accordion='+ isOpen);" role="button" class="user-select-none">
      <div class="rounded nav-icon">
        <ArmSettingsIcon/>
      </div>
      <span v-show="isShow">Settings</span></a>
    <Transition name="slidedown">
      <NaviAccordionSettings v-show="isOpen" :isOpen="isOpen" :isShow="isShow" title="Settings"/>
    </Transition>
    <router-link class="rounded" to="/send_to_api" title="Send DVD's to API">
      <div class="rounded nav-icon">
        <SendToApiIcon/>
      </div>
      <span v-show="isShow">Send DVD's to API</span></router-link>
    <router-link class="rounded" to="/change_password" title="Change Password">
      <div class="rounded nav-icon">
        <ChangePasswordIcon/>
      </div>
      <span v-show="isShow">Change Password</span></router-link>
  </nav>
</template>
<style>
.nav-icon {
  display: inline;
  background-color: #3a3f48;
  min-width: 5px;
  margin: 7px;
  padding: 3px 3px 6px;
}
nav a:hover .nav-icon, nav a.router-link-exact-active:hover .nav-icon, .nav-icon:hover{
  color: #061215;
  background-color: rgba(22, 199, 255, 0.3);
}
nav a:hover .nav-icon svg path,
nav a:hover .nav-icon svg line,
nav a:hover .nav-icon svg ellipse,
nav a:hover .nav-icon svg rect,
nav a:hover .nav-icon svg circle,
nav a:hover .nav-icon svg polyline{
   fill: rgba(252, 252, 252, 0.37);
   stroke: rgb(43, 43, 44);
 }

nav {
  background-color: #31353d;
  color: #f2f2f2;
}
/*For navi on small screens*/
@media only screen and (max-width: 1000px) {
  nav{
    display: inline-flex;
    flex-wrap: wrap;
    position: fixed;
    top: 0;
    left: 0;
    z-index: 1000;
    width: 100%;
    opacity: 0.8;
  }
}

nav a.router-link-exact-active, nav a.router-link-exact-active svg {
  color: #d2d2d2;
}
nav a.router-link-exact-active .nav-icon svg path,
nav a.router-link-exact-active .nav-icon svg line,
nav a.router-link-exact-active .nav-icon svg ellipse,
nav a.router-link-exact-active .nav-icon svg rect,
nav a.router-link-exact-active .nav-icon svg circle,
nav a.router-link-exact-active .nav-icon svg polyline,
nav a.router-link-exact-active .nav-icon{
  fill: rgba(252, 252, 252, 0.37);
  stroke: rgb(43, 43, 44);
  color: #061215;
  background-color: rgba(22, 199, 255, 0.99);
}

nav a svg {
  margin: 5px;
}

nav a {
  font-weight: bold;
  padding: 15px;
  color: #f2f2f2;
}

nav a:hover {
  color: #36c7c7;
  text-decoration: none;
}

nav a span {
  display: inline;
  padding-left: 4px;
  vertical-align: bottom;
}

.slidedown-enter-active,
.slidedown-leave-active {
  transition: max-height 0.5s ease-in-out;
}

.slidedown-enter-to,
.slidedown-leave-from {
  overflow: hidden;
  max-height: 1000px;
}

.slidedown-enter-from,
.slidedown-leave-to {
  overflow: hidden;
  max-height: 0;
}
</style>