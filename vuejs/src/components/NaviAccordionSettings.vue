<template>
  <div>
    <app-tabs :tabList="tabList" :tabLinks="tabLinks" :tabIcons="tabIcons" :isShow="this.isShowing">
    </app-tabs>
  </div>
</template>

<script>
import AppTabs from "@/components/NaviTabs.vue";

export default {
  components: {
    AppTabs,
  },
  props: {
    isShow: {
      type: Boolean,
      required: true
    }
  },
  computed: {
    isShowing() {
      return Boolean(this.isShow);
    }
  },
  data() {
    return {
      tabList: ["General Info", "System Info", "Abcde Config",
        "Ripper Settings", "UI Settings", "Apprise Config", "Help"],
      tabLinks:["general-info", "system-info", "abcde-config",
        "ripper-settings", "ui-settings", "apprise-config", "help"],
      isShow: this.isShow
    };
  },
};
</script>