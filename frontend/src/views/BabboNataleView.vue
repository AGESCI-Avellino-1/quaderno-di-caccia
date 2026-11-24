<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { api, type BabboNatale } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Babbo Natale segreto (DEC-422): to whom one gives a gift (and one's children, for a
// parent), then the exchanges for who organises them. The organisers never see who gives a
// gift to whom. While the feature is off the API answers 404 (DEC-421). Online only.
const router = useRouter()
const { errore, inCorso, esegui } = useErrore()
const dati = ref<BabboNatale | null>(null)
const data = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString('it-IT')

const nuovo = ref({ nome: '', unita_id: null as number | null, consegna_il: '', luogo: '' })
const apertoNuovo = ref(false)

const attivi = computed(() => dati.value?.scambi.filter((s) => !s.chiuso) ?? [])
const chiusi = computed(() => dati.value?.scambi.filter((s) => s.chiuso) ?? [])

onMounted(async () => {
  dati.value = (await esegui(() => api.babboNatale())) ?? null
  if (dati.value && !dati.value.puo_tutto_il_gruppo && dati.value.unita.length) {
    nuovo.value.unita_id = dati.value.unita[0]!.id
  }
})

async function crea() {
  const scambio = await esegui(() => api.creaScambio(nuovo.value))
  if (scambio) await router.push({ name: 'scambio-regali', params: { id: scambio.id } })
}
</script>

<template>
  <section>
    <h1 class="h4">Babbo Natale segreto</h1>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>

    <template v-if="dati">
      <div v-if="dati.nascosti" class="alert theme-warning small" role="status">
        Stai usando l'app al posto di un'altra persona: a chi fa il regalo non si vede.
      </div>
      <section v-for="(r, i) in dati.regali" :key="i" class="card card-body mb-5" data-regalo>
        <h2 class="h5 mb-3">{{ r.scambio }}</h2>
        <p class="mb-3">
          <template v-if="r.proprio">Fai il regalo a</template>
          <template v-else>{{ r.chi }} fa il regalo a</template>
        </p>
        <p v-if="r.a_chi" class="h4 mb-3" data-a-chi>{{ r.a_chi }}</p>
        <p class="small mb-1">
          Consegna: {{ data(r.consegna_il) }}<template v-if="r.luogo">, {{ r.luogo }}</template>
          <span v-if="r.chiuso" class="badge theme-secondary ms-3">Concluso</span>
        </p>
        <p class="small fg-2 mb-0">
          Non dirlo a nessuno: chi riceve il regalo scoprirà chi è stato solo alla consegna.
        </p>
      </section>

      <template v-if="dati.puo_organizzare">
        <div class="d-flex align-items-center flex-wrap gap-3 mb-3">
          <h2 class="h5 mb-0">Scambi di regali</h2>
          <button
            v-if="!apertoNuovo"
            type="button"
            class="btn btn-solid theme-primary btn-sm ms-auto"
            @click="apertoNuovo = true"
          >
            Nuovo scambio
          </button>
        </div>
        <p class="small fg-2">
          Scegli i partecipanti, poi fai l'estrazione: ognuno saprà solo a chi fa il regalo. Né tu
          né altri potrete vedere gli abbinamenti.
        </p>

        <form v-if="apertoNuovo" class="card card-body mb-5" @submit.prevent="crea">
          <div class="form-field mb-3">
            <label class="form-label small" for="scambio-nome">Nome</label>
            <input
              id="scambio-nome"
              v-model="nuovo.nome"
              class="form-control"
              required
              maxlength="120"
              placeholder="Natale in reparto"
            />
          </div>
          <div class="form-field mb-3">
            <label class="form-label small" for="scambio-unita">Unità</label>
            <select id="scambio-unita" v-model="nuovo.unita_id" class="form-control">
              <option v-if="dati.puo_tutto_il_gruppo" :value="null">Tutto il gruppo</option>
              <option v-for="u in dati.unita" :key="u.id" :value="u.id">{{ u.nome }}</option>
            </select>
          </div>
          <div class="form-field mb-3">
            <label class="form-label small" for="scambio-consegna">Giorno della consegna</label>
            <input
              id="scambio-consegna"
              v-model="nuovo.consegna_il"
              type="date"
              class="form-control"
              required
            />
          </div>
          <div class="form-field mb-3">
            <label class="form-label small" for="scambio-luogo">Luogo (facoltativo)</label>
            <input id="scambio-luogo" v-model="nuovo.luogo" class="form-control" maxlength="200" />
          </div>
          <div class="d-flex gap-3">
            <button type="submit" class="btn btn-solid theme-primary" :disabled="inCorso">
              Crea
            </button>
            <button
              type="button"
              class="btn btn-outline theme-secondary"
              @click="apertoNuovo = false"
            >
              Annulla
            </button>
          </div>
        </form>

        <p v-if="!dati.scambi.length" class="fg-2 small">Nessuno scambio.</p>
        <ul v-for="(elenco, i) in [attivi, chiusi]" :key="i" class="list-unstyled mb-5">
          <li v-if="i === 1 && elenco.length" class="h6 mt-5">Conclusi</li>
          <li v-for="s in elenco" :key="s.id" class="border-top py-3" data-scambio>
            <RouterLink :to="{ name: 'scambio-regali', params: { id: s.id } }">
              <strong>{{ s.nome }}</strong>
            </RouterLink>
            <span class="badge ms-3" :class="s.estratto ? 'theme-success' : 'theme-secondary'">
              {{ s.estratto ? 'Estratto' : 'Da estrarre' }}
            </span>
            <div class="small fg-2">
              {{ s.unita }} · consegna {{ data(s.consegna_il) }} · {{ s.partecipanti }}
              partecipanti
            </div>
          </li>
        </ul>
      </template>
      <p v-else-if="!dati.regali.length" class="fg-2">Nessuno scambio di regali in corso.</p>
    </template>
  </section>
</template>
