import 'bootstrap/dist/css/bootstrap.min.css'
import './theme/qdc.scss'

import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import { collegaCassaforte } from './sicurezza/collegamenti'

// Ask the browser not to evict offline data under storage pressure (camp, DEC-94).
void navigator.storage?.persist?.()

// Offline expiry header and device revocation from every server answer (DEC-97).
collegaCassaforte()

createApp(App).use(createPinia()).use(router).mount('#app')
