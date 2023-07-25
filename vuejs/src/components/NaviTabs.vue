<template>
  <div>
    <ul class="mini-navi">
      <li v-for="(tab, index) in tabList" :key="index">
        <router-link :id="`${index}`" :to="{path: tabLinks[index]}" class="rounded" v-bind:title="tab">
          <div class="rounded nav-icon">
            <component :is="mapTypeComponents[index]"/>
          </div>
          <span v-show="isShow">{{ tab }}</span>
        </router-link>
        <div>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { defineAsyncComponent, ref } from 'vue';


const mapTypeComponents = {
  0: defineAsyncComponent(() => import("@/components/icons/GeneralInfoIcon.vue")),
  1: defineAsyncComponent(() => import("@/components/icons/SystemInfoIcon.vue")),
  2: defineAsyncComponent(() => import("@/components/icons/abcdeIcon.vue")),
  3: defineAsyncComponent(() => import("@/components/icons/RipperIcon.vue")),
  4: defineAsyncComponent(() => import("@/components/icons/uiSettingsIcon.vue")),
  5: defineAsyncComponent(() => import("@/components/icons/AppriseIcon.vue")),
  6: defineAsyncComponent(() => import("@/components/icons/HelpIcon.vue")),
};
defineProps({
  tabList: {
    type: Array,
    required: true,
  },
  tabLinks:{
    type: Array,
    required: true
  },
  variant: {
    type: String,
    required: false
  },
  isShow: {
    type: Boolean,
    required: true
  }
})
</script>

<style>
.mini-navi{
  list-style-type: none;
  margin-left: 0px;
  padding-left: 16px;
}
</style>