<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, type CandidatoImpersonazione, type Impersonazione } from '@/api/qdc'
import AvviaImpersonazione from '@/components/AvviaImpersonazione.vue'
import { useErrore } from '@/composables/useErrore'

// Using the app as another user, to help them or check a problem: the capigruppo and
// the administrators who are capi with anyone, the unit staff with its ragazzi and their
// parents (the API decides). Also accounts without a record, e.g. a family still
// completing a registration. The Co.Ca. sees who did it, when and why.
const { errore, inCorso, esegui } = useErrore()
const cerca = ref('')
const trovati = ref<CandidatoImpersonazione[] | null>(null)
const elenco = ref<Impersonazione[]>([])

onMounted(async () => {
  try {
    elenco.value = await api.impersonazioni()
  } catch {
    elenco.value = []
  }
})

async function trova() {
  trovati.value = (await esegui(() => api.candidatiImpersonazione(cerca.value))) ?? []
}

const quando = (iso: string) =>
  new Date(iso).toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'short' })
</script>

<template>
  <section>
    <h1 class="h4">Usa l'app al posto di un altro</h1>
    <p class="small fg-2">
      Per aiutare qualcuno a compilare o per vedere un problema come lo vede lui. Puoi fare quello
      che fa lui, ma non cambiare il suo account (password, email, accessi, dispositivi) né le sue
      scelte personali (consensi, email da ricevere, cosa vedono i genitori). Dura al massimo 30
      minuti; la persona vede chi l'ha fatto e perché.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <form class="d-flex flex-wrap align-items-end gap-3 mb-3" @submit.prevent="trova">
      <div class="flex-grow-1">
        <label class="form-label small" for="cerca-imp">Nome, cognome o email</label>
        <input id="cerca-imp" v-model="cerca" class="form-control form-control-sm" minlength="2" />
      </div>
      <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
        Cerca
      </button>
    </form>
    <template v-if="trovati">
      <p v-if="!trovati.length" class="small">Nessuno che tu possa impersonare.</p>
      <ul v-else class="list-group mb-5">
        <li v-for="c in trovati" :key="c.utente_id" class="list-group-item">
          <div class="mb-1">
            <strong>{{ c.nome }}</strong> <span class="small fg-2">{{ c.email }}</span>
          </div>
          <AvviaImpersonazione :utente="c.utente_id" :nome="c.nome" />
        </li>
      </ul>
    </template>

    <section v-if="elenco.length" class="mt-5">
      <h2 class="h5">Chi l'ha fatto</h2>
      <ul class="list-group small">
        <li v-for="i in elenco" :key="i.id" class="list-group-item">
          <strong>{{ i.impersonatore }}</strong> al posto di <strong>{{ i.impersonato }}</strong
          >, {{ quando(i.iniziata_il) }} – {{ quando(i.finita_il ?? i.scade_il) }}: {{ i.motivo }}
        </li>
      </ul>
    </section>
  </section>
</template>
