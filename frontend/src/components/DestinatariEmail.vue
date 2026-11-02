<script setup lang="ts">
import { computed } from 'vue'

import { api, type Impostazioni } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Who receives the emails (DEC-276): off at first, switched on one group at a time once
// the app has been presented to them. What a group switched off would have got is
// dropped, only counted.
const props = defineProps<{ impostazioni: Impostazioni }>()
const emit = defineEmits<{ aggiornate: [Impostazioni] }>()
const { errore, inCorso, esegui } = useErrore()

const GRUPPI = [
  { chiave: 'capi', nome: 'Capi' },
  { chiave: 'genitori', nome: 'Genitori' },
  { chiave: 'ragazzi', nome: 'Ragazzi' },
] as const
type Gruppo = (typeof GRUPPI)[number]['chiave']

const acceso = (g: Gruppo) => !!props.impostazioni[`email_${g}`]
const scartate = computed(() => props.impostazioni.email_scartate ?? {})

async function imposta(gruppo: Gruppo, valore: boolean) {
  const gruppi = {
    capi: acceso('capi'),
    genitori: acceso('genitori'),
    ragazzi: acceso('ragazzi'),
    [gruppo]: valore,
  }
  const nuove = await esegui(() => api.destinatariEmail(gruppi))
  if (nuove) emit('aggiornate', nuove)
}
</script>

<template>
  <section class="mb-7">
    <h2 class="h5">Chi riceve le email</h2>
    <p class="small fg-2">
      Per partire un po' alla volta: accendi un gruppo quando gli hai presentato l'app. Finché un
      gruppo è spento, le email per lui non partono e non vengono tenute da parte. Chi è in più
      gruppi (per esempio un capo che è anche genitore) le riceve se almeno uno è acceso. Partono
      sempre, a chiunque, i codici per entrare, il cambio della password, gli inviti e le email
      dell'iscrizione e della lista d'attesa.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div class="card card-body">
      <div v-for="g in GRUPPI" :key="g.chiave" class="form-field">
        <div class="switch">
          <input
            :id="`imp-email-${g.chiave}`"
            type="checkbox"
            role="switch"
            :checked="acceso(g.chiave)"
            :disabled="inCorso"
            @change="imposta(g.chiave, ($event.target as HTMLInputElement).checked)"
          />
        </div>
        <label :for="`imp-email-${g.chiave}`">
          {{ g.nome }}
          <span v-if="scartate[g.chiave]" class="small fg-2">
            · {{ scartate[g.chiave] }} email non inviate finora
          </span>
        </label>
      </div>
    </div>
  </section>
</template>
