<script setup lang="ts">
import { ref, watch } from 'vue'

import { api, type Impostazioni } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { useSitoStore } from '@/stores/sito'

// Maintenance (DEC-268): only the technical administrators get in while it is on.
const props = defineProps<{ impostazioni: Impostazioni }>()
const emit = defineEmits<{ aggiornate: [Impostazioni] }>()
const { errore, inCorso, esegui } = useErrore()
const sito = useSitoStore()
const messaggio = ref(props.impostazioni.messaggio_manutenzione)
watch(
  () => props.impostazioni.messaggio_manutenzione,
  (nuovo) => (messaggio.value = nuovo),
)

async function imposta(attiva: boolean) {
  const nuove = await esegui(() => api.manutenzione(attiva, messaggio.value))
  if (!nuove) return
  emit('aggiornate', nuove)
  await sito.carica()
}
</script>

<template>
  <section class="mb-7">
    <h2 class="h5">Manutenzione</h2>
    <p class="small fg-2">
      Mentre la manutenzione è attiva entrano solo gli amministratori tecnici. Tutti gli altri
      vedono il messaggio qui sotto al posto delle pagine, anche chi è già dentro, e si fermano
      anche la richiesta di iscrizione, la lista d'attesa e il calendario. Restano aperte la pagina
      di accesso, la privacy policy e i termini. Quello che i capi hanno salvato sul telefono non si
      perde: le modifiche fatte senza rete partono quando la manutenzione finisce.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div class="card card-body">
      <label class="form-label small mb-0" for="imp-manutenzione-messaggio">Messaggio</label>
      <textarea
        id="imp-manutenzione-messaggio"
        v-model="messaggio"
        class="form-control form-control-sm"
        rows="3"
        maxlength="1000"
        :placeholder="impostazioni.messaggio_manutenzione_predefinito"
      ></textarea>
      <p class="small fg-2 mb-3">Se lo lasci vuoto si vede il testo di esempio.</p>
      <div class="d-flex flex-wrap gap-3 align-items-center">
        <template v-if="impostazioni.manutenzione">
          <span class="badge theme-warning">Manutenzione in corso</span>
          <button
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            :disabled="inCorso"
            @click="imposta(true)"
          >
            Aggiorna il messaggio
          </button>
          <button
            type="button"
            class="btn btn-sm btn-solid theme-primary"
            :disabled="inCorso"
            @click="imposta(false)"
          >
            Termina la manutenzione
          </button>
        </template>
        <button
          v-else
          type="button"
          class="btn btn-sm btn-solid theme-warning"
          :disabled="inCorso"
          @click="imposta(true)"
        >
          Metti in manutenzione
        </button>
      </div>
    </div>
  </section>
</template>
