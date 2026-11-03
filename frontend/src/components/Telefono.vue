<script setup lang="ts">
import { computed } from 'vue'

import Icona from '@/components/Icona.vue'
import { PULSANTI_PREDEFINITI, indirizziTelefono } from '@/navigazione/telefono'
import { useSessioneStore } from '@/stores/sessione'

// Every phone number the app shows (DEC-301): the number, and next to it the buttons the
// person chose in their preferences (call and WhatsApp unless changed). `di` names whose
// number it is, for screen readers ("Chiama Giulia Rossi").
const props = defineProps<{ numero: string; di?: string }>()
const sessione = useSessioneStore()

const indirizzi = computed(() => indirizziTelefono(props.numero))
const pulsanti = computed(() => sessione.profilo?.pulsanti_telefono ?? PULSANTI_PREDEFINITI)
const chi = computed(() => (props.di ? ` ${props.di}` : ''))
</script>

<template>
  <span class="d-inline-flex flex-wrap align-items-center gap-1">
    <span>{{ numero }}</span>
    <a
      v-if="pulsanti.includes('chiama')"
      :href="indirizzi.chiama"
      class="btn btn-icon btn-sm btn-outline theme-primary"
      :aria-label="`Chiama${chi}`"
      :title="`Chiama${chi}`"
      ><Icona nome="telephone"
    /></a>
    <a
      v-if="pulsanti.includes('whatsapp')"
      :href="indirizzi.whatsapp"
      target="_blank"
      rel="noopener"
      class="btn btn-icon btn-sm btn-outline theme-success"
      :aria-label="`Scrivi su WhatsApp${chi ? ' a' + chi : ''}`"
      :title="`Scrivi su WhatsApp${chi ? ' a' + chi : ''}`"
      ><Icona nome="whatsapp"
    /></a>
    <a
      v-if="pulsanti.includes('sms')"
      :href="indirizzi.sms"
      class="btn btn-icon btn-sm btn-outline theme-secondary"
      :aria-label="`Manda un SMS${chi ? ' a' + chi : ''}`"
      :title="`Manda un SMS${chi ? ' a' + chi : ''}`"
      ><Icona nome="chat-text"
    /></a>
  </span>
</template>
