<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, type MiaSquadriglia } from '@/api/qdc'
import CopiaLocale from '@/components/CopiaLocale.vue'
import { useErrore } from '@/composables/useErrore'
import { leggiConCache } from '@/offline/cache'

// Phones of the patrol (DEC-13): the members see each other's phone, the capo
// squadriglia also the parents'. Kept as an encrypted copy for outings without network.
const { errore, inCorso, esegui } = useErrore()
const squadriglie = ref<MiaSquadriglia[]>([])
const copiaDel = ref<string | null>(null)

onMounted(async () => {
  const letto = await esegui(() => leggiConCache('mia-squadriglia', () => api.miaSquadriglia()))
  squadriglie.value = letto?.dati ?? []
  copiaDel.value = letto?.copiaDel ?? null
})

const genitoriDi = (s: MiaSquadriglia, id: number) => s.genitori.filter((g) => g.figlio_id === id)
</script>

<template>
  <section>
    <h1 class="h4 mb-5">La mia squadriglia</h1>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <CopiaLocale :del="copiaDel" />
    <p v-if="inCorso && !squadriglie.length" class="fg-2">Caricamento…</p>
    <p v-else-if="!squadriglie.length && !errore" class="fg-2">Non sei in una squadriglia.</p>

    <section v-for="s in squadriglie" :key="s.id" class="card card-body mb-5">
      <h2 class="h5 mb-0">{{ s.nome }}</h2>
      <p class="fg-2 small mb-3">{{ s.reparto }}</p>
      <ul class="list-group">
        <li v-for="m in s.membri" :key="m.id" class="list-group-item">
          <div class="d-flex flex-wrap align-items-baseline gap-3">
            <strong>{{ m.nome }} {{ m.cognome }}</strong>
            <span v-if="m.incarico" class="badge theme-primary">{{ m.incarico }}</span>
            <a v-if="m.telefono" :href="`tel:${m.telefono}`" class="ms-auto">{{ m.telefono }}</a>
            <span v-else class="fg-2 small ms-auto">nessun numero</span>
          </div>
          <div v-if="m.del_genitore && m.telefono" class="fg-2 small">
            numero di {{ m.del_genitore }} (genitore)
          </div>
          <ul v-if="s.sono_capo && genitoriDi(s, m.id).length" class="list-unstyled small mb-0">
            <li v-for="g in genitoriDi(s, m.id)" :key="g.telefono + g.nome">
              Genitore: {{ g.nome }} {{ g.cognome }} ·
              <a :href="`tel:${g.telefono}`">{{ g.telefono }}</a>
            </li>
          </ul>
        </li>
      </ul>
      <p v-if="s.sono_capo" class="form-text mb-0 mt-3">
        Come capo squadriglia vedi anche i numeri dei genitori e quelli che gli altri non vedono.
        Usali solo per la squadriglia.
      </p>
    </section>
  </section>
</template>
