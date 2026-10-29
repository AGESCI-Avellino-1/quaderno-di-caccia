<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import {
  api,
  euro,
  giustificativoSpesa,
  nomeUnita,
  PERCORSO_SPESE_ANTICIPATE,
  type SpesaAnticipata,
  type Unita,
} from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'
import { leggiGiustificativo } from '@/offline/giustificativo'
import { scrivi } from '@/offline/outbox'
import { useSessioneStore } from '@/stores/sessione'

// A capo records what they paid out of pocket, with the receipt photo, also offline;
// the treasurer refunds it from a cash box (DEC-86). The API shows each capo their own.
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()
const spese = ref<SpesaAnticipata[]>([])
const unita = ref<Unita[]>([])
const esito = ref('')
const oggi = () => new Date().toLocaleDateString('sv')
const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')

const modulo = reactive({
  data: oggi(),
  importo: '',
  descrizione: '',
  unita_id: null as number | null,
  giustificativo: '',
})

async function carica() {
  const tutte = (await esegui(() => api.speseAnticipate())) ?? []
  const mia = sessione.profilo?.persona?.id
  spese.value = tutte.filter((s) => s.capo_id === mia)
}

onMounted(async () => {
  unita.value = (await esegui(() => api.unita())) ?? []
  await carica()
})

async function scegliFile(evento: Event) {
  const file = (evento.target as HTMLInputElement).files?.[0]
  if (!file) return
  modulo.giustificativo = (await esegui(() => leggiGiustificativo(file))) ?? ''
}

async function registra() {
  const importo = Number(modulo.importo).toFixed(2)
  const risultato = await esegui(() =>
    scrivi({
      metodo: 'POST',
      percorso: PERCORSO_SPESE_ANTICIPATE,
      corpo: { ...modulo, importo },
      // Stored in clear in the queue: no names, no descriptions.
      descrizione: `Spesa anticipata di ${euro(importo)}`,
    }),
  )
  if (!risultato) return
  Object.assign(modulo, { data: oggi(), importo: '', descrizione: '', giustificativo: '' })
  esito.value = risultato.inCoda
    ? 'Spesa salvata sul telefono: arriverà al tesoriere appena torna la rete.'
    : 'Spesa registrata: il tesoriere la rimborserà.'
  if (!risultato.inCoda) await carica()
}
</script>

<template>
  <section>
    <h1 class="h4 mb-1">Le mie spese</h1>
    <p class="fg-2 small">
      Quello che hai pagato di tasca tua per il gruppo: con la foto dello scontrino, il tesoriere te
      lo rimborsa.
    </p>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>

    <form class="card card-body mb-5" @submit.prevent="registra">
      <div class="row g-3">
        <div class="md:col-4">
          <label class="form-label small" for="spesa-data">Data</label>
          <input
            id="spesa-data"
            v-model="modulo.data"
            type="date"
            :max="oggi()"
            class="form-control form-control-sm"
            required
          />
        </div>
        <div class="md:col-4">
          <label class="form-label small" for="spesa-importo">Importo (€)</label>
          <input
            id="spesa-importo"
            v-model="modulo.importo"
            type="number"
            min="0.01"
            step="0.01"
            class="form-control form-control-sm"
            required
          />
        </div>
        <div class="md:col-4">
          <label class="form-label small" for="spesa-unita">Per l'unità</label>
          <select id="spesa-unita" v-model="modulo.unita_id" class="form-control form-control-sm">
            <option :value="null">Gruppo</option>
            <option v-for="u in unita" :key="u.id" :value="u.id">{{ nomeUnita(u) }}</option>
          </select>
        </div>
        <div class="col-12">
          <label class="form-label small" for="spesa-descrizione">Cosa hai comprato</label>
          <input
            id="spesa-descrizione"
            v-model="modulo.descrizione"
            class="form-control form-control-sm"
            required
          />
        </div>
        <div class="col-12">
          <label class="form-label small" for="spesa-foto">Foto dello scontrino</label>
          <input
            id="spesa-foto"
            type="file"
            accept="image/*,application/pdf"
            capture="environment"
            class="form-control form-control-sm"
            @change="scegliFile"
          />
        </div>
      </div>
      <button
        type="submit"
        class="btn btn-sm btn-solid theme-primary align-self-start mt-3"
        :disabled="inCorso"
      >
        Registra la spesa
      </button>
    </form>

    <p v-if="!spese.length && !inCorso" class="fg-2">Nessuna spesa registrata.</p>
    <ul class="list-group">
      <li v-for="s in spese" :key="s.id" class="list-group-item">
        <div class="d-flex flex-wrap justify-content-between gap-3">
          <span>{{ data(s.data) }} · {{ s.descrizione }}</span>
          <strong>{{ euro(s.importo) }}</strong>
        </div>
        <div class="small">
          <span v-if="s.stato === 'rimborsata'" class="badge theme-success">
            Rimborsata il {{ data(s.rimborsata_il!) }}
          </span>
          <span v-else-if="s.stato === 'respinta'" class="badge theme-danger">
            Respinta: {{ s.motivo_rifiuto }}
          </span>
          <span v-else class="badge theme-warning">Da rimborsare</span>
          <a
            v-if="s.ha_giustificativo"
            :href="giustificativoSpesa(s.id)"
            target="_blank"
            class="ms-3"
          >
            Giustificativo
          </a>
        </div>
      </li>
    </ul>
  </section>
</template>
