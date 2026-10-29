<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api, type Campo, type SchedaCampo, type Unita } from '@/api/qdc'
import SchedaSanitaria from '@/components/SchedaSanitaria.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache, leggiDallaCache } from '@/offline/cache'
import { protetta } from '@/sicurezza/cassaforte'

// "Al campo": contacts, medicines, allergies of a unit, readable with no network
// (DEC-55, DEC-95). Downloaded only to a protected, registered device (DEC-97).
const route = useRoute()
const router = useRouter()
const { errore, inCorso, esegui } = useErrore()

const unita = ref<Unita[]>([])
const scelta = ref<number | undefined>(route.query.unita ? Number(route.query.unita) : undefined)
const campo = ref<Campo | null>(null)
const copiaDel = ref<string | null>(null)
const filtro = ref('')
const soloConDati = ref(false)
const puoSalvare = protetta()

const eta = (nascita: string | null) => {
  if (!nascita) return null
  const n = new Date(nascita)
  const oggi = new Date()
  let anni = oggi.getFullYear() - n.getFullYear()
  if (oggi < new Date(oggi.getFullYear(), n.getMonth(), n.getDate())) anni--
  return anni
}

const haDati = (p: SchedaCampo) => p.sanitarie.allergie.length > 0 || p.sanitarie.farmaci.length > 0
const haGrave = (p: SchedaCampo) => p.sanitarie.allergie.some((a) => a.gravita === 'GRAVE')

const persone = computed(() => {
  const testo = filtro.value.trim().toLowerCase()
  return (campo.value?.persone ?? []).filter(
    (p) =>
      (!testo || `${p.cognome} ${p.nome}`.toLowerCase().includes(testo)) &&
      (!soloConDati.value || haDati(p) || !p.sanitarie.compilate),
  )
})
const nonCompilate = computed(
  () => (campo.value?.persone ?? []).filter((p) => !p.sanitarie.compilate).length,
)

async function mostraCopia() {
  campo.value = null
  copiaDel.value = null
  if (scelta.value === undefined) return
  const copia = await esegui(() => leggiDallaCache<Campo>(`campo:${scelta.value}`))
  if (copia) {
    campo.value = copia.dati
    copiaDel.value = copia.copiaDel
  }
}

async function aggiorna() {
  if (scelta.value === undefined) return
  const id = scelta.value
  const letto = await esegui(() => leggiConCache(`campo:${id}`, () => api.campo(id)))
  if (letto) {
    campo.value = letto.dati
    copiaDel.value = letto.copiaDel
  }
}

onMounted(async () => {
  const lette = await esegui(() => leggiConCache('unita', api.unita))
  if (lette) unita.value = lette.dati
  await mostraCopia()
})
watch(scelta, async (valore) => {
  await router.replace({ query: valore === undefined ? {} : { unita: valore } })
  await mostraCopia()
})
</script>

<template>
  <section>
    <h1 class="h4 mb-5">Al campo</h1>
    <div v-if="!puoSalvare" class="alert theme-warning">
      <div>
        Su questo telefono non salvi dati: senza rete non li vedrai.
        <RouterLink :to="{ name: 'protezione', query: { prossima: '/campo' } }"
          >Attiva la protezione con PIN</RouterLink
        >
      </div>
    </div>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>

    <div class="row g-3 mb-5">
      <div class="col-12 md:col-5">
        <select v-model="scelta" class="form-control" aria-label="Unità">
          <option :value="undefined" disabled>Scegli l'unità</option>
          <option v-for="u in unita" :key="u.id" :value="u.id">{{ u.nome }}</option>
        </select>
      </div>
      <div class="col-auto">
        <button
          type="button"
          class="btn btn-solid theme-primary"
          :disabled="scelta === undefined || inCorso"
          @click="aggiorna"
        >
          {{ campo ? 'Aggiorna' : 'Scarica sul telefono' }}
        </button>
      </div>
    </div>

    <template v-if="campo">
      <p class="small fg-2">
        {{ campo.unita }} · scaricati il
        {{ new Date(copiaDel ?? campo.scaricato_il).toLocaleString('it-IT') }}
        <template v-if="nonCompilate">
          · <strong>{{ nonCompilate }} senza farmaci e allergie compilati</strong></template
        >
      </p>
      <div class="d-flex flex-wrap gap-5 align-items-center mb-5">
        <input
          v-model="filtro"
          class="form-control"
          style="max-width: 20rem"
          type="search"
          placeholder="Cerca per nome"
        />
        <div class="form-field">
          <input
            id="solo-con-dati"
            v-model="soloConDati"
            class="switch"
            type="checkbox"
            role="switch"
          />
          <label for="solo-con-dati">Solo con farmaci o allergie (e non compilati)</label>
        </div>
      </div>

      <div class="row g-5">
        <div v-for="p in persone" :key="p.id" class="col-12 lg:col-6">
          <article class="card h-100" :class="{ 'border-danger border-2': haGrave(p) }">
            <div class="card-body">
              <h2 class="h6 mb-1">
                {{ p.cognome }} {{ p.nome }}
                <span v-if="eta(p.data_nascita) !== null" class="fg-2 fw-normal">
                  · {{ eta(p.data_nascita) }} anni</span
                >
              </h2>
              <SchedaSanitaria :dati="p.sanitarie" compatta />
              <ul v-if="p.contatti.length" class="list-unstyled small mb-0 mt-3">
                <li v-for="(c, i) in p.contatti" :key="i">
                  {{ c.nome }} ({{ c.relazione }}):
                  <a :href="`tel:${c.cellulare}`">{{ c.cellulare }}</a>
                </li>
              </ul>
            </div>
          </article>
        </div>
      </div>
    </template>
    <p v-else-if="scelta !== undefined && !inCorso" class="fg-2">
      Nessuna copia su questo telefono: scaricala finché c'è rete.
    </p>
  </section>
</template>
