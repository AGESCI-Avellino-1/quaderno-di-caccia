<script setup lang="ts">
// Medicines, allergies and intolerances (DEC-48 core), dietary needs (DEC-49). Severe allergies come first and
// stand out: at camp this is read in a hurry.
import { computed } from 'vue'

import { ANAMNESI, TIPI_ALLERGIA, type Sanitarie } from '@/api/qdc'

const props = defineProps<{ dati: Sanitarie; compatta?: boolean }>()

const ordineGravita = { GRAVE: 0, MODERATA: 1, LIEVE: 2 } as const
const allergie = computed(() =>
  [...props.dati.allergie].sort((a, b) => ordineGravita[a.gravita] - ordineGravita[b.gravita]),
)
const nomeTipo = Object.fromEntries(TIPI_ALLERGIA.map((t) => [t.tipo, t.nome.toLowerCase()]))
// Copies of the device saved before the group's form may still say "ALLERGIA".
const tipo = (t: string) => nomeTipo[t] ?? 'allergia'
const siNo = (v: boolean | null | undefined) => (v === true ? 'sì' : v === false ? 'no' : '')
const etichettaGravita = { GRAVE: 'Grave', MODERATA: 'Moderata', LIEVE: 'Lieve' } as const
const classeGravita = {
  GRAVE: 'theme-danger',
  MODERATA: 'theme-warning',
  LIEVE: 'theme-secondary',
} as const
</script>

<template>
  <div>
    <p v-if="!dati.compilate" class="fg-2 small mb-0">Farmaci e allergie non ancora compilati.</p>
    <template v-else>
      <h3 v-if="!compatta" class="h6 mt-3">Allergie e intolleranze</h3>
      <p v-if="dati.nessuna_allergia" class="small mb-1">Nessuna allergia o intolleranza.</p>
      <ul v-else-if="allergie.length" class="list-unstyled mb-3">
        <li v-for="(a, i) in allergie" :key="i" class="mb-1">
          <span class="badge me-1" :class="classeGravita[a.gravita]">{{
            etichettaGravita[a.gravita]
          }}</span>
          <strong>{{ a.sostanza }}</strong>
          <span class="fg-2 small"> ({{ tipo(a.tipo) }})</span>
          <div v-if="a.reazione" class="small">Reazione: {{ a.reazione }}</div>
          <div v-if="a.cosa_fare" class="small fw-semibold">Cosa fare: {{ a.cosa_fare }}</div>
        </li>
      </ul>
      <p v-else class="small fg-2 mb-1">Allergie non indicate.</p>

      <h3 v-if="!compatta" class="h6 mt-3">Farmaci</h3>
      <p v-if="dati.nessun_farmaco" class="small mb-1">Nessun farmaco.</p>
      <ul v-else-if="dati.farmaci.length" class="list-unstyled mb-1">
        <li v-for="(f, i) in dati.farmaci" :key="i" class="mb-1">
          <strong>{{ f.nome }}</strong> — {{ f.posologia }}
          <span v-if="f.orari" class="small">({{ f.orari }})</span>
          <span class="badge badge-outline theme-secondary ms-1">{{
            f.autonomo ? 'lo prende da solo' : 'glielo dà un capo'
          }}</span>
          <div v-if="f.note" class="small">{{ f.note }}</div>
        </li>
      </ul>
      <p v-else class="small fg-2 mb-1">Farmaci non indicati.</p>

      <!-- At camp too (DEC-291). -->
      <p v-if="dati.farmaco_salvavita" class="small mb-1">
        <span class="badge theme-danger me-1">Salvavita</span>
        Ha un farmaco salvavita per un'allergia grave.
      </p>
      <p v-if="dati.farmaci_da_banco != null" class="small mb-1">
        Farmaci da banco per piccoli malesseri:
        <strong>{{ dati.farmaci_da_banco ? 'autorizzati' : 'non autorizzati' }}</strong>
      </p>

      <template v-if="dati.esigenze_alimentari">
        <h3 v-if="!compatta" class="h6 mt-3">Esigenze alimentari</h3>
        <p class="small mb-1">
          <span v-if="compatta" class="fw-semibold">A tavola: </span>{{ dati.esigenze_alimentari }}
        </p>
      </template>

      <template v-if="!compatta">
        <template v-if="ANAMNESI.some((d) => dati[d.campo] != null)">
          <h3 class="h6 mt-3">Stato di salute</h3>
          <ul class="list-unstyled small mb-1">
            <template v-for="d in ANAMNESI" :key="d.campo">
              <li v-if="dati[d.campo] != null">
                {{ d.domanda }} <strong>{{ siNo(dati[d.campo]) }}</strong>
                <template v-if="dati[d.campo]">: {{ dati[`${d.campo}_dettaglio`] }}</template>
              </li>
            </template>
          </ul>
        </template>
        <h3 class="h6 mt-3">Contatti e altre informazioni</h3>
        <ul class="list-unstyled small mb-1">
          <li v-for="g in dati.genitori ?? []" :key="g.id">
            {{ g.nome }}: {{ [g.cellulare, g.telefono_fisso].filter(Boolean).join(' · ') || '—' }}
          </li>
          <li v-if="dati.reperibilita_nome || dati.reperibilita_telefono">
            Contatto di fiducia: <strong>{{ dati.reperibilita_nome }}</strong>
            {{ dati.reperibilita_telefono }}
          </li>
          <li v-if="dati.medico_curante || dati.medico_telefono">
            Medico: {{ dati.medico_curante }} {{ dati.medico_telefono }}
          </li>
          <li v-if="dati.tessera_sanitaria">Tessera sanitaria: {{ dati.tessera_sanitaria }}</li>
          <li v-if="dati.antitetanica_data">
            Ultimo richiamo antitetanico:
            {{ new Date(dati.antitetanica_data).toLocaleDateString('it-IT') }}
          </li>
          <li v-else-if="dati.antitetanica !== undefined">
            Antitetanica: {{ siNo(dati.antitetanica) || 'non indicata' }}
          </li>
          <li v-if="dati.note_sanitarie" class="testo-a-capo">Note: {{ dati.note_sanitarie }}</li>
          <li v-if="dati.gruppo_sanguigno">Gruppo sanguigno: {{ dati.gruppo_sanguigno }}</li>
          <li v-if="dati.altre_vaccinazioni">Altre vaccinazioni: {{ dati.altre_vaccinazioni }}</li>
        </ul>
      </template>

      <p v-if="!compatta && dati.aggiornate_il" class="small fg-2 mb-0">
        Aggiornate il {{ new Date(dati.aggiornate_il).toLocaleDateString('it-IT') }}
        <template v-if="dati.inserite_da"> · {{ dati.inserite_da }}</template>
      </p>
    </template>
  </div>
</template>
