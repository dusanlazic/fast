<script setup>
import { reactive } from "vue";
import { Icon } from '@iconify/vue'
import Dashboard from './Dashboard.vue'
import FlagBrowser from "./FlagBrowser.vue";
import ManualSubmit from "./ManualSubmit.vue";

const routes = {
  '': {
    title: 'Dashboard',
    iconInactive: 'ri:dashboard-3-line',
    iconActive: 'ri:dashboard-3-fill',
  },
  'browse': {
    title: 'Browse flags',
    iconInactive: 'ri:flag-line',
    iconActive: 'ri:flag-fill',
  },
  'submit': {
    title: 'Manual submit',
    iconInactive: 'ri:send-plane-line',
    iconActive: 'ri:send-plane-fill',
  },
}

window.addEventListener('hashchange', () => {
  navigation.path = getCurrentPath()
  navigation.page = routes[navigation.path]
})

function getCurrentPath() {
  const path = window.location.hash.slice(1) || ''
  if (!(path in routes)) {
    return ''
  } else {
    return path
  }
}

function getIcon(path) {
  return path === navigation.path ? routes[path].iconActive : routes[path].iconInactive
}

const navigation = reactive({
  path: getCurrentPath(),
  page: routes[getCurrentPath()],
  navigate: (path) => {
    window.location.hash = path
  }
})
</script>

<template>
  <div class="is-flex mb-5">
    <div v-for="[path, page] in Object.entries(routes)" @click="navigation.navigate(path)" class="navigation-link" :class="{ active: path === navigation.path}">
      <Icon :icon="getIcon(path)" class="is-size-4 mr-2" inline="true" />
      <span>{{ page.title }}</span>
    </div>
  </div>
  <div v-show="navigation.path === ''">
    <Dashboard />
  </div>
  <div v-show="navigation.path === 'browse'">
    <FlagBrowser />
  </div>
  <div v-show="navigation.path === 'submit'">
    <ManualSubmit />
  </div>
</template>

<style>
.navigation-link {
  margin-right: 2em;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #b5b5b5;
  cursor: pointer;
  z-index: 2;
}

.navigation-link:hover {
  color:#7A7A7A;
}

.navigation-link.active {
  color:#363636;
}
</style>