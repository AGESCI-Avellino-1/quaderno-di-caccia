<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, type MiaSquadriglia } from '@/api/qdc'
import Avatar from '@/components/Avatar.vue'
import BarraRubrica from '@/components/BarraRubrica.vue'
import CopiaLocale from '@/components/CopiaLocale.vue'
import DelegaSquadriglia from '@/components/DelegaSquadriglia.vue'
import LinkPersonale from '@/components/LinkPersonale.vue'
import Telefono from '@/components/Telefono.vue'
import { useErrore } from '@/composables/useErrore'
import { useRubrica } from '@/composables/useRubrica'
import { leggiConCache } from '@/offline/cache'

// Phones of the patrol (DEC-13): the members see each other's phone, the capo
// squadriglia also the parents'. Kept as an encrypted copy for outings without network.
const { errore, inCorso, esegui } = useErrore()
const squadriglie = ref<MiaSquadriglia[]>([])
const copiaDel = ref<string | null>(null)
const rubrica = useRubrica()
// The member whose personal link the CSQ is generating (DEC-309).
const linkPer = ref<number | null>(null)

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
      <BarraRubrica
        v-if="s.sono_capo"
        :rubrica="rubrica"
        :tutti="[...s.membri.map((m) => m.id), ...s.genitori.map((g) => g.id)]"
      />
      <ul class="list-group">
        <li v-for="m in s.membri" :key="m.id" class="list-group-item">
          <div class="d-flex flex-wrap align-items-center gap-3">
            <!-- Choosing whom to put in the phone's contacts (DEC-302). -->
            <input
              v-if="s.sono_capo && rubrica.attiva.value"
              type="checkbox"
              class="check"
              :aria-label="`${m.nome} ${m.cognome} in rubrica`"
              :checked="rubrica.scelti.value.has(m.id)"
              @change="rubrica.alterna(m.id)"
            />
            <Avatar
              :nome="`${m.nome} ${m.cognome}`"
              :scheda="m.scheda ? m.id : null"
              dimensione="sm"
              tenue
              aria-hidden="true"
            />
            <RouterLink
              v-if="s.sono_capo"
              :to="{ name: 'persona', params: { id: m.id } }"
              title="Scheda e note"
              ><strong>{{ m.nome }} {{ m.cognome }}</strong></RouterLink
            >
            <strong v-else>{{ m.nome }} {{ m.cognome }}</strong>
            <span v-if="m.incarico" class="badge theme-primary">{{ m.incarico }}</span>
            <Telefono
              v-if="m.telefono"
              :numero="m.telefono"
              :di="`${m.nome} ${m.cognome}`"
              class="ms-auto"
            />
            <span v-else class="fg-2 small ms-auto">nessun numero</span>
          </div>
          <div v-if="m.del_genitore && m.telefono" class="fg-2 small">
            numero di {{ m.del_genitore }} (genitore)
          </div>
          <button
            v-if="m.link_attivazione && linkPer !== m.id"
            type="button"
            class="btn btn-link btn-sm p-0"
            @click="linkPer = m.id"
          >
            Link per creare il suo account
          </button>
          <LinkPersonale
            v-if="m.link_attivazione && linkPer === m.id"
            :persona="m.id"
            :nome="m.nome"
            sempre
            class="mt-3"
          />
          <ul v-if="s.sono_capo && genitoriDi(s, m.id).length" class="list-unstyled small mb-0">
            <li v-for="g in genitoriDi(s, m.id)" :key="g.telefono + g.nome">
              <input
                v-if="rubrica.attiva.value"
                type="checkbox"
                class="check me-1"
                :aria-label="`${g.nome} ${g.cognome} in rubrica`"
                :checked="rubrica.scelti.value.has(g.id)"
                @change="rubrica.alterna(g.id)"
              />
              Genitore: {{ g.nome }} {{ g.cognome }} ·
              <Telefono :numero="g.telefono" :di="`${g.nome} ${g.cognome}`" />
            </li>
          </ul>
        </li>
      </ul>
      <p v-if="s.sono_capo" class="form-text mb-0 mt-3">
        Come capo squadriglia vedi anche i numeri dei genitori e quelli che gli altri non vedono.
        Usali solo per la squadriglia.
      </p>
      <DelegaSquadriglia :squadriglia="s.id" :membri="s.membri" />
    </section>
  </section>
</template>
