<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { api, type CandidatoInvito, type EsitoInviti } from '@/api/qdc'
import Icona from '@/components/Icona.vue'
import { useErrore } from '@/composables/useErrore'

// Several invitations at once (DEC-308): who of the list may get one now (parents and
// adults with an email of their own, no account, no invitation still valid; the server
// decides), ticked and sent together. The emails go out a few at a time (DEC-311).
// Online only: nothing is kept on the device.
const props = defineProps<{ unita?: number; tipo: 'soci' | 'genitori' }>()
const attivo = defineModel<boolean>('attivo', { default: false })
const { errore, inCorso, esegui } = useErrore()

const candidati = ref<CandidatoInvito[] | null>(null)
const scelti = ref(new Set<number>())
const esito = ref<EsitoInviti | null>(null)

async function apri() {
  attivo.value = true
  esito.value = null
  candidati.value = (await esegui(() => api.candidatiInvito(props.unita, props.tipo))) ?? []
  scelti.value = new Set()
}
watch(
  () => [props.unita, props.tipo],
  () => attivo.value && apri(),
)

const tutti = computed(() => candidati.value?.length ?? 0)
function alterna(id: number) {
  const nuovi = new Set(scelti.value)
  if (nuovi.has(id)) nuovi.delete(id)
  else nuovi.add(id)
  scelti.value = nuovi
}
function tuttiONessuno() {
  scelti.value =
    scelti.value.size === tutti.value ? new Set() : new Set(candidati.value!.map((c) => c.id))
}

async function invia() {
  const risposta = await esegui(() => api.invitaMolti([...scelti.value]))
  if (!risposta) return
  esito.value = risposta
  candidati.value = (await esegui(() => api.candidatiInvito(props.unita, props.tipo))) ?? []
  scelti.value = new Set()
}
</script>

<template>
  <div class="mb-3">
    <button v-if="!attivo" type="button" class="btn btn-sm btn-outline theme-primary" @click="apri">
      <Icona nome="envelope-paper" /> Invita chi non ha un account
    </button>
    <div v-else class="card card-body">
      <p class="small mb-3">
        Qui ci sono i genitori e i maggiorenni con un'email che non hanno ancora un account né un
        invito valido. Spunta chi invitare e tocca <strong>Manda gli inviti</strong>: le email
        partono un po' alla volta. I ragazzi minorenni si invitano con il link personale, dalla loro
        scheda.
      </p>
      <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
      <div v-if="esito" class="alert theme-success small" role="status">
        <div>
          Inviti mandati: {{ esito.invitati }}.
          <ul v-if="esito.saltati.length" class="mb-0">
            <li v-for="s in esito.saltati" :key="s.id">
              {{ s.nome }} {{ s.cognome }}: {{ s.motivo }}
            </li>
          </ul>
        </div>
      </div>
      <p v-if="candidati && !candidati.length" class="small fg-2">Nessuno da invitare qui.</p>
      <div v-else-if="candidati" class="list-group mb-3">
        <label
          v-for="c in candidati"
          :key="c.id"
          class="list-group-item list-group-item-action d-flex flex-wrap align-items-center gap-3"
        >
          <input
            type="checkbox"
            class="check"
            :checked="scelti.has(c.id)"
            @change="alterna(c.id)"
          />
          <span class="me-auto">{{ c.cognome }} {{ c.nome }}</span>
          <span class="small fg-2 text-break">{{ c.email }}</span>
        </label>
      </div>
      <div class="d-flex flex-wrap align-items-center gap-3">
        <button
          type="button"
          class="btn btn-sm btn-solid theme-primary"
          :disabled="!scelti.size || inCorso"
          @click="invia"
        >
          Manda gli inviti ({{ scelti.size }})
        </button>
        <button v-if="tutti" type="button" class="btn btn-sm btn-link" @click="tuttiONessuno">
          {{ scelti.size === tutti ? 'Nessuno' : 'Tutti' }}
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="attivo = false">Chiudi</button>
      </div>
    </div>
  </div>
</template>
