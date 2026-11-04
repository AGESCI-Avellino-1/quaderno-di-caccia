<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { api, type PreferenzePush } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { appInstallata } from '@/pwa/installazione'
import { attiva, attiveQui, disattiva, notificheSupportate, permesso } from '@/pwa/notifiche'
import { useSessioneStore } from '@/stores/sessione'

// Notifications on this device and what the person wants on all of theirs (DEC-345).
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()
const disponibili = ref(false)
const chiave = ref('')
const qui = ref(false)
const supportate = notificheSupportate()
const negate = ref(permesso() === 'denied')
const salvate = ref(false)
const scelte = reactive<PreferenzePush>({
  eventi: true,
  promemoria_quote: true,
  riepiloghi: true,
  avvisi: true,
})
const VOCI = [
  { chiave: 'eventi', etichetta: 'Riunioni ed eventi: novità, cambi, annullamenti, convocazioni' },
  { chiave: 'promemoria_quote', etichetta: 'Scadenze delle quote e di BuonaCaccia' },
  { chiave: 'avvisi', etichetta: 'Bacheca e documenti, quando chi pubblica sceglie di avvisare' },
] as const

onMounted(async () => {
  const stato = await esegui(() => api.statoPush())
  if (!stato) return
  disponibili.value = stato.disponibili
  chiave.value = stato.chiave_pubblica
  Object.assign(scelte, stato.preferenze)
  qui.value = await attiveQui().catch(() => false)
})

async function cambiaQui() {
  await esegui(async () => {
    if (qui.value) {
      await disattiva()
      qui.value = false
      return true
    }
    qui.value = await attiva(chiave.value)
    negate.value = permesso() === 'denied'
    return true
  })
}

async function salva() {
  salvate.value = false
  const dati = await esegui(() => api.scegliPreferenzePush({ ...scelte }))
  if (dati) salvate.value = true
}
</script>

<template>
  <div v-if="disponibili" class="mb-7">
    <h2 class="h5 mb-1">Notifiche sul telefono</h2>
    <p class="fg-2 small">
      Compaiono anche a telefono bloccato, quindi dicono solo di cosa si tratta: i dettagli sono
      nell'app. Si aggiungono alle email, che scegli qui sotto.
    </p>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div class="card card-body">
      <p v-if="!supportate && !appInstallata()" class="small mb-3">
        Su iPhone le notifiche funzionano solo con l'app aggiunta alla schermata Home: tocca il
        tasto Condividi e poi <strong>Aggiungi alla schermata Home</strong>.
      </p>
      <p v-else-if="!supportate" class="small mb-3">Questo browser non permette le notifiche.</p>
      <p v-else-if="negate" class="small mb-3">
        Hai rifiutato le notifiche su questo dispositivo: per riattivarle cambia il permesso nelle
        impostazioni del browser o del telefono.
      </p>
      <div v-else class="d-flex flex-wrap align-items-center gap-3 mb-3">
        <button
          type="button"
          class="btn btn-sm"
          :class="qui ? 'btn-outline theme-primary' : 'btn-solid theme-primary'"
          :disabled="inCorso"
          @click="cambiaQui"
        >
          {{ qui ? 'Disattiva su questo dispositivo' : 'Attiva su questo dispositivo' }}
        </button>
        <span class="small fg-2">{{ qui ? 'Attive qui.' : 'Non attive qui.' }}</span>
      </div>
      <form @submit.prevent="salva">
        <p class="small mb-1">Cosa vuoi ricevere, su tutti i tuoi dispositivi:</p>
        <div v-for="v in VOCI" :key="v.chiave" class="form-field">
          <div class="switch">
            <input
              :id="`push-${v.chiave}`"
              v-model="scelte[v.chiave]"
              type="checkbox"
              role="switch"
            />
          </div>
          <label :for="`push-${v.chiave}`">{{ v.etichetta }}</label>
        </div>
        <div v-if="sessione.capo" class="form-field">
          <div class="switch">
            <input id="push-riepiloghi" v-model="scelte.riepiloghi" type="checkbox" role="switch" />
          </div>
          <label for="push-riepiloghi">
            Per i capi: promemoria dei verbali, correzioni e iscrizioni da decidere
          </label>
        </div>
        <div class="d-flex align-items-center gap-3 mt-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva
          </button>
          <span v-if="salvate" class="small fg-success">Salvate.</span>
        </div>
      </form>
    </div>
  </div>
</template>
