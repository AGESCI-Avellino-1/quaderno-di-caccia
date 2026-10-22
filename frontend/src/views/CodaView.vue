<script setup lang="ts">
import { liveQuery } from 'dexie'
import { onScopeDispose, ref } from 'vue'

import { testoErrore } from '@/composables/useErrore'
import { useRete } from '@/composables/useRete'
import { ErroreApi } from '@/api/http'
import { db, type OperazioneInCoda } from '@/offline/db'
import { riprova, scarta } from '@/offline/outbox'

// Changes made offline, waiting to be sent or needing a decision (DEC-96).
const { online, invia } = useRete()
const operazioni = ref<OperazioneInCoda[]>([])
const sottoscrizione = liveQuery(() => db.coda.orderBy('id').toArray()).subscribe((v) => {
  operazioni.value = v
})
onScopeDispose(() => sottoscrizione.unsubscribe())

const motivo = (o: OperazioneInCoda) =>
  o.errore ? testoErrore(new ErroreApi(o.errore.stato, o.errore.dati)) : ''
</script>

<template>
  <section>
    <h1 class="h4 mb-3">Modifiche in sospeso</h1>
    <button class="btn btn-primary mb-3" :disabled="!online" @click="invia()">Invia ora</button>
    <p v-if="!operazioni.length" class="text-body-secondary">Tutto inviato.</p>
    <ul class="list-group">
      <li v-for="o in operazioni" :key="o.id" class="list-group-item">
        <div class="d-flex justify-content-between">
          <span>{{ o.descrizione }}</span>
          <small class="text-body-secondary">{{
            new Date(o.creata_il).toLocaleString('it-IT')
          }}</small>
        </div>
        <template v-if="o.stato === 'errore'">
          <p class="small text-danger mb-1">{{ motivo(o) }}</p>
          <button class="btn btn-sm btn-outline-primary me-2" @click="riprova(o.id!)">
            Riprova
          </button>
          <button class="btn btn-sm btn-outline-danger" @click="scarta(o.id!)">Scarta</button>
        </template>
      </li>
    </ul>
  </section>
</template>
