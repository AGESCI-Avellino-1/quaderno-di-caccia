<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { ErroreApi } from '@/api/http'
import { api, type Percorso } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The scout path (DEC-287): every period as ragazzo and as capo, in this group and in
// others, one per line, and the year of joining the group. The capi, the person and the
// parents of a minor read it; the capo for themself and the capigruppo complete it.
// Online only.
const props = defineProps<{ persona: number }>()
const { errore, inCorso, esegui } = useErrore()
const percorso = ref<Percorso | null>(null)

onMounted(async () => {
  try {
    percorso.value = await api.percorso(props.persona)
  } catch (e) {
    // Not one to see: nothing to show.
    if (!(e instanceof ErroreApi && e.stato === 404)) throw e
  }
})

const annoCorrente =
  new Date().getMonth() >= 9 ? new Date().getFullYear() + 1 : new Date().getFullYear()
const nuovo = reactive({
  aperto: false,
  gruppo: '',
  unita: '',
  ruolo: 'RAGAZZO',
  anno_inizio: annoCorrente - 1,
  anno_fine: annoCorrente - 1,
})

async function aggiungi() {
  const esito = await esegui(() =>
    api.nuovoPeriodoPercorso(props.persona, {
      gruppo: nuovo.gruppo,
      unita: nuovo.unita,
      ruolo: nuovo.ruolo,
      anno_inizio: nuovo.anno_inizio,
      anno_fine: nuovo.anno_fine,
    }),
  )
  if (esito) {
    percorso.value = esito
    Object.assign(nuovo, { aperto: false, gruppo: '', unita: '' })
  }
}

async function togli(id: number) {
  percorso.value = (await esegui(() => api.togliPeriodoPercorso(id))) ?? percorso.value
}
</script>

<template>
  <section v-if="percorso" class="card card-body mb-5">
    <div class="d-flex align-items-center gap-3 mb-3">
      <h2 class="h5 mb-0">Percorso scout</h2>
      <button
        v-if="percorso.puo_modificare && !nuovo.aperto"
        type="button"
        class="btn btn-sm btn-outline theme-primary ms-auto"
        @click="nuovo.aperto = true"
      >
        Aggiungi un periodo
      </button>
    </div>
    <p v-if="percorso.anno_ingresso" class="small mb-3">
      Nel gruppo dal {{ percorso.anno_ingresso }}.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <form v-if="nuovo.aperto" class="mb-5" @submit.prevent="aggiungi">
      <div class="row g-3">
        <div class="col-12 md:col-6">
          <label class="form-label small" for="perc-unita">Unità</label>
          <input
            id="perc-unita"
            v-model="nuovo.unita"
            class="form-control form-control-sm"
            maxlength="160"
            placeholder="Es. Reparto Orsa Maggiore"
            required
          />
        </div>
        <div class="col-12 md:col-6">
          <label class="form-label small" for="perc-gruppo">Gruppo</label>
          <input
            id="perc-gruppo"
            v-model="nuovo.gruppo"
            class="form-control form-control-sm"
            maxlength="160"
            placeholder="Vuoto se era il nostro gruppo"
          />
        </div>
        <div class="col-12 md:col-4">
          <label class="form-label small" for="perc-ruolo">Come</label>
          <select id="perc-ruolo" v-model="nuovo.ruolo" class="form-control form-control-sm">
            <option value="RAGAZZO">Ragazzo/a</option>
            <option value="CAPO">Capo</option>
          </select>
        </div>
        <div class="col-6 md:col-4">
          <label class="form-label small" for="perc-dal">Dall'anno (fine)</label>
          <input
            id="perc-dal"
            v-model.number="nuovo.anno_inizio"
            type="number"
            min="1951"
            :max="annoCorrente"
            class="form-control form-control-sm"
            required
          />
        </div>
        <div class="col-6 md:col-4">
          <label class="form-label small" for="perc-al">All'anno (fine)</label>
          <input
            id="perc-al"
            v-model.number="nuovo.anno_fine"
            type="number"
            min="1951"
            :max="annoCorrente"
            class="form-control form-control-sm"
            required
          />
        </div>
      </div>
      <p class="small fg-2 mt-1 mb-3">
        L'anno associativo si indica con l'anno in cui finisce: 2014/15 è 2015.
      </p>
      <div class="d-flex gap-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="nuovo.aperto = false">
          Annulla
        </button>
      </div>
    </form>
    <p v-if="!percorso.periodi.length" class="small fg-2 mb-0">Nessun periodo registrato.</p>
    <ul v-else class="list-group">
      <li
        v-for="(p, n) in percorso.periodi"
        :key="p.id ?? `unita-${n}`"
        class="list-group-item small"
      >
        <strong>{{ p.unita }}</strong
        >, {{ p.anni }}
        <span class="fg-2">· {{ p.ruolo_nome }} · {{ p.gruppo }}</span>
        <span v-if="p.ricostruito" class="badge theme-secondary ms-1">ricostruito</span>
        <button
          v-if="percorso.puo_modificare && p.rimovibile && p.id"
          type="button"
          class="btn btn-sm btn-link py-0"
          :disabled="inCorso"
          @click="togli(p.id)"
        >
          Togli
        </button>
      </li>
    </ul>
  </section>
</template>
