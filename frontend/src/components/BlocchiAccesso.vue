<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, type BloccoAccesso } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Who cannot log in now after too many wrong attempts (DEC-269), by account and by
// address; a lock also ends by itself an hour after the last attempt.
const { errore, inCorso, esegui } = useErrore()
const blocchi = ref<BloccoAccesso[] | null>(null)
const esito = ref('')

async function carica() {
  blocchi.value = (await esegui(() => api.blocchiAccesso())) ?? blocchi.value
}
onMounted(carica)

async function sblocca(blocco: BloccoAccesso) {
  esito.value = ''
  const rimasti = await esegui(() => api.sbloccaAccesso(blocco))
  if (!rimasti) return
  blocchi.value = rimasti
  esito.value = `Sbloccato: ${blocco.valore}.`
}

const ora = (iso: string) =>
  new Date(iso).toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'short' })
</script>

<template>
  <section class="mb-7">
    <h2 class="h5">Accessi bloccati</h2>
    <p class="small fg-2">
      Dopo 5 tentativi sbagliati l'app non accetta più la password per un'ora: per quell'account
      dallo stesso browser, oppure per tutti da quell'indirizzo internet (per esempio la rete di
      casa o della sede). Sblocca quando la persona ti conferma di aver sbagliato lei: altrimenti
      può essere qualcuno che prova a entrare al posto suo.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>
    <div class="card card-body">
      <p v-if="blocchi && !blocchi.length" class="small mb-0">Nessun accesso bloccato adesso.</p>
      <ul v-else-if="blocchi" class="list-unstyled mb-0">
        <li
          v-for="b in blocchi"
          :key="`${b.tipo}-${b.valore}`"
          class="d-flex flex-wrap align-items-center justify-content-between gap-3 py-3 border-bottom"
        >
          <span>
            <span class="badge theme-secondary me-3">{{
              b.tipo === 'account' ? 'Account' : 'Indirizzo'
            }}</span>
            <strong>{{ b.valore }}</strong>
            <span class="small fg-2 d-block">
              {{ b.tentativi }} tentativi sbagliati · bloccato al massimo fino alle
              {{ ora(b.fino_al) }}
            </span>
          </span>
          <button
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            :disabled="inCorso"
            @click="sblocca(b)"
          >
            Sblocca
          </button>
        </li>
      </ul>
      <button
        type="button"
        class="btn btn-sm btn-outline mt-3 align-self-start"
        :disabled="inCorso"
        @click="carica"
      >
        Aggiorna l'elenco
      </button>
    </div>
  </section>
</template>
