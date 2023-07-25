import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
let app = createApp(App)

// Set global arm api backend link
app.config.globalProperties.armapi = 'http://0.0.0.0:8880'

app.use(router).mount('#app')