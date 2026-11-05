<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, criteriPubbliciPdf, type CriteriPubblici } from '@/api/qdc'

// The admission criteria, for anyone: on the waiting list without an account, in Download
// (DEC-357). While the year's are missing, the last ones as an outline. With none, nothing:
// a person joining the list must not meet an error or an empty box.
const criteri = ref<CriteriPubblici | null>(null)
onMounted(async () => {
  try {
    criteri.value = await api.criteriPubblici()
  } catch {
    criteri.value = null
  }
})
const giorno = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
</script>

<template>
  <div v-if="criteri?.versioni.length">
    <p class="small mb-1">
      <strong>Criteri di ammissione {{ criteri.anno_nome }}</strong>
    </p>
    <div v-if="criteri.traccia" class="alert theme-warning small py-3" role="note">
      <div>
        Sono i criteri dell'anno {{ criteri.anno_nome }}: solo una traccia. Quelli dell'anno
        {{ criteri.anno_corrente_nome }} verranno caricati a breve.
      </div>
    </div>
    <ul class="list-unstyled small mb-0">
      <li v-for="v in criteri.versioni" :key="v.id">
        <a :href="criteriPubbliciPdf(v.id)">Scarica il PDF</a>
        · dal {{ giorno(v.valida_dal) }} al {{ giorno(v.valida_fino_al) }}
        <span v-if="v.in_vigore" class="badge theme-success">In vigore</span>
      </li>
    </ul>
  </div>
</template>
