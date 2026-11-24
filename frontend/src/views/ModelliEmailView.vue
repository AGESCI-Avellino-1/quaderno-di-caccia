<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, type ModelloEmailBreve } from '@/api/qdc'
import Icona from '@/components/Icona.vue'
import { useErrore } from '@/composables/useErrore'

// The email templates on a page of their own (DEC-300), grouped by what they are about in an
// accordion: all closed at first, one open at a time (`<details name>`, DEC-423). The server
// sends them in the order of the groups. Capigruppo and the technical administrator: the API
// decides.
const { errore, inCorso, esegui } = useErrore()
const modelli = ref<ModelloEmailBreve[]>([])

onMounted(async () => {
  modelli.value = (await esegui(() => api.modelliEmail())) ?? []
})

const gruppi = computed(() => {
  const per = new Map<string, ModelloEmailBreve[]>()
  for (const m of modelli.value) per.set(m.gruppo, [...(per.get(m.gruppo) ?? []), m])
  return [...per].map(([nome, elenco]) => ({
    nome,
    elenco,
    personalizzati: elenco.filter((m) => m.personalizzato).length,
    daCorreggere: elenco.filter((m) => m.da_correggere).length,
  }))
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
    <div v-else class="accordion" data-gruppi>
      <details v-for="g in gruppi" :key="g.nome" name="modelli-email" class="accordion-item">
        <summary class="accordion-header">
          <span class="d-flex flex-wrap align-items-center gap-3">
            {{ g.nome }}
            <span class="small fg-2">{{
              g.elenco.length === 1 ? '1 modello' : `${g.elenco.length} modelli`
            }}</span>
            <span v-if="g.daCorreggere" class="badge theme-warning">
              {{ g.daCorreggere }} da correggere
            </span>
            <span v-if="g.personalizzati" class="badge theme-success">
              {{ g.personalizzati }}
              {{ g.personalizzati === 1 ? 'personalizzato' : 'personalizzati' }}
            </span>
          </span>
          <Icona nome="chevron-down" class="accordion-icon" />
        </summary>
        <div class="accordion-body p-0">
          <div class="list-group list-group-flush">
            <RouterLink
              v-for="m in g.elenco"
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
        </div>
      </details>
    </div>
  </section>
</template>
