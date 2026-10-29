<script setup lang="ts">
import { ref, watch } from 'vue'

import { api, type PersonaDettaglio, type Sanitarie } from '@/api/qdc'
import AccountPersona from '@/components/AccountPersona.vue'
import CopiaLocale from '@/components/CopiaLocale.vue'
import CorrezioniPersona from '@/components/CorrezioniPersona.vue'
import DerogheSquadriglia from '@/components/DerogheSquadriglia.vue'
import SchedaSanitaria from '@/components/SchedaSanitaria.vue'
import TelefonoSquadriglia from '@/components/TelefonoSquadriglia.vue'
import VisibilitaGenitori from '@/components/VisibilitaGenitori.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'
import { useSessioneStore } from '@/stores/sessione'

const props = defineProps<{ id: number }>()
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()
const persona = ref<PersonaDettaglio | null>(null)
const copiaDel = ref<string | null>(null)
const sanitarie = ref<Sanitarie | null>(null)

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
      <CopiaLocale :del="copiaDel" />
      <dl class="row">
        <template v-if="persona.codice_socio">
          <dt class="col-5 md:col-3">Codice socio</dt>
          <dd class="col-7 md:col-9">
            {{ persona.codice_socio }}
            <span v-if="persona.codice_provvisorio" class="badge theme-warning ms-1">
              provvisorio, in attesa di BuonaStrada
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
      <section v-if="sanitarie" class="card card-body mb-5">
        <div class="d-flex align-items-center">
          <h2 class="h5 mb-0">Farmaci, allergie e alimentazione</h2>
          <RouterLink
            v-if="sanitarie.puo_modificare"
            :to="{ name: 'sanitarie', params: { id: persona.id } }"
            class="btn btn-sm btn-outline theme-primary ms-auto"
            >{{ sanitarie.compilate ? 'Modifica' : 'Compila' }}</RouterLink
          >
        </div>
        <SchedaSanitaria :dati="sanitarie" />
      </section>
      <VisibilitaGenitori :id="persona.id" />
      <CorrezioniPersona :id="persona.id" @cambiato="carica(persona.id)" />
      <TelefonoSquadriglia :id="persona.id" />
      <DerogheSquadriglia :id="persona.id" />
      <AccountPersona :id="persona.id" />
      <p v-if="sessione.capogruppo" class="small">
        <RouterLink :to="{ name: 'fascicolo', params: { id: persona.id } }">
          Fascicolo completo e cancellazione (richieste dell'interessato)
        </RouterLink>
      </p>
    </template>
  </section>
</template>
