<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAppStore } from './stores/app'

const appStore = useAppStore()

onMounted(async () => {
  // 初始化应用
  await appStore.init()
})
</script>

<style scoped>
#app {
  width: 100%;
  height: 100%;
}
</style>

