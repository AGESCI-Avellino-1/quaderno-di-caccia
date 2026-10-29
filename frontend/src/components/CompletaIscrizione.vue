<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import { api, type Completamento, type RichiestaIscrizione } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The data still missing after the approval, written straight on the member (BuonaStrada
// has no record of them yet). What BuonaStrada requires (DEC-124): own mobile and
// email for adults and minors in Clan/Fuoco or Noviziato; for a minor the parents, one with exclusive custody or both,
// with codice fiscale, mobile and email. Online only.
const props = defineProps<{ id: number }>()
const emit = defineEmits<{ cambiata: [richiesta: RichiestaIscrizione] }>()
const { errore, inCorso, esegui } = useErrore()
const dati = reactive<Completamento>({
  sesso: '',
  luogo_nascita: '',
  indirizzo: '',
  civico: '',
  comune: '',
  provincia: '',
  cap: '',
  cellulare: '',
  email: '',
  contatti_obbligatori: false,
  cellulare_genitore: null,
  genitore_unico: null,
  altro_genitore: null,
})
const vuoto = { nome: '', cognome: '', codice_fiscale: '', cellulare: '', email: '' }

function scegliGenitori(unico: boolean) {
  dati.genitore_unico = unico
  if (!unico && !dati.altro_genitore) dati.altro_genitore = { ...vuoto }
}
const caricato = ref(false)
const salvato = ref(false)

watch(
  () => props.id,
  async (id) => {
    const letto = await esegui(() => api.completamento(id))
    if (!letto) return
    for (const campo of Object.keys(dati) as (keyof Completamento)[]) {
      ;(dati as Record<string, unknown>)[campo] = letto[campo]
    }
    caricato.value = true
  },
  { immediate: true },
)

async function salva() {
  salvato.value = false
  const esito = await esegui(() => api.completa(props.id, { ...dati }))
  if (!esito) return
  salvato.value = true
  emit('cambiata', esito.richiesta)
}
</script>

<template>
  <form v-if="caricato" class="row g-3 mt-1" @submit.prevent="salva">
    <div v-if="errore" class="col-12 alert theme-danger py-3 small" role="alert">{{ errore }}</div>
    <div class="col-6 sm:col-3">
      <label class="form-label small" :for="`sesso-${id}`">Sesso</label>
      <select :id="`sesso-${id}`" v-model="dati.sesso" class="form-control form-control-sm">
        <option value="">—</option>
        <option value="F">F</option>
        <option value="M">M</option>
      </select>
    </div>
    <div class="col-6 sm:col-9">
      <label class="form-label small" :for="`luogo-${id}`">Luogo di nascita</label>
      <input
        :id="`luogo-${id}`"
        v-model="dati.luogo_nascita"
        class="form-control form-control-sm"
      />
    </div>
    <div class="col-9">
      <label class="form-label small" :for="`indirizzo-${id}`">Indirizzo</label>
      <input
        :id="`indirizzo-${id}`"
        v-model="dati.indirizzo"
        class="form-control form-control-sm"
      />
    </div>
    <div class="col-3">
      <label class="form-label small" :for="`civico-${id}`">Civico</label>
      <input :id="`civico-${id}`" v-model="dati.civico" class="form-control form-control-sm" />
    </div>
    <div class="col-12 sm:col-6">
      <label class="form-label small" :for="`comune-${id}`">Comune</label>
      <input :id="`comune-${id}`" v-model="dati.comune" class="form-control form-control-sm" />
    </div>
    <div class="col-6 sm:col-3">
      <label class="form-label small" :for="`provincia-${id}`">Provincia</label>
      <input
        :id="`provincia-${id}`"
        v-model="dati.provincia"
        class="form-control form-control-sm"
        maxlength="2"
        placeholder="AV"
      />
    </div>
    <div class="col-6 sm:col-3">
      <label class="form-label small" :for="`cap-${id}`">CAP</label>
      <input
        :id="`cap-${id}`"
        v-model="dati.cap"
        class="form-control form-control-sm"
        maxlength="5"
        inputmode="numeric"
      />
    </div>
    <template v-if="dati.cellulare_genitore === null">
      <div class="col-12 sm:col-6">
        <label class="form-label small" :for="`socio-cellulare-${id}`">Il tuo cellulare</label>
        <input
          :id="`socio-cellulare-${id}`"
          v-model="dati.cellulare"
          type="tel"
          class="form-control form-control-sm"
        />
      </div>
      <div class="col-12 sm:col-6">
        <label class="form-label small" :for="`socio-email-${id}`">La tua email</label>
        <input
          :id="`socio-email-${id}`"
          v-model="dati.email"
          type="email"
          class="form-control form-control-sm"
        />
      </div>
    </template>
    <template v-else>
      <div class="col-12 sm:col-6">
        <label class="form-label small" :for="`socio-cellulare-${id}`">
          Cellulare del ragazzo{{ dati.contatti_obbligatori ? '' : ' (se ne ha uno)' }}
        </label>
        <input
          :id="`socio-cellulare-${id}`"
          v-model="dati.cellulare"
          type="tel"
          class="form-control form-control-sm"
        />
      </div>
      <div class="col-12 sm:col-6">
        <label class="form-label small" :for="`socio-email-${id}`">
          Email del ragazzo (sua, non del genitore){{
            dati.contatti_obbligatori ? '' : ', se ne ha una'
          }}
        </label>
        <input
          :id="`socio-email-${id}`"
          v-model="dati.email"
          type="email"
          class="form-control form-control-sm"
        />
      </div>
      <div class="col-12 sm:col-6">
        <label class="form-label small" :for="`cellulare-${id}`">Il tuo cellulare (genitore)</label>
        <input
          :id="`cellulare-${id}`"
          v-model="dati.cellulare_genitore"
          type="tel"
          class="form-control form-control-sm"
        />
      </div>
      <fieldset class="col-12">
        <legend class="form-label small">I genitori, come in BuonaStrada</legend>
        <div class="d-flex flex-wrap gap-5">
          <div class="form-field">
            <input
              :id="`unico-${id}`"
              type="radio"
              class="radio"
              :name="`genitori-${id}`"
              :checked="dati.genitore_unico === true"
              @change="scegliGenitori(true)"
            />
            <label class="small" :for="`unico-${id}`">
              Genitore singolo (affidamento esclusivo)
            </label>
          </div>
          <div class="form-field">
            <input
              :id="`entrambi-${id}`"
              type="radio"
              class="radio"
              :name="`genitori-${id}`"
              :checked="dati.genitore_unico === false"
              @change="scegliGenitori(false)"
            />
            <label class="small" :for="`entrambi-${id}`">Entrambi i genitori o tutori</label>
          </div>
        </div>
      </fieldset>
      <template v-if="dati.genitore_unico === false && dati.altro_genitore">
        <div class="col-12 sm:col-6">
          <label class="form-label small" :for="`altro-nome-${id}`">Nome dell'altro genitore</label>
          <input
            :id="`altro-nome-${id}`"
            v-model="dati.altro_genitore.nome"
            class="form-control form-control-sm"
          />
        </div>
        <div class="col-12 sm:col-6">
          <label class="form-label small" :for="`altro-cognome-${id}`">Cognome</label>
          <input
            :id="`altro-cognome-${id}`"
            v-model="dati.altro_genitore.cognome"
            class="form-control form-control-sm"
          />
        </div>
        <div class="col-12 sm:col-4">
          <label class="form-label small" :for="`altro-cf-${id}`">Codice fiscale</label>
          <input
            :id="`altro-cf-${id}`"
            v-model="dati.altro_genitore.codice_fiscale"
            class="form-control form-control-sm"
            maxlength="16"
            autocapitalize="characters"
          />
        </div>
        <div class="col-12 sm:col-4">
          <label class="form-label small" :for="`altro-cellulare-${id}`">Cellulare</label>
          <input
            :id="`altro-cellulare-${id}`"
            v-model="dati.altro_genitore.cellulare"
            type="tel"
            class="form-control form-control-sm"
          />
        </div>
        <div class="col-12 sm:col-4">
          <label class="form-label small" :for="`altro-email-${id}`">Email</label>
          <input
            :id="`altro-email-${id}`"
            v-model="dati.altro_genitore.email"
            type="email"
            class="form-control form-control-sm"
          />
        </div>
      </template>
    </template>
    <div class="col-12 d-flex align-items-center gap-3">
      <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
        Salva
      </button>
      <span v-if="salvato" class="small fg-success" role="status">Salvato</span>
    </div>
  </form>
</template>
