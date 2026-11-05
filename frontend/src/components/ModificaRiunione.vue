<script setup lang="ts">
import { defineAsyncComponent, onMounted, reactive, ref } from 'vue'

import { api, type DettaglioEvento, type Localita, type NuovaLocalita } from '@/api/qdc'
import SceltaLocalita from '@/components/SceltaLocalita.vue'
import { useErrore } from '@/composables/useErrore'

// One meeting (DEC-310): moved, another place, with the uniform or not, notes written
// with the text editor. Moving it tells the invited by email; notes and uniform do not.
// Online only, like creating it.
const EditorTesto = defineAsyncComponent(() => import('@/components/EditorTesto.vue'))
const props = defineProps<{ riunione: DettaglioEvento }>()
const emit = defineEmits<{ salvata: []; chiusa: [] }>()
const { errore, inCorso, esegui } = useErrore()
const localita = ref<Localita[]>([])

const inLocale = (iso: string) => {
  const d = new Date(iso)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString()
}
const r = props.riunione
const dati = reactive({
  giorno: inLocale(r.inizio).slice(0, 10),
  ora_inizio: inLocale(r.inizio).slice(11, 16),
  ora_fine: inLocale(r.fine).slice(11, 16),
  localita: {
    id: r.localita?.id ?? null,
    nuova: null as NuovaLocalita | null,
  },
  // 'serie': as its series (only for a meeting of a series).
  uniforme: (r.serie_id ? 'serie' : r.uniforme ? 'si' : 'no') as 'serie' | 'si' | 'no',
  informazioni: r.informazioni ?? '',
})

onMounted(async () => {
  try {
    localita.value = await api.localita()
  } catch {
    localita.value = []
  }
})

async function salva() {
  const istante = (ora: string) => new Date(`${dati.giorno}T${ora}`).toISOString()
  const fatta = await esegui(() =>
    api.modificaRiunione(r.id, {
      inizio: istante(dati.ora_inizio),
      fine: istante(dati.ora_fine),
      localita_id: dati.localita.nuova ? null : dati.localita.id,
      nuova_localita: dati.localita.nuova,
      // A place written before the list existed stays, unless another one is chosen.
      luogo: !dati.localita.id && !dati.localita.nuova && !r.localita ? r.luogo : '',
      uniforme: dati.uniforme === 'serie' ? null : dati.uniforme === 'si',
      informazioni: dati.informazioni,
    }),
  )
  if (fatta) emit('salvata')
}
</script>

<template>
  <form class="card card-body" @submit.prevent="salva">
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div class="row g-3">
      <div class="md:col-4">
        <label class="form-label small" for="mr-giorno">Giorno</label>
        <input
          id="mr-giorno"
          v-model="dati.giorno"
          type="date"
          class="form-control form-control-sm"
          required
        />
      </div>
      <div class="md:col-4">
        <label class="form-label small" for="mr-inizio">Dalle</label>
        <input
          id="mr-inizio"
          v-model="dati.ora_inizio"
          type="time"
          class="form-control form-control-sm"
          required
        />
      </div>
      <div class="md:col-4">
        <label class="form-label small" for="mr-fine">Alle</label>
        <input
          id="mr-fine"
          v-model="dati.ora_fine"
          type="time"
          class="form-control form-control-sm"
          required
        />
      </div>
      <div class="col-12">
        <SceltaLocalita v-model="dati.localita" id-campo="mr-localita" :localita="localita" />
      </div>
      <div class="md:col-6">
        <label class="form-label small" for="mr-uniforme">Uniforme</label>
        <select id="mr-uniforme" v-model="dati.uniforme" class="form-control form-control-sm">
          <option v-if="riunione.serie_id" value="serie">Come le altre riunioni</option>
          <option value="si">Con l'uniforme</option>
          <option value="no">Senza uniforme</option>
        </select>
      </div>
      <div class="col-12">
        <EditorTesto v-model="dati.informazioni" etichetta="Informazioni per questa riunione" />
      </div>
    </div>
    <p class="form-text mt-3 mb-0">
      Se cambi giorno, orari o località, gli invitati ricevono un'email; per le informazioni e
      l'uniforme no.
    </p>
    <div class="d-flex gap-3 mt-3">
      <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
        Salva
      </button>
      <button type="button" class="btn btn-sm btn-link" @click="emit('chiusa')">Annulla</button>
    </div>
  </form>
</template>
