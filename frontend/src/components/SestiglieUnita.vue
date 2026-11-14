<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, type Sestiglie } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The sestiglie of a branco or cerchio (DEC-312): only groups of children for the turns,
// made by the staff, one at a time for each child, without a capo sestiglia. Online only.
// `nome`: the unit's name, with a linked unit's on the same page (DEC-405).
const props = defineProps<{ unita: number; nome?: string }>()
const { errore, inCorso, esegui } = useErrore()
const dati = ref<Sestiglie | null>(null)
const nuova = ref('')

onMounted(async () => {
  try {
    dati.value = await api.sestiglie(props.unita)
  } catch {
    dati.value = null
  }
})

async function crea() {
  const fatti = await esegui(() => api.creaSestiglia(props.unita, nuova.value))
  if (!fatti) return
  dati.value = fatti
  nuova.value = ''
}

async function metti(evento: Event, persona: number) {
  const sestiglia = Number((evento.target as HTMLSelectElement).value)
  if (!sestiglia) return
  dati.value = (await esegui(() => api.mettiInSestiglia(sestiglia, persona))) ?? dati.value
}

async function togli(membro: number) {
  dati.value = (await esegui(() => api.togliDaSestiglia(membro))) ?? dati.value
}

async function chiudi(sestiglia: number) {
  dati.value = (await esegui(() => api.chiudiSestiglia(sestiglia))) ?? dati.value
}
</script>

<template>
  <section v-if="dati" class="card card-body mb-5">
    <h2 class="h5">
      Sestiglie<template v-if="nome"> · {{ nome }}</template>
    </h2>
    <p class="small fg-2">
      Gruppi di bambini per i turni delle riunioni: ogni bambino è in una sestiglia alla volta.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-for="s in dati.sestiglie" :key="s.id" class="border-top pt-3 mt-3">
      <div class="d-flex align-items-center gap-3">
        <strong>{{ s.nome }}</strong>
        <button type="button" class="btn btn-link btn-sm p-0 ms-auto" @click="chiudi(s.id)">
          chiudi
        </button>
      </div>
      <ul class="list-unstyled small mb-0">
        <li v-for="m in s.membri" :key="m.id" class="d-flex align-items-center gap-3 py-1">
          {{ m.persona.nome }} {{ m.persona.cognome }}
          <button type="button" class="btn btn-link btn-sm p-0" @click="togli(m.id)">togli</button>
        </li>
        <li v-if="!s.membri.length" class="fg-2">Nessun bambino.</li>
      </ul>
    </div>
    <div v-if="dati.senza_sestiglia.length && dati.sestiglie.length" class="border-top pt-3 mt-3">
      <strong>Senza sestiglia</strong>
      <ul class="list-unstyled small mb-0">
        <li
          v-for="b in dati.senza_sestiglia"
          :key="b.id"
          class="d-flex align-items-center flex-wrap gap-3 py-1"
        >
          {{ b.nome }} {{ b.cognome }}
          <select
            class="form-control form-control-sm w-auto ms-auto"
            :aria-label="`Sestiglia di ${b.nome} ${b.cognome}`"
            :disabled="inCorso"
            @change="metti($event, b.id)"
          >
            <option value="">Metti in…</option>
            <option v-for="s in dati.sestiglie" :key="s.id" :value="s.id">{{ s.nome }}</option>
          </select>
        </li>
      </ul>
    </div>
    <form class="d-flex gap-3 mt-3" @submit.prevent="crea">
      <label for="nuova-sestiglia" class="visually-hidden">Nome della sestiglia</label>
      <input
        id="nuova-sestiglia"
        v-model="nuova"
        class="form-control form-control-sm"
        placeholder="Nome della nuova sestiglia"
        required
      />
      <button type="submit" class="btn btn-sm btn-outline theme-primary" :disabled="inCorso">
        Aggiungi
      </button>
    </form>
  </section>
</template>
