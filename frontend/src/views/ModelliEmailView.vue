<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, type ModelloEmailBreve } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The email templates on a page of their own (DEC-300): too many for the settings page.
// Capigruppo and the technical administrator: the API decides.
const { errore, inCorso, esegui } = useErrore()
const modelli = ref<ModelloEmailBreve[]>([])

onMounted(async () => {
  modelli.value = (await esegui(() => api.modelliEmail())) ?? []
})
</script>

<template>
  <section>
    <RouterLink to="/impostazioni" class="small">Torna alle impostazioni</RouterLink>
    <h1 class="h4 mb-1 mt-3">Modelli delle email</h1>
    <p class="small fg-2">
      Il testo di ogni email che l'app manda. Puoi cambiarlo e tornare quando vuoi al testo di base;
      quello che serve davvero (link, codici, le informazioni da mandare) deve restare.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <p class="small">
      <RouterLink to="/impostazioni/email-piede">Piè di pagina comune delle email</RouterLink>
    </p>
    <p v-if="inCorso" class="fg-2">Caricamento…</p>
    <div v-else class="list-group">
      <RouterLink
        v-for="m in modelli"
        :key="m.chiave"
        :to="{ name: 'modello-email', params: { chiave: m.chiave } }"
        class="list-group-item list-group-item-action"
      >
        <div class="d-flex flex-wrap align-items-center gap-3">
          <strong>{{ m.nome }}</strong>
          <span v-if="m.da_correggere" class="badge theme-warning">Da correggere</span>
          <span v-else-if="m.personalizzato" class="badge theme-success">Personalizzato</span>
        </div>
        <div class="small fg-2">{{ m.descrizione }}</div>
      </RouterLink>
    </div>
  </section>
</template>
