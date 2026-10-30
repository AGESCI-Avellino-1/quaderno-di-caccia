<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { api, type Dispositivo } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { BiometriaNonDisponibile, biometriaForseDisponibile } from '@/sicurezza/biometria'
import {
  attivaBiometria,
  biometriaAttiva,
  cancella,
  disattivaBiometria,
  stato,
} from '@/sicurezza/cassaforte'
import ImpersonazioniMie from '@/components/ImpersonazioniMie.vue'
import { useSessioneStore } from '@/stores/sessione'

// Own devices; a capogruppo can see and disconnect anyone's lost phone (DEC-23, DEC-97).
const sessione = useSessioneStore()
const router = useRouter()
const { errore, inCorso, esegui } = useErrore()
const dispositivi = ref<Dispositivo[]>([])
const tutti = ref(false)
const daConfermare = ref<string | null>(null)
const biometriaPossibile = ref(false)
const avviso = ref<string | null>(null)

async function carica() {
  dispositivi.value = (await esegui(() => api.dispositivi(tutti.value))) ?? []
}

onMounted(async () => {
  biometriaPossibile.value = await biometriaForseDisponibile()
  await carica()
})
watch(tutti, carica)

async function scollega(d: Dispositivo) {
  const fatto = await esegui(() => api.revocaDispositivo(d.id))
  daConfermare.value = null
  if (!fatto) return
  if (d.corrente) {
    await cancella('revocato')
    return
  }
  await carica()
}

async function biometria(attiva: boolean) {
  avviso.value = null
  try {
    if (attiva) await attivaBiometria(sessione.profilo!.email)
    else await disattivaBiometria()
  } catch (e) {
    avviso.value =
      e instanceof BiometriaNonDisponibile ? e.message : 'Operazione annullata o non riuscita.'
  }
}

const data = (iso: string) => new Date(iso).toLocaleString('it-IT')
</script>

<template>
  <section>
    <h1 class="h4 mb-5">Dispositivi</h1>

    <div class="card card-body mb-5">
      <h2 class="h6">Questo telefono</h2>
      <p v-if="stato === 'solo_online'" class="small mb-3">
        Nessun dato salvato qui: l'app funziona solo con la rete.
      </p>
      <p v-else class="small mb-3">Dati salvati qui cifrati, sbloccabili con il PIN.</p>
      <div class="d-flex flex-wrap gap-3">
        <button
          v-if="stato === 'sbloccata' && biometriaPossibile && !biometriaAttiva"
          type="button"
          class="btn btn-sm btn-outline theme-primary"
          @click="biometria(true)"
        >
          Attiva impronta o volto
        </button>
        <button
          v-if="biometriaAttiva"
          type="button"
          class="btn btn-sm btn-outline theme-secondary"
          @click="biometria(false)"
        >
          Disattiva impronta o volto
        </button>
        <button
          type="button"
          class="btn btn-sm btn-outline theme-secondary"
          @click="router.push({ name: 'protezione', query: { prossima: '/dispositivi' } })"
        >
          {{ stato === 'solo_online' ? 'Attiva la protezione con PIN' : 'Cambia PIN' }}
        </button>
      </div>
      <p v-if="avviso" class="small fg-danger mt-3 mb-0">{{ avviso }}</p>
    </div>

    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div v-if="sessione.capogruppo" class="form-field mb-3">
      <input id="tutti" v-model="tutti" class="switch" type="checkbox" role="switch" />
      <label for="tutti">Tutti i dispositivi del gruppo</label>
    </div>
    <p v-if="inCorso" class="fg-2">Caricamento…</p>
    <ul class="list-group">
      <li v-for="d in dispositivi" :key="d.id" class="list-group-item">
        <div class="d-flex flex-wrap align-items-center gap-3">
          <strong>{{ d.nome }}</strong>
          <span v-if="d.corrente" class="badge theme-primary">questo</span>
          <span v-if="d.revocato_il" class="badge theme-secondary">scollegato</span>
          <span v-if="tutti" class="small fg-2">{{ d.utente }}</span>
          <span class="small fg-2 ms-auto">ultimo collegamento {{ data(d.ultimo_contatto) }}</span>
        </div>
        <div v-if="!d.revocato_il" class="mt-3">
          <template v-if="daConfermare === d.id">
            <span class="small me-3">
              I dati su quel dispositivo verranno cancellati al prossimo collegamento.
            </span>
            <button
              type="button"
              class="btn btn-sm btn-solid theme-danger me-1"
              @click="scollega(d)"
            >
              Scollega
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="daConfermare = null">
              Annulla
            </button>
          </template>
          <button
            v-else
            type="button"
            class="btn btn-sm btn-outline theme-danger"
            @click="daConfermare = d.id"
          >
            Scollega…
          </button>
        </div>
      </li>
      <li v-if="!dispositivi.length && !inCorso" class="list-group-item fg-2">
        Nessun dispositivo registrato.
      </li>
    </ul>

    <ImpersonazioniMie class="mt-5" />
  </section>
</template>
