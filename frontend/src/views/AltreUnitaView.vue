<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import { useSessioneStore } from '@/stores/sessione'

// The units a capo does not serve, in the profile: their pages are the usual ones, and the
// server says on each that this capo may only read them (DEC-381).
const sessione = useSessioneStore()
const unita = computed(() => sessione.profilo?.altre_unita ?? [])
</script>

<template>
  <section>
    <h1 class="h4 mb-1">Altre unità</h1>
    <p class="small fg-2 mb-5">
      La progressione delle unità del gruppo in cui non servi. Puoi guardarla: le modifiche spettano
      al loro staff.
    </p>
    <p v-if="!unita.length" class="fg-2">Nessun'altra unità.</p>
    <ul v-else class="list-group">
      <li v-for="u in unita" :key="u.id" class="list-group-item">
        <RouterLink :to="{ name: 'sentiero-unita', params: { id: u.id } }">{{ u.nome }}</RouterLink>
        <div class="d-flex flex-wrap gap-3 small">
          <RouterLink v-if="u.tipo === 'REPARTO'" :to="{ name: 'imprese', params: { id: u.id } }"
            >Imprese</RouterLink
          >
          <RouterLink
            v-if="u.tipo === 'CLAN_FUOCO'"
            :to="{ name: 'carta-clan', params: { id: u.id } }"
            >Carta di clan</RouterLink
          >
          <RouterLink :to="{ name: 'passaggi', params: { id: u.id } }">Passaggi</RouterLink>
        </div>
      </li>
    </ul>
  </section>
</template>
