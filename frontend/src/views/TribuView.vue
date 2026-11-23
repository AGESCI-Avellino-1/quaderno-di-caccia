<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, cerimoniaTotemPdf, immagineTotem, type TotemTribu, type Tribu } from '@/api/qdc'
import Icona from '@/components/Icona.vue'
import { useErrore } from '@/composables/useErrore'
import { useSessioneStore } from '@/stores/sessione'

// «La mia tribù» (DEC-416): the description of the tribe, one's own totem first, then
// every totem name of the members in the group today. Whose a totem is: the capi always,
// a ragazzo only for the capi and the members of their own unit. The capi approve the
// images uploaded by ragazzi and read the ceremony, when the group wrote one. Who may write
// their own totem name and has none yet sees nothing here until they write it (DEC-418).
// Online only.
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()
const tribu = ref<Tribu | null>(null)
const cerimonia = ref<string | null>(null)
// The image being refused: its totem and the reason.
const rifiuto = ref<{ id: number; motivo: string } | null>(null)

const paragrafi = computed(() => tribu.value?.descrizione.split('\n\n') ?? [])

async function carica() {
  tribu.value = (await esegui(() => api.tribu())) ?? tribu.value
}
onMounted(carica)

async function mostraCerimonia() {
  if (cerimonia.value !== null) {
    cerimonia.value = null
    return
  }
  const esito = await esegui(() => api.cerimoniaTotem())
  if (esito) cerimonia.value = esito.html
}

async function decisa(azione: () => Promise<TotemTribu>) {
  if (!(await esegui(azione))) return
  rifiuto.value = null
  await Promise.all([carica(), sessione.carica()])
}

const approva = (t: TotemTribu) => decisa(() => api.approvaImmagineTotem(t.id))
function rifiuta() {
  const r = rifiuto.value
  if (r) decisa(() => api.rifiutaImmagineTotem(r.id, r.motivo))
}
</script>

<template>
  <section>
    <h1 class="h4 mb-3">La mia tribù</h1>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>

    <p v-if="tribu?.scrivi_il_tuo" class="card card-body" data-scrivi-il-tuo>
      <span>
        Scrivi prima il tuo nome di totem
        <RouterLink
          v-if="sessione.profilo?.persona"
          :to="{ name: 'persona', params: { id: sessione.profilo.persona.id } }"
          >nel tuo profilo</RouterLink
        ><template v-else>nel tuo profilo</template>: poi qui troverai la tribù.
      </span>
    </p>

    <template v-else-if="tribu">
      <div class="card card-body mb-5 descrizione">
        <p v-for="(p, i) in paragrafi" :key="i" :class="{ 'mb-0': i === paragrafi.length - 1 }">
          {{ p }}
        </p>
      </div>

      <div v-if="tribu.cerimonia" class="d-flex flex-wrap gap-3 mb-5">
        <button type="button" class="btn btn-sm btn-outline theme-primary" @click="mostraCerimonia">
          {{ cerimonia === null ? 'Leggi la cerimonia del totem' : 'Nascondi la cerimonia' }}
        </button>
        <a :href="cerimoniaTotemPdf" download class="btn btn-sm btn-outline theme-primary">
          <Icona nome="download" /> Scarica in PDF
        </a>
      </div>
      <div v-if="cerimonia !== null" class="card card-body mb-5">
        <!-- eslint-disable-next-line vue/no-v-html -- HTML cleaned by the server -->
        <div v-html="cerimonia"></div>
      </div>

      <section v-if="tribu.da_approvare.length" class="mb-7">
        <h2 class="h5">Immagini da approvare</h2>
        <div v-for="t in tribu.da_approvare" :key="t.id" class="card card-body mb-3">
          <div class="d-flex flex-wrap align-items-center gap-3">
            <img
              :src="immagineTotem(t.id, t.versione, true)"
              :alt="`Immagine proposta per ${t.nome}`"
              width="96"
              height="96"
              class="rounded"
            />
            <div>
              <strong>{{ t.nome }}</strong>
              <div v-if="t.persona" class="small fg-2">
                {{ t.persona.nome }} {{ t.persona.cognome }}
              </div>
            </div>
            <div class="d-flex flex-wrap gap-3 ms-auto">
              <button
                type="button"
                class="btn btn-sm btn-solid theme-primary"
                :disabled="inCorso"
                @click="approva(t)"
              >
                Approva
              </button>
              <button
                v-if="rifiuto?.id !== t.id"
                type="button"
                class="btn btn-sm btn-outline theme-danger"
                @click="rifiuto = { id: t.id, motivo: '' }"
              >
                Rifiuta…
              </button>
            </div>
          </div>
          <form v-if="rifiuto?.id === t.id" class="mt-3" @submit.prevent="rifiuta">
            <label class="form-label small" :for="`rifiuto-${t.id}`">
              Perché la rifiuti? Lo legge chi ha il totem.
            </label>
            <input
              :id="`rifiuto-${t.id}`"
              v-model="rifiuto.motivo"
              class="form-control mb-3"
              maxlength="200"
              required
            />
            <div class="d-flex gap-3">
              <button type="submit" class="btn btn-sm btn-solid theme-danger" :disabled="inCorso">
                Rifiuta l'immagine
              </button>
              <button type="button" class="btn btn-sm btn-link" @click="rifiuto = null">
                Annulla
              </button>
            </div>
          </form>
        </div>
      </section>

      <template v-for="(elenco, i) in [tribu.mio ? [tribu.mio] : [], tribu.totem]" :key="i">
        <h2 v-if="i === 1 && tribu.mio && tribu.totem.length" class="h5">La tribù</h2>
        <ul class="list-unstyled totem mb-5">
          <li v-for="t in elenco" :key="t.id" class="card card-body">
            <img
              v-if="t.immagine"
              :src="immagineTotem(t.id, t.versione)"
              :alt="`Immagine di ${t.nome}`"
              width="120"
              height="120"
              class="rounded mb-3"
            />
            <span v-else class="segnaposto rounded mb-3" aria-hidden="true">
              <Icona nome="fire" />
            </span>
            <strong>{{ t.nome }}</strong>
            <span v-if="t === tribu.mio" class="badge theme-primary mt-1">il tuo</span>
            <RouterLink
              v-if="t.persona && sessione.capo"
              class="small"
              :to="{ name: 'persona', params: { id: t.persona.id } }"
            >
              {{ t.persona.nome }} {{ t.persona.cognome }}
            </RouterLink>
            <span v-else-if="t.persona && t !== tribu.mio" class="small fg-2">
              {{ t.persona.nome }} {{ t.persona.cognome }}
            </span>
            <span v-if="t.in_attesa" class="small fg-2">Immagine nuova in attesa</span>
          </li>
        </ul>
      </template>
      <p v-if="!tribu.mio && !tribu.totem.length" class="fg-2">
        Nessuno ha ancora un nome di totem.
      </p>
    </template>
  </section>
</template>

<style scoped>
.descrizione {
  border-left: 4px solid var(--ag-primary);
  font-style: italic;
}
.totem {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr));
  gap: 1rem;
}
.totem li {
  align-items: center;
  text-align: center;
}
.segnaposto {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 120px;
  height: 120px;
  font-size: 3rem;
  color: var(--ag-primary);
  background: var(--ag-primary-subtle);
}
</style>
