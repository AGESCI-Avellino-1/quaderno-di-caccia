<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { api, nomeUnita, temaDellaBranca, type Unita, type UnitaIn } from '@/api/qdc'
import CopiaLocale from '@/components/CopiaLocale.vue'
import ModuloUnita from '@/components/ModuloUnita.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'
import { useSessioneStore } from '@/stores/sessione'

const sessione = useSessioneStore()
const router = useRouter()
const { errore, inCorso, esegui } = useErrore()
const unita = ref<Unita[]>([])
const copiaDel = ref<string | null>(null)
const ancheChiuse = ref(false)
const nuova = ref(false)

async function carica() {
  // The offline copy holds the active units only (the "Al campo" view relies on it).
  const letto = ancheChiuse.value
    ? { dati: (await esegui(() => api.unita(true))) ?? [], copiaDel: null }
    : await esegui(() => leggiConCache('unita', () => api.unita()))
  if (letto) {
    unita.value = letto.dati
    copiaDel.value = letto.copiaDel
  }
}
onMounted(carica)
watch(ancheChiuse, carica)

// Units are created by the capigruppo (DEC-10); the backend checks it.
async function crea(dati: UnitaIn) {
  const creata = await esegui(() => api.creaUnita(dati))
  if (creata) await router.push({ name: 'unita-dettaglio', params: { id: creata.id } })
}
</script>

<template>
  <section>
    <div class="d-flex align-items-center flex-wrap gap-3 mb-5">
      <h1 class="h4 mb-0">Unità</h1>
      <button
        v-if="sessione.capogruppo && !nuova"
        type="button"
        class="btn btn-sm btn-outline theme-primary ms-auto"
        @click="nuova = true"
      >
        Nuova unità
      </button>
    </div>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <CopiaLocale :del="copiaDel" />
    <div v-if="nuova" class="card card-body mb-5">
      <ModuloUnita
        :altre="unita"
        :in-corso="inCorso"
        etichetta="Crea unità"
        @salva="crea"
        @annulla="nuova = false"
      />
    </div>
    <div class="list-group mb-3">
      <RouterLink
        v-for="u in unita"
        :key="u.id"
        :to="{ name: 'unita-dettaglio', params: { id: u.id } }"
        class="list-group-item list-group-item-action"
        :data-branca="temaDellaBranca(u.branca)"
      >
        <strong>{{ nomeUnita(u) }}</strong>
        <span v-if="u.senza_nome" class="badge badge-outline theme-warning ms-1"> senza nome </span>
        <span class="badge ms-3" style="background: var(--ag-primary); color: var(--ag-on-primary)">
          {{ u.branca }}
        </span>
        <span v-if="!u.attiva" class="badge theme-secondary ms-1">Chiusa</span>
      </RouterLink>
    </div>
    <div class="d-flex flex-wrap gap-5 small">
      <div class="form-field">
        <input id="anche-chiuse" v-model="ancheChiuse" type="checkbox" class="check" />
        <label for="anche-chiuse">Mostra anche le unità chiuse</label>
      </div>
      <RouterLink :to="{ name: 'gruppo' }">Capigruppo e tesorieri di gruppo</RouterLink>
    </div>
  </section>
</template>
