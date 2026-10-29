<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { MINUTI_BLOCCO } from '@/composables/useBloccoAutomatico'
import { useErrore } from '@/composables/useErrore'
import { salvaInCache } from '@/offline/cache'
import { BiometriaNonDisponibile, biometriaForseDisponibile } from '@/sicurezza/biometria'
import {
  LUNGHEZZA_MINIMA_PIN,
  TENTATIVI_MASSIMI,
  attivaBiometria,
  configura,
  sceltaSoloOnline,
  stato,
} from '@/sicurezza/cassaforte'
import { nomeProposto, registraDispositivo } from '@/sicurezza/dispositivo'
import { useSessioneStore } from '@/stores/sessione'

// First login on a device (or "Cambia PIN"): protect the data kept on it (DEC-97).
const route = useRoute()
const router = useRouter()
const sessione = useSessioneStore()
const { errore, inCorso, esegui } = useErrore()

const nome = ref(nomeProposto())
const pin = ref('')
const conferma = ref('')
const conBiometria = ref(false)
const biometriaPossibile = ref(false)
const avviso = ref<string | null>(null)
const giaConfigurata = stato.value === 'sbloccata' || stato.value === 'solo_online'

onMounted(async () => {
  biometriaPossibile.value = await biometriaForseDisponibile()
  conBiometria.value = biometriaPossibile.value
})

const prossima = () => (typeof route.query.prossima === 'string' ? route.query.prossima : '/')

async function attiva() {
  avviso.value = null
  if (!/^\d+$/.test(pin.value) || pin.value.length < LUNGHEZZA_MINIMA_PIN) {
    errore.value = `Il PIN deve avere almeno ${LUNGHEZZA_MINIMA_PIN} cifre.`
    return
  }
  if (pin.value !== conferma.value) {
    errore.value = 'I due PIN non coincidono.'
    return
  }
  const email = sessione.profilo!.email
  // Registering first: it needs the network, and without it nothing is saved here.
  const fatto = await esegui(async () => {
    await registraDispositivo(nome.value)
    await configura(email, pin.value)
    // The profile was loaded before the vault existed: save it now, or the app could not
    // open offline (it would not know who is using it).
    await salvaInCache('profilo', sessione.profilo)
    return true
  })
  if (!fatto) return
  if (conBiometria.value) {
    try {
      await attivaBiometria(email)
    } catch (e) {
      avviso.value =
        e instanceof BiometriaNonDisponibile
          ? e.message
          : 'Impronta o volto non attivati: potrai riprovare da «Dispositivi».'
    }
  }
  if (!avviso.value) await router.replace(prossima())
}

async function soloOnline() {
  await sceltaSoloOnline(sessione.profilo!.email)
  await router.replace(prossima())
}
</script>

<template>
  <section class="mx-auto" style="max-width: 30rem">
    <h1 class="h4 mb-5">Proteggi i dati su questo telefono</h1>
    <p>
      Per funzionare anche senza rete, l'app salva su questo telefono una copia dei dati che puoi
      vedere: contatti, e per i capi farmaci e allergie dei ragazzi. Sono dati di minori: la copia
      viene cifrata e si apre solo con un PIN, o con impronta o volto.
    </p>
    <ul class="small">
      <li>Dopo {{ MINUTI_BLOCCO }} minuti senza usarla l'app si blocca.</li>
      <li>Dopo {{ TENTATIVI_MASSIMI }} PIN sbagliati la copia sul telefono viene cancellata.</li>
      <li>Se perdi il telefono, tu o un capogruppo potete scollegarlo a distanza.</li>
      <li>Se il telefono non si collega per molti giorni, la copia si cancella da sola.</li>
    </ul>
    <div v-if="giaConfigurata" class="alert theme-warning small">
      Impostando un nuovo PIN la copia attuale sul telefono viene cancellata e riscaricata.
    </div>
    <div v-if="errore" class="alert theme-danger" role="alert">{{ errore }}</div>
    <div v-if="avviso" class="alert theme-warning" role="status">
      <div>
        {{ avviso }}
        <RouterLink :to="prossima()" class="d-block mt-1">Continua con il solo PIN</RouterLink>
      </div>
    </div>

    <form v-if="!avviso" class="vstack gap-3" @submit.prevent="attiva">
      <label class="form-label mb-0" for="nome-dispositivo">Nome di questo dispositivo</label>
      <input id="nome-dispositivo" v-model="nome" class="form-control" maxlength="80" required />
      <label class="form-label mb-0 mt-3" for="pin"
        >PIN (almeno {{ LUNGHEZZA_MINIMA_PIN }} cifre)</label
      >
      <input
        id="pin"
        v-model="pin"
        class="form-control"
        type="password"
        inputmode="numeric"
        autocomplete="new-password"
        :minlength="LUNGHEZZA_MINIMA_PIN"
        required
      />
      <label class="form-label mb-0" for="conferma-pin">Ripeti il PIN</label>
      <input
        id="conferma-pin"
        v-model="conferma"
        class="form-control"
        type="password"
        inputmode="numeric"
        autocomplete="new-password"
        required
      />
      <div v-if="biometriaPossibile" class="form-field mt-3">
        <input id="biometria" v-model="conBiometria" class="check" type="checkbox" />
        <label for="biometria">Sblocca anche con impronta o volto</label>
      </div>
      <button class="btn btn-solid theme-primary mt-3" :disabled="inCorso">
        Attiva la protezione
      </button>
    </form>

    <hr />
    <p class="small mb-3">
      Preferisci non salvare niente su questo telefono (ad esempio se non è tuo)? L'app funzionerà
      solo con la rete.
      <template v-if="sessione.capo"> Al campo, senza rete, non avrai i dati dei ragazzi.</template>
    </p>
    <button type="button" class="btn btn-outline theme-secondary btn-sm" @click="soloOnline">
      Usa solo online
    </button>
  </section>
</template>
