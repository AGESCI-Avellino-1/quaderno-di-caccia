<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { api, valoreLeggibile, type CorrezioneElenco } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// For the capigruppo (DEC-31): corrections made in the app, to forward to the regional
// office by hand (portal or email) and then mark as forwarded. The import closes them
// once BuonaStrada has the new value. Online only: the API answers 403 to anyone else.
const { errore, inCorso, esegui } = useErrore()
const correzioni = ref<CorrezioneElenco[]>([])
const chiuse = ref(false)
const daScartare = ref<number | null>(null)
const motivo = ref('')

async function carica() {
  const elenco = await esegui(() => api.correzioni(!chiuse.value))
  correzioni.value = elenco ?? []
}
watch(chiuse, carica, { immediate: true })

const gruppi = computed(() => [
  {
    titolo: 'Da inoltrare',
    voci: correzioni.value.filter((c) => c.stato === 'IN_ATTESA'),
  },
  {
    titolo: 'Inoltrate, in attesa di BuonaStrada',
    voci: correzioni.value.filter((c) => c.stato === 'INOLTRATA'),
  },
])

async function inoltra(id: number) {
  if (await esegui(() => api.inoltraCorrezione(id))) await carica()
}

function chiediScarto(id: number) {
  daScartare.value = id
  motivo.value = ''
}

async function scarta(id: number) {
  if (!(await esegui(() => api.scartaCorrezione(id, motivo.value)))) return
  daScartare.value = null
  await carica()
}

const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
</script>

<template>
  <section>
    <h1 class="h4 mb-1">Correzioni ai dati di BuonaStrada</h1>
    <p class="fg-2 small">
      Valgono già nell'app. Mandale alla segreteria regionale e poi segnalale come inoltrate: si
      chiudono da sole quando l'importazione le ritrova in BuonaStrada.
    </p>
    <div class="form-field mb-5">
      <input id="mostra-chiuse" v-model="chiuse" type="checkbox" class="switch" role="switch" />
      <label for="mostra-chiuse">Mostra le correzioni chiuse</label>
    </div>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <p v-if="inCorso && !correzioni.length" class="fg-2">Caricamento…</p>

    <template v-if="!chiuse">
      <p v-if="!inCorso && !correzioni.length" class="fg-2">Nessuna correzione da gestire.</p>
      <template v-for="g in gruppi" :key="g.titolo">
        <h2 v-if="g.voci.length" class="h6 mt-5">{{ g.titolo }} ({{ g.voci.length }})</h2>
        <ul v-if="g.voci.length" class="list-group">
          <li v-for="c in g.voci" :key="c.id" class="list-group-item">
            <div class="d-flex flex-wrap align-items-baseline gap-3">
              <RouterLink :to="{ name: 'persona', params: { id: c.persona.id } }">
                {{ c.persona.cognome }} {{ c.persona.nome }}
              </RouterLink>
              <span v-if="c.persona.codice_socio" class="fg-2 small">
                socio {{ c.persona.codice_socio }}
              </span>
              <strong class="small">{{ c.etichetta }}</strong>
            </div>
            <div class="small">
              {{ valoreLeggibile(c.valore_precedente) }} →
              <strong>{{ valoreLeggibile(c.valore_corretto) }}</strong>
            </div>
            <div class="fg-2 small">
              Corretto<template v-if="c.richiesta_da"> da {{ c.richiesta_da }}</template> il
              {{ data(c.creata_il) }}
              <template v-if="c.inoltrata_il"> · inoltrata il {{ data(c.inoltrata_il) }}</template>
            </div>
            <form
              v-if="daScartare === c.id"
              class="d-flex flex-wrap gap-3 mt-3"
              @submit.prevent="scarta(c.id)"
            >
              <input
                v-model="motivo"
                class="form-control form-control-sm"
                aria-label="Motivo dello scarto"
                placeholder="Perché la scarti? Lo vede chi l'ha corretta."
                required
              />
              <button type="submit" class="btn btn-sm btn-solid theme-danger" :disabled="inCorso">
                Scarta e rimetti il valore di prima
              </button>
              <button type="button" class="btn btn-sm btn-link" @click="daScartare = null">
                Annulla
              </button>
            </form>
            <div v-else class="d-flex gap-3 mt-3">
              <button
                v-if="c.stato === 'IN_ATTESA'"
                type="button"
                class="btn btn-sm btn-solid theme-primary"
                :disabled="inCorso"
                @click="inoltra(c.id)"
              >
                Segna come inoltrata
              </button>
              <button type="button" class="btn btn-sm btn-link" @click="chiediScarto(c.id)">
                Scarta
              </button>
            </div>
          </li>
        </ul>
      </template>
    </template>

    <ul v-else class="list-group">
      <li v-for="c in correzioni" :key="c.id" class="list-group-item small">
        <div class="d-flex flex-wrap align-items-baseline gap-3">
          <RouterLink :to="{ name: 'persona', params: { id: c.persona.id } }">
            {{ c.persona.cognome }} {{ c.persona.nome }}
          </RouterLink>
          <strong>{{ c.etichetta }}</strong>
          <span
            class="badge"
            :class="c.stato === 'RECEPITA' ? 'theme-success' : 'theme-secondary'"
            >{{ c.stato_nome }}</span
          >
        </div>
        <div>
          {{ valoreLeggibile(c.valore_precedente) }} → {{ valoreLeggibile(c.valore_corretto) }}
          <template v-if="c.chiusa_il"> · {{ data(c.chiusa_il) }}</template>
        </div>
        <div v-if="c.motivo_scarto" class="fg-2">{{ c.motivo_scarto }}</div>
      </li>
      <li v-if="!inCorso && !correzioni.length" class="list-group-item fg-2">
        Nessuna correzione chiusa.
      </li>
    </ul>
  </section>
</template>
