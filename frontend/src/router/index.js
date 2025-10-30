import { createRouter, createWebHashHistory } from 'vue-router'
import MainLayout from '../views/MainLayout.vue'
import ChatView from '../views/ChatView.vue'
import ServersView from '../views/ServersView.vue'
import SettingsView from '../views/SettingsView.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    children: [
      {
        path: '',
        redirect: '/chat'
      },
      {
        path: '/chat',
        name: 'Chat',
        component: ChatView
      },
      {
        path: '/servers',
        name: 'Servers',
        component: ServersView
      },
      {
        path: '/settings',
        name: 'Settings',
        component: SettingsView
      }
    ]
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router

