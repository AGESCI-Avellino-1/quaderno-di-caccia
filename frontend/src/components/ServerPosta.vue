<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import { api, type Impostazioni, type SmtpIn } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The SMTP server (DEC-277), for the technical administrator: the password is encrypted
// on the server and never comes back.
const props = defineProps<{ impostazioni: Impostazioni }>()
const emit = defineEmits<{ aggiornate: [Impostazioni] }>()
const { errore, inCorso, esegui } = useErrore()
const esito = ref('')

const SICUREZZE = [
  { valore: 'STARTTLS', nome: 'STARTTLS (di solito porta 587)' },
  { valore: 'SSL', nome: 'SSL/TLS (di solito porta 465)' },
  { valore: 'NESSUNA', nome: 'Nessuna (solo in una rete fidata)' },
]

const dati = reactive<SmtpIn>({
  host: '',
  porta: 587,
  sicurezza: 'STARTTLS',
  utente: '',
  password: '',
  mittente: '',
})
function leggi(imp: Impostazioni) {
  Object.assign(dati, {
    host: imp.smtp_host ?? '',
    porta: imp.smtp_porta ?? 587,
    sicurezza: imp.smtp_sicurezza ?? 'STARTTLS',
    utente: imp.smtp_utente ?? '',
    password: '',
    mittente: imp.mittente ?? '',
  })
}
leggi(props.impostazioni)
watch(() => props.impostazioni, leggi)

async function salva() {
  esito.value = ''
  const nuove = await esegui(() => api.salvaSmtp({ ...dati }))
  if (!nuove) return
  emit('aggiornate', nuove)
  esito.value = 'Server di posta salvato.'
}

async function prova() {
  esito.value = ''
  const risposta = await esegui(() => api.provaSmtp())
  if (risposta) esito.value = `Email di prova mandata a ${risposta.inviata_a}: controlla la posta.`
}
</script>

<template>
  <section class="mb-7">
    <h2 class="h5">Server di posta</h2>
    <p class="small fg-2">
      Il server da cui partono le email. Se lo lasci vuoto vale quello configurato sul server da chi
      ha installato l'app. Con Google Workspace o Gmail: server <code>smtp.gmail.com</code>, porta
      587, STARTTLS, e una <strong>password per le app</strong> (serve la verifica in due passaggi,
      e l'amministratore del workspace deve permetterla). Con Microsoft 365:
      <code>smtp.office365.com</code>, porta 587, STARTTLS, finché il tenant accetta utente e
      password.
    </p>
    <div v-if="!impostazioni.smtp_disponibile" class="alert theme-warning small" role="status">
      <div>
        Manca la chiave per conservare la password in modo sicuro: la imposta chi ha installato
        l'app.
      </div>
    </div>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">{{ esito }}</div>
    <form class="card card-body" @submit.prevent="salva">
      <div class="row g-3">
        <div class="md:col-6">
          <label class="form-label small" for="smtp-host">Server</label>
          <input
            id="smtp-host"
            v-model="dati.host"
            class="form-control form-control-sm"
            autocomplete="off"
            placeholder="smtp.gmail.com"
          />
        </div>
        <div class="col-6 md:col-2">
          <label class="form-label small" for="smtp-porta">Porta</label>
          <input
            id="smtp-porta"
            v-model.number="dati.porta"
            type="number"
            min="1"
            max="65535"
            class="form-control form-control-sm"
          />
        </div>
        <div class="col-6 md:col-4">
          <label class="form-label small" for="smtp-sicurezza">Sicurezza</label>
          <select id="smtp-sicurezza" v-model="dati.sicurezza" class="form-control form-control-sm">
            <option v-for="s in SICUREZZE" :key="s.valore" :value="s.valore">{{ s.nome }}</option>
          </select>
        </div>
        <div class="md:col-6">
          <label class="form-label small" for="smtp-utente">Utente</label>
          <input
            id="smtp-utente"
            v-model="dati.utente"
            class="form-control form-control-sm"
            autocomplete="off"
          />
        </div>
        <div class="md:col-6">
          <label class="form-label small" for="smtp-password">Password</label>
          <input
            id="smtp-password"
            v-model="dati.password"
            type="password"
            class="form-control form-control-sm"
            autocomplete="new-password"
            :placeholder="
              impostazioni.smtp_password_salvata ? 'Salvata: lascia vuoto per non cambiarla' : ''
            "
          />
        </div>
        <div class="col-12">
          <label class="form-label small" for="smtp-mittente">Mittente</label>
          <input
            id="smtp-mittente"
            v-model="dati.mittente"
            class="form-control form-control-sm"
            :placeholder="impostazioni.mittente_predefinito"
          />
          <div class="small fg-2">
            Come «Nome &lt;indirizzo@dominio.it&gt;». Con Gmail e Microsoft 365 l'indirizzo deve
            essere quello dell'utente, o un alias che l'utente può usare.
          </div>
        </div>
        <div class="col-12 d-flex flex-wrap gap-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva
          </button>
          <button
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            :disabled="inCorso"
            @click="prova"
          >
            Manda un'email di prova a me
          </button>
        </div>
      </div>
    </form>
  </section>
</template>
