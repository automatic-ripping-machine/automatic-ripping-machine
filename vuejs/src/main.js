import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
let app = createApp(App)

// Set global arm api backend link
app.config.globalProperties.armapi = 'http://192.168.1.127:8887'

app.use(router).mount('#app')