<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, TIPI_RICHIESTA, type PersonaElenco, type RichiestaDiritti } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Register of requests from data subjects (DEC-102): the capigruppo record them, pass
// them on to the national office and close them; the answer is due within a month.
// Online only: the API answers 403 to anyone else.
const { errore, inCorso, esegui } = useErrore()
const richieste = ref<RichiestaDiritti[]>([])
const persone = ref<PersonaElenco[]>([])
const aperto = ref(false)
// Local date as YYYY-MM-DD (toISOString would give the UTC day around midnight).
const oggi = new Date().toLocaleDateString('sv')
const modulo = reactive({ persona: '', tipo: 'ACCESSO', richiedente: '', ricevuta: oggi, note: '' })

async function carica() {
  richieste.value = (await esegui(() => api.richiesteDiritti())) ?? []
}
onMounted(carica)

async function apri() {
  if (!persone.value.length) persone.value = (await esegui(() => api.persone())) ?? []
  Object.assign(modulo, { persona: '', tipo: 'ACCESSO', richiedente: '', ricevuta: oggi, note: '' })
  aperto.value = true
}

async function registra() {
  const fatta = await esegui(() =>
    api.registraRichiesta({
      persona_id: Number(modulo.persona),
      tipo: modulo.tipo,
      richiedente: modulo.richiedente,
      ricevuta_il: modulo.ricevuta,
      note: modulo.note,
    }),
  )
  if (!fatta) return
  aperto.value = false
  await carica()
}

async function segna(r: RichiestaDiritti, campo: 'inoltrata_nazionale_il' | 'evasa_il') {
  if (await esegui(() => api.aggiornaRichiesta(r.id, { [campo]: oggi }))) await carica()
}

const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
const scaduta = (r: RichiestaDiritti) => !r.evasa_il && r.scadenza < oggi
</script>

<template>
  <section>
    <div class="d-flex align-items-center mb-3">
      <h1 class="h4 mb-0">Richieste degli interessati</h1>
      <button
        v-if="!aperto"
        type="button"
        class="btn btn-sm btn-outline theme-primary ms-auto"
        @click="apri"
      >
        Registra una richiesta
      </button>
    </div>
    <p class="fg-2 small">
      Accesso, copia, rettifica o cancellazione dei dati. Vanno girate all'Ufficio Privacy nazionale
      e chiuse entro un mese. Il fascicolo completo e la cancellazione si fanno dalla scheda della
      persona.
    </p>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>

    <form v-if="aperto" class="card card-body row g-3 mb-5 mx-0" @submit.prevent="registra">
      <div class="col-12 md:col-6">
        <label class="form-label small" for="richiesta-persona">Persona</label>
        <select
          id="richiesta-persona"
          v-model="modulo.persona"
          class="form-control form-control-sm"
          required
        >
          <option value="" disabled>Scegli…</option>
          <option v-for="p in persone" :key="p.id" :value="String(p.id)">
            {{ p.cognome }} {{ p.nome }}
          </option>
        </select>
      </div>
      <div class="col-12 md:col-6">
        <label class="form-label small" for="richiesta-tipo">Cosa chiede</label>
        <select id="richiesta-tipo" v-model="modulo.tipo" class="form-control form-control-sm">
          <option v-for="t in TIPI_RICHIESTA" :key="t.valore" :value="t.valore">
            {{ t.etichetta }}
          </option>
        </select>
      </div>
      <div class="col-12 md:col-8">
        <label class="form-label small" for="richiesta-chi">Chi l'ha chiesta e come</label>
        <input
          id="richiesta-chi"
          v-model="modulo.richiedente"
          class="form-control form-control-sm"
          placeholder="Es. la madre, con un'email al gruppo"
          required
        />
      </div>
      <div class="col-12 md:col-4">
        <label class="form-label small" for="richiesta-data">Ricevuta il</label>
        <input
          id="richiesta-data"
          v-model="modulo.ricevuta"
          type="date"
          class="form-control form-control-sm"
          :max="oggi"
          required
        />
      </div>
      <div class="col-12">
        <label class="form-label small" for="richiesta-note">Note</label>
        <textarea
          id="richiesta-note"
          v-model="modulo.note"
          class="form-control form-control-sm"
          rows="2"
        />
      </div>
      <div class="col-12 d-flex gap-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Registra
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="aperto = false">Annulla</button>
      </div>
    </form>

    <p v-if="!inCorso && !richieste.length" class="fg-2">Nessuna richiesta registrata.</p>
    <ul class="list-group">
      <li v-for="r in richieste" :key="r.id" class="list-group-item small">
        <div class="d-flex flex-wrap align-items-baseline gap-3">
          <RouterLink :to="{ name: 'persona', params: { id: r.persona.id } }">
            {{ r.persona.cognome }} {{ r.persona.nome }}
          </RouterLink>
          <strong>{{ r.tipo_nome }}</strong>
          <span v-if="r.evasa_il" class="badge theme-success"
            >Chiusa il {{ data(r.evasa_il) }}</span
          >
          <span v-else-if="scaduta(r)" class="badge theme-danger">
            Scaduta il {{ data(r.scadenza) }}
          </span>
          <span v-else class="badge theme-warning">Entro il {{ data(r.scadenza) }}</span>
        </div>
        <div>{{ r.richiedente }}, ricevuta il {{ data(r.ricevuta_il) }}</div>
        <div v-if="r.note" class="fg-2" style="white-space: pre-line">{{ r.note }}</div>
        <div class="d-flex flex-wrap align-items-baseline gap-3 mt-1">
          <span v-if="r.inoltrata_nazionale_il" class="fg-2">
            Girata al nazionale il {{ data(r.inoltrata_nazionale_il) }}
          </span>
          <button
            v-else
            type="button"
            class="btn btn-link btn-sm p-0"
            :disabled="inCorso"
            @click="segna(r, 'inoltrata_nazionale_il')"
          >
            Girata al nazionale oggi
          </button>
          <button
            v-if="!r.evasa_il"
            type="button"
            class="btn btn-link btn-sm p-0"
            :disabled="inCorso"
            @click="segna(r, 'evasa_il')"
          >
            Chiusa oggi
          </button>
        </div>
      </li>
    </ul>
  </section>
</template>
