<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import { api, type DerogheSquadriglia } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Exceptions to single-sex patrols (gender identity, transition): decided by the Co.Ca.,
// recorded by a capogruppo, visible to capi only (the backend answers 404 to anyone
// else and logs every read). Special-category data: online only, never cached here.
const props = defineProps<{ id: number }>()
const { errore, inCorso, esegui } = useErrore()
const stato = ref<DerogheSquadriglia | null>(null)
const aperto = ref(false)
const daRevocare = ref<number | null>(null)
const modulo = reactive({ reparto: '', sesso: 'F', data: '', motivazione: '' })

async function carica(id: number) {
  try {
    stato.value = await api.deroghe(id)
  } catch {
    stato.value = null
  }
}
watch(() => props.id, carica, { immediate: true })

const visibile = computed(
  () => !!stato.value && (stato.value.deroghe.length > 0 || puoRegistrare.value),
)
const puoRegistrare = computed(() => !!stato.value?.puo_gestire && !!stato.value.reparti.length)

function apri() {
  Object.assign(modulo, {
    reparto: stato.value?.reparti[0]?.valore ?? '',
    sesso: 'F',
    data: '',
    motivazione: '',
  })
  aperto.value = true
}

async function registra() {
  const fatto = await esegui(() =>
    api.registraDeroga(props.id, {
      reparto_id: Number(modulo.reparto),
      sesso_squadriglia: modulo.sesso,
      data_decisione: modulo.data,
      motivazione: modulo.motivazione,
    }),
  )
  if (!fatto) return
  aperto.value = false
  await carica(props.id)
}

async function revoca(id: number) {
  const fatto = await esegui(() => api.revocaDeroga(id))
  daRevocare.value = null
  if (fatto) await carica(props.id)
}

const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
// Local date as YYYY-MM-DD (toISOString would give the UTC day around midnight).
const oggi = () => new Date().toLocaleDateString('sv')
</script>

<template>
  <section v-if="visibile && stato" class="card card-body mb-3">
    <div class="d-flex align-items-center">
      <h2 class="h5 mb-0">Eccezioni sulla squadriglia</h2>
      <button
        v-if="puoRegistrare && !aperto"
        type="button"
        class="btn btn-sm btn-outline-primary ms-auto"
        @click="apri"
      >
        Registra
      </button>
    </div>
    <p class="form-text mb-2">
      Decise dalla Co.Ca., visibili solo ai capi. Ogni lettura resta nel registro degli accessi.
    </p>
    <div v-if="errore" class="alert alert-danger py-2 small" role="alert">{{ errore }}</div>

    <div v-for="d in stato.deroghe" :key="d.id" class="border-top pt-2 mt-1 small">
      <div class="d-flex flex-wrap align-items-baseline gap-2">
        <strong>Squadriglie {{ d.squadriglie_ammesse.toLowerCase() }}</strong>
        <span>di {{ d.reparto }}</span>
        <span v-if="d.valida" class="badge text-bg-success">In vigore</span>
        <span v-else class="badge text-bg-secondary">Non in vigore</span>
        <template v-if="stato.puo_gestire && d.valida">
          <button
            v-if="daRevocare !== d.id"
            type="button"
            class="btn btn-link btn-sm p-0 ms-auto"
            @click="daRevocare = d.id"
          >
            revoca
          </button>
          <span v-else class="ms-auto">
            Revocare da oggi?
            <button
              type="button"
              class="btn btn-sm btn-danger py-0"
              :disabled="inCorso"
              @click="revoca(d.id)"
            >
              Sì
            </button>
            <button type="button" class="btn btn-sm btn-link py-0" @click="daRevocare = null">
              No
            </button>
          </span>
        </template>
      </div>
      <div class="text-body-secondary">
        Decisa in Co.Ca. il {{ data(d.data_decisione) }}
        <template v-if="d.registrata_da">, registrata da {{ d.registrata_da }}</template>
        <template v-if="d.revocata_il">, revocata il {{ data(d.revocata_il) }}</template>
      </div>
      <details>
        <summary>Motivazione</summary>
        <p class="mb-0" style="white-space: pre-line">{{ d.motivazione }}</p>
      </details>
    </div>

    <form v-if="aperto" class="row g-2 mt-1" @submit.prevent="registra">
      <div class="col-12 col-sm-6">
        <label class="form-label small" for="deroga-reparto">Reparto</label>
        <select id="deroga-reparto" v-model="modulo.reparto" class="form-select form-select-sm">
          <option v-for="r in stato.reparti" :key="r.valore" :value="r.valore">
            {{ r.etichetta }}
          </option>
        </select>
      </div>
      <div class="col-6 col-sm-3">
        <label class="form-label small" for="deroga-sesso">Può entrare nelle squadriglie</label>
        <select id="deroga-sesso" v-model="modulo.sesso" class="form-select form-select-sm">
          <option value="F">femminili</option>
          <option value="M">maschili</option>
        </select>
      </div>
      <div class="col-6 col-sm-3">
        <label class="form-label small" for="deroga-data">Decisa in Co.Ca. il</label>
        <input
          id="deroga-data"
          v-model="modulo.data"
          type="date"
          class="form-control form-control-sm"
          :max="oggi()"
          required
        />
      </div>
      <div class="col-12">
        <label class="form-label small" for="deroga-motivazione">Motivazione</label>
        <textarea
          id="deroga-motivazione"
          v-model="modulo.motivazione"
          class="form-control form-control-sm"
          rows="3"
          required
        />
        <p class="form-text">
          Scrivi solo quello che serve: è un dato delicato, lo leggono tutti i capi.
        </p>
      </div>
      <div class="col-12 d-flex gap-2">
        <button type="submit" class="btn btn-sm btn-primary" :disabled="inCorso">Registra</button>
        <button type="button" class="btn btn-sm btn-link" @click="aperto = false">Annulla</button>
      </div>
    </form>
  </section>
</template>
