<script setup lang="ts">
import { ref, watch } from 'vue'

import { api, trasferimentoJson, type PersonaDettaglio, type Sanitarie } from '@/api/qdc'
import AccountPersona from '@/components/AccountPersona.vue'
import AvviaImpersonazione from '@/components/AvviaImpersonazione.vue'
import CopiaLocale from '@/components/CopiaLocale.vue'
import CorrezioniPersona from '@/components/CorrezioniPersona.vue'
import DerogheSquadriglia from '@/components/DerogheSquadriglia.vue'
import QuotePersona from '@/components/QuotePersona.vue'
import CartaSanitaria from '@/components/CartaSanitaria.vue'
import FotoProfilo from '@/components/FotoProfilo.vue'
import NotePersona from '@/components/NotePersona.vue'
import RegoleRapporto from '@/components/RegoleRapporto.vue'
import SchedaSanitaria from '@/components/SchedaSanitaria.vue'
import { useRete } from '@/composables/useRete'
import TelefonoSquadriglia from '@/components/TelefonoSquadriglia.vue'
import { useErrore } from '@/composables/useErrore'
import { useNomePagina } from '@/composables/useNomePagina'
import { leggiConCache } from '@/offline/cache'
import { useSessioneStore } from '@/stores/sessione'

const props = defineProps<{ id: number }>()
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()
const persona = ref<PersonaDettaglio | null>(null)
useNomePagina(() => persona.value && `${persona.value.nome} ${persona.value.cognome}`)
const copiaDel = ref<string | null>(null)
// Printing and paper dates need the network.
const { online } = useRete()
const sanitarie = ref<Sanitarie | null>(null)
// Whether the user may act as this person (online only; the API decides).
const impersonabile = ref(false)

watch(
  () => props.id,
  async (id) => {
    impersonabile.value = false
    if (!sessione.profilo?.puo_impersonare || sessione.profilo.impersonazione) return
    try {
      impersonabile.value = (await api.impersonabile(id)).puo
    } catch {
      impersonabile.value = false
    }
  },
  { immediate: true },
)

// Health essentials: shown only if the backend lets this user see them (404 otherwise).
async function caricaSanitarie(id: number) {
  sanitarie.value = null
  try {
    sanitarie.value = (await leggiConCache(`sanitarie:${id}`, () => api.sanitarie(id))).dati
  } catch {
    sanitarie.value = null // 404: not visible to this user; offline without a copy
  }
}

// What is shown depends on the access level computed by the backend (policy.py):
// fields the user may not see arrive as null and are simply not rendered.
async function carica(id: number) {
  const letto = await esegui(() => leggiConCache(`persona:${id}`, () => api.persona(id)))
  persona.value = letto?.dati ?? null
  copiaDel.value = letto?.copiaDel ?? null
  if (letto) await caricaSanitarie(id)
}
watch(() => props.id, carica, { immediate: true })

const formattaData = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
</script>

<template>
  <section>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <p v-if="inCorso" class="fg-2">Caricamento…</p>
    <template v-if="persona">
      <h1 class="h4 mb-1">{{ persona.nome }} {{ persona.cognome }}</h1>
      <p class="fg-2 small">{{ persona.unita.join(' · ') }}</p>
      <p class="small">
        <RouterLink :to="{ name: 'sentiero', params: { id: persona.id } }">
          Sentiero (Progressione Personale)
        </RouterLink>
        <template v-if="persona.livello_accesso !== 'squadriglia'">
          ·
          <RouterLink :to="{ name: 'fascicolo-anno', params: { id: persona.id } }">
            Fascicolo dell'anno
          </RouterLink>
        </template>
        <template v-if="sessione.profilo?.capogruppo && persona.livello_accesso === 'completo'">
          ·
          <a
            :href="trasferimentoJson(persona.id)"
            title="Per un altro gruppo che usa il Quaderno di Caccia"
          >
            Esporta per un altro gruppo
          </a>
        </template>
        <template v-if="persona.fascicolo_capo">
          ·
          <RouterLink :to="{ name: 'fascicolo-capo', params: { id: persona.id } }">
            Servizio e formazione
          </RouterLink>
        </template>
      </p>
      <FotoProfilo v-if="online" :persona="persona" @cambiata="(nuova) => (persona = nuova)" />
      <CopiaLocale :del="copiaDel" />
      <dl class="row">
        <template v-if="persona.codice_socio">
          <dt class="col-5 md:col-3">Codice socio</dt>
          <dd class="col-7 md:col-9">
            {{ persona.codice_socio }}
            <span v-if="persona.codice_provvisorio" class="badge theme-warning ms-1">
              provvisorio, in attesa di BuonaStrada
            </span>
            <span v-if="persona.iscrizione_sospesa" class="badge theme-danger ms-1">
              iscrizione sospesa: scaduto il termine per completarla
            </span>
          </dd>
        </template>
        <template v-if="persona.data_nascita">
          <dt class="col-5 md:col-3">Data di nascita</dt>
          <dd class="col-7 md:col-9">{{ formattaData(persona.data_nascita) }}</dd>
        </template>
        <template v-if="persona.email">
          <dt class="col-5 md:col-3">Email</dt>
          <dd class="col-7 md:col-9">
            <a :href="`mailto:${persona.email}`">{{ persona.email }}</a>
          </dd>
        </template>
        <template v-if="persona.cellulare">
          <dt class="col-5 md:col-3">Cellulare</dt>
          <dd class="col-7 md:col-9">
            <a :href="`tel:${persona.cellulare}`">{{ persona.cellulare }}</a>
          </dd>
        </template>
        <template v-if="persona.indirizzo">
          <dt class="col-5 md:col-3">Indirizzo</dt>
          <dd class="col-7 md:col-9">{{ persona.indirizzo }} {{ persona.comune }}</dd>
        </template>
        <template v-if="persona.consenso_foto !== null">
          <dt class="col-5 md:col-3">Consenso foto</dt>
          <dd class="col-7 md:col-9">{{ persona.consenso_foto ? 'Sì' : 'No' }}</dd>
        </template>
      </dl>
      <RegoleRapporto :persona="persona.id" />
      <section v-if="sanitarie" class="card card-body mb-5">
        <div class="d-flex align-items-center">
          <h2 class="h5 mb-0">Scheda sanitaria</h2>
          <RouterLink
            v-if="sanitarie.puo_modificare"
            :to="{ name: 'sanitarie', params: { id: persona.id } }"
            class="btn btn-sm btn-outline theme-primary ms-auto"
            >{{ sanitarie.compilate ? 'Modifica' : 'Compila' }}</RouterLink
          >
        </div>
        <SchedaSanitaria :dati="sanitarie" />
        <CartaSanitaria
          v-if="online"
          :persona="persona.id"
          :dati="sanitarie"
          @cambiata="(nuovi) => (sanitarie = nuovi)"
        />
      </section>
      <NotePersona :persona="persona.id" />
      <CorrezioniPersona :id="persona.id" @cambiato="carica(persona.id)" />
      <QuotePersona :id="persona.id" />
      <TelefonoSquadriglia :id="persona.id" />
      <DerogheSquadriglia :id="persona.id" />
      <AccountPersona :id="persona.id" />
      <AvviaImpersonazione
        v-if="impersonabile"
        class="mb-5"
        :persona="persona.id"
        :nome="`${persona.nome} ${persona.cognome}`"
      />
      <p v-if="sessione.capogruppo" class="small">
        <RouterLink :to="{ name: 'fascicolo', params: { id: persona.id } }">
          Fascicolo completo e cancellazione (richieste dell'interessato)
        </RouterLink>
      </p>
    </template>
  </section>
</template>
