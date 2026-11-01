<script setup lang="ts">
import { RouterLink } from 'vue-router'

import { useSessioneStore } from '@/stores/sessione'

// An address the app does not know (DEC-270): a mistyped link or a page that moved.
const sessione = useSessioneStore()
</script>

<template>
  <section class="text-center py-12 mx-auto" style="max-width: 36rem">
    <h1 class="h4">Pagina non trovata</h1>
    <p class="my-5">
      L'indirizzo non esiste o non è più valido: forse il link è incompleto, oppure la pagina è
      stata spostata.
    </p>
    <p class="fg-2 small">
      {{
        sessione.autenticato
          ? 'Dalla Home o dal menu trovi tutto quello che puoi vedere con il tuo profilo.'
          : 'Se stavi cercando di entrare, vai alla pagina di accesso.'
      }}
    </p>
    <RouterLink to="/" class="btn btn-solid theme-primary">Torna alla Home</RouterLink>
  </section>
</template>
