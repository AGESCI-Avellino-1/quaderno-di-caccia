<script setup lang="ts">
import { api, type FunzioneFacoltativa, type Impostazioni } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { useSessioneStore } from '@/stores/sessione'

// The features the group may switch off (DEC-421): off at first. Off, a feature is as if it
// did not exist, for everyone; its data stay and come back when it is switched on again.
// The capigruppo and the technical administrator.
defineProps<{ impostazioni: Impostazioni }>()
const emit = defineEmits<{ aggiornate: [Impostazioni] }>()
const { errore, inCorso, esegui } = useErrore()
const sessione = useSessioneStore()

async function imposta(f: FunzioneFacoltativa, attiva: boolean) {
  const nuove = await esegui(() => api.attivaFunzione(f.chiave, attiva))
  if (nuove) {
    emit('aggiornate', nuove)
    // The menu entries follow at once.
    await sessione.carica()
  }
}
</script>

<template>
  <section id="funzioni" class="mb-7" data-funzioni>
    <h2 class="h5">Funzioni facoltative</h2>
    <p class="small fg-2">
      Spenta, una funzione sparisce dall'app per tutti, con le sue email e notifiche. Quello che
      contiene non si perde: riaccendendola torna com'era.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div class="card card-body">
      <div v-for="f in impostazioni.funzioni ?? []" :key="f.chiave" class="form-field">
        <div class="switch">
          <input
            :id="`imp-funzione-${f.chiave}`"
            type="checkbox"
            role="switch"
            :checked="f.attiva"
            :disabled="inCorso"
            @change="imposta(f, ($event.target as HTMLInputElement).checked)"
          />
        </div>
        <label :for="`imp-funzione-${f.chiave}`">
          {{ f.nome }}
          <span class="d-block small fg-2">{{ f.descrizione }}</span>
        </label>
      </div>
    </div>
  </section>
</template>
