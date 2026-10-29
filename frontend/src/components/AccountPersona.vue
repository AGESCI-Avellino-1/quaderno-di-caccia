<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import { api, type SchedaAccount, type StatoAccount } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Accounts of a person and of their parents, with the invitation form (DEC-21, DEC-24).
// Every account has its own email, a child's too (refines DEC-25). Online only, like device revocation: an invitation queued offline would leave
// days later, and the backend answers 404 to whoever may not invite (panel hidden).
const props = defineProps<{ id: number }>()
const { errore, inCorso, esegui } = useErrore()
const stato = ref<StatoAccount | null>(null)
const aperto = ref<number | null>(null)
const inviato = ref<string | null>(null)
const modulo = reactive({ email: '', consensoDa: null as number | null, metodo: '' })

async function carica(id: number) {
  try {
    stato.value = await api.statoAccount(id)
  } catch {
    stato.value = null
  }
}
watch(() => props.id, carica, { immediate: true })

// "Dall'account del genitore" only when the chosen parent has an account.
const metodiConsenso = () => {
  const genitore = stato.value?.genitori.find((g) => g.id === modulo.consensoDa)
  return (stato.value?.metodi_consenso ?? []).filter(
    (m) => m.valore !== 'ACCOUNT_GENITORE' || !!genitore?.ha_account,
  )
}

function apri(scheda: SchedaAccount) {
  aperto.value = scheda.id
  inviato.value = null
  modulo.email = scheda.email ?? ''
  modulo.consensoDa = stato.value?.genitori.length === 1 ? stato.value.genitori[0]!.id : null
  modulo.metodo = ''
}

async function invia(scheda: SchedaAccount) {
  const fatto = await esegui(() =>
    api.invita({
      persona_id: scheda.id,
      email: modulo.email.trim(),
      ...(scheda.richiede_consenso_genitore && modulo.consensoDa
        ? { consenso_genitore_da_id: modulo.consensoDa, consenso_genitore_metodo: modulo.metodo }
        : {}),
    }),
  )
  if (!fatto) return
  inviato.value = `Invito inviato a ${modulo.email.trim()}.`
  aperto.value = null
  await carica(props.id)
}

async function annulla(invito: number) {
  if (await esegui(() => api.annullaInvito(invito))) await carica(props.id)
}

const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
const schede = () => (stato.value ? [stato.value.persona, ...stato.value.genitori] : [])
</script>

<template>
  <section v-if="stato" class="card card-body mb-5">
    <h2 class="h5">Accesso all'app</h2>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div v-if="inviato" class="alert theme-success" role="status">{{ inviato }}</div>
    <div v-for="s in schede()" :key="s.id" class="border-top pt-3 mt-3">
      <div class="d-flex align-items-center flex-wrap gap-3">
        <strong>{{ s.nome }} {{ s.cognome }}</strong>
        <span v-if="s.id !== stato.persona.id" class="fg-2 small">genitore</span>
        <span v-if="s.ha_account" class="badge theme-success">Ha un account</span>
        <span v-else class="badge theme-secondary">Nessun account</span>
        <button
          v-if="!s.ha_account && s.puo_invitare && aperto !== s.id"
          type="button"
          class="btn btn-sm btn-outline theme-primary ms-auto"
          @click="apri(s)"
        >
          Invita
        </button>
      </div>

      <ul v-if="s.inviti.some((i) => i.valido)" class="list-unstyled small mb-0 mt-1">
        <li v-for="i in s.inviti.filter((i) => i.valido)" :key="i.id">
          Invito a {{ i.email }}, valido fino al {{ data(i.scadenza) }}
          <button
            v-if="s.puo_invitare"
            type="button"
            class="btn btn-link btn-sm p-0 ms-1 align-baseline"
            :disabled="inCorso"
            @click="annulla(i.id)"
          >
            annulla
          </button>
        </li>
      </ul>

      <form v-if="aperto === s.id" class="mt-3" @submit.prevent="invia(s)">
        <label :for="`email-${s.id}`" class="form-label small">Email a cui mandare l'invito</label>
        <input
          :id="`email-${s.id}`"
          v-model="modulo.email"
          type="email"
          class="form-control form-control-sm"
          required
          autocomplete="off"
        />
        <p class="form-text">
          Deve essere un'email di {{ s.nome }}: non quella di un genitore, che serve per l'account
          del genitore.
        </p>

        <fieldset v-if="s.richiede_consenso_genitore" class="mt-3">
          <legend class="small fw-semibold mb-1">
            Ha meno di 14 anni: serve il consenso di un genitore
          </legend>
          <select
            v-model="modulo.consensoDa"
            class="form-control form-control-sm mb-1"
            aria-label="Genitore che dà il consenso"
            required
            @change="modulo.metodo = ''"
          >
            <option :value="null" disabled>Chi ha dato il consenso</option>
            <option v-for="g in stato.genitori" :key="g.id" :value="g.id">
              {{ g.nome }} {{ g.cognome }}
            </option>
          </select>
          <select
            v-model="modulo.metodo"
            class="form-control form-control-sm"
            aria-label="Come è stato verificato"
            required
          >
            <option value="" disabled>Come è stato verificato</option>
            <option v-for="m in metodiConsenso()" :key="m.valore" :value="m.valore">
              {{ m.etichetta }}
            </option>
          </select>
        </fieldset>

        <div class="d-flex gap-3 mt-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Invia invito
          </button>
          <button type="button" class="btn btn-sm btn-link" @click="aperto = null">Annulla</button>
        </div>
      </form>
    </div>
  </section>
</template>
