<script setup lang="ts">
import { ref } from 'vue'

import { api } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// A capo whose joining is complete outside the app, waiting only for BuonaStrada's code:
// a capogruppo lets them in as if registered, and may take it back (DEC-400). The real
// code makes it pointless.
const props = defineProps<{ persona: number; nome: string; abilitato: boolean }>()
const emit = defineEmits<{ cambiato: [] }>()
const { errore, inCorso, esegui } = useErrore()
const conferma = ref(false)

async function cambia() {
  await esegui(() =>
    props.abilitato ? api.togliAbilitazione(props.persona) : api.abilitaComeCensito(props.persona),
  )
  if (errore.value) return
  conferma.value = false
  emit('cambiato')
}
</script>

<template>
  <section class="card card-body mb-5">
    <h2 class="h5">Codice socio provvisorio</h2>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <p v-if="abilitato" class="small fg-2">
      {{ nome }} è abilitato come censito: vede quello che vede un capo già in BuonaStrada. Quando
      arriva il codice socio vero l'abilitazione non serve più.
    </p>
    <p v-else class="small fg-2">
      Finché il codice socio è provvisorio, {{ nome }} non vede i dati delicati degli altri soci. Se
      l'iscrizione è già completa e manca solo il codice da BuonaStrada, abilitalo come censito.
    </p>
    <div class="d-flex flex-wrap gap-3 align-items-center">
      <button
        v-if="!conferma"
        type="button"
        class="btn btn-sm btn-outline"
        :class="abilitato ? 'theme-danger' : 'theme-primary'"
        @click="conferma = true"
      >
        {{ abilitato ? "Togli l'abilitazione…" : 'Abilita come censito…' }}
      </button>
      <template v-else>
        <span class="small">
          {{ abilitato ? "Togliere l'abilitazione?" : `Abilitare ${nome} come censito?` }}
        </span>
        <button
          type="button"
          class="btn btn-sm btn-solid"
          :class="abilitato ? 'theme-danger' : 'theme-primary'"
          :disabled="inCorso"
          @click="cambia"
        >
          {{ abilitato ? "Togli l'abilitazione" : 'Abilita come censito' }}
        </button>
        <button type="button" class="btn btn-sm btn-link" @click="conferma = false">No</button>
      </template>
    </div>
  </section>
</template>
