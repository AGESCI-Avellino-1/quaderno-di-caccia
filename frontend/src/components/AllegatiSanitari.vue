<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { ErroreApi } from '@/api/http'
import { api, fileAllegatoSanitario, type AllegatiSanitari } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// The documents of the medical form and the signed form (DEC-290): the family (or the
// adult, or a capo) uploads them; a capo of the unit or a capogruppo checks each one and
// saves it on the group's Drive or on their computer; then the server deletes it and only
// "verified on … by …" stays. Online only, never kept on the device.
const props = defineProps<{ persona: number }>()
const emit = defineEmits<{ cambiati: [] }>()
const { errore, inCorso, esegui } = useErrore()
const dati = ref<AllegatiSanitari | null>(null)

onMounted(async () => {
  try {
    dati.value = await api.allegatiSanitari(props.persona)
  } catch (e) {
    if (!(e instanceof ErroreApi && e.stato === 404)) throw e
  }
})

const nuovo = reactive({ tipo: '', file: null as File | null })
const campoFile = ref<HTMLInputElement | null>(null)

async function carica() {
  if (!nuovo.file || !nuovo.tipo) return
  const file = nuovo.file
  const esito = await esegui(() => api.caricaAllegatoSanitario(props.persona, nuovo.tipo, file))
  if (esito) {
    dati.value = esito
    nuovo.file = null
    if (campoFile.value) campoFile.value.value = ''
  }
}

async function togli(id: number) {
  dati.value = (await esegui(() => api.togliAllegatoSanitario(id))) ?? dati.value
}

// The signed form asks the day of the signature before it is confirmed.
const firmataIl = reactive<Record<number, string>>({})

async function salva(id: number, dove: 'drive' | 'computer') {
  const data = firmataIl[id] || null
  const esito = await esegui(() =>
    dove === 'drive' ? api.allegatoSulDrive(id, data) : api.allegatoScaricato(id, data),
  )
  if (esito) {
    dati.value = esito
    emit('cambiati')
  }
}
</script>

<template>
  <div
    v-if="dati && (dati.puo_caricare || dati.puo_verificare || dati.allegati.length)"
    class="mt-5"
  >
    <h3 class="h6">Documenti da allegare</h3>
    <p class="small fg-2">
      Tessera sanitaria o codice fiscale, documento d'identità e scheda firmata. Restano sul server
      solo finché un capo li controlla e li salva: poi vengono cancellati.
    </p>
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <ul v-if="dati.allegati.length" class="list-group mb-3">
      <li v-for="a in dati.allegati" :key="a.id" class="list-group-item small">
        <strong>{{ a.tipo_nome }}</strong>
        <template v-if="a.verificato_il">
          · verificato il {{ new Date(a.verificato_il).toLocaleDateString('it-IT') }}
          <template v-if="a.verificato_da"> da {{ a.verificato_da }}</template>
          ({{ a.salvato_su }})
        </template>
        <template v-else>
          · caricato il {{ new Date(a.caricato_il).toLocaleDateString('it-IT') }}, da verificare
          <div class="d-flex flex-wrap align-items-center gap-3 mt-1">
            <a :href="fileAllegatoSanitario(a.id)" download>Scarica</a>
            <template v-if="dati.puo_verificare">
              <label v-if="a.tipo === 'SCHEDA'" class="d-flex align-items-center gap-1">
                Firmata il
                <input
                  v-model="firmataIl[a.id]"
                  type="date"
                  class="form-control form-control-sm w-auto"
                />
              </label>
              <button
                v-if="dati.drive"
                type="button"
                class="btn btn-sm btn-solid theme-primary"
                :disabled="inCorso || (a.tipo === 'SCHEDA' && !firmataIl[a.id])"
                @click="salva(a.id, 'drive')"
              >
                Salva sul Drive del gruppo
              </button>
              <button
                type="button"
                class="btn btn-sm btn-outline theme-primary"
                :disabled="inCorso || (a.tipo === 'SCHEDA' && !firmataIl[a.id])"
                @click="salva(a.id, 'computer')"
              >
                L'ho salvato sul mio computer
              </button>
            </template>
            <button
              type="button"
              class="btn btn-sm btn-link fg-danger px-0"
              :disabled="inCorso"
              @click="togli(a.id)"
            >
              Togli
            </button>
          </div>
        </template>
      </li>
    </ul>
    <form
      v-if="dati.puo_caricare"
      class="d-flex flex-wrap align-items-end gap-3"
      @submit.prevent="carica"
    >
      <div>
        <label class="form-label small mb-0" for="allegato-tipo">Documento</label>
        <select
          id="allegato-tipo"
          v-model="nuovo.tipo"
          class="form-control form-control-sm"
          required
        >
          <option value="" disabled>Scegli…</option>
          <option v-for="t in dati.tipi" :key="t.valore" :value="t.valore">{{ t.nome }}</option>
        </select>
      </div>
      <div>
        <label class="form-label small mb-0" for="allegato-file"
          >PDF o foto, al massimo 10 MB</label
        >
        <input
          id="allegato-file"
          ref="campoFile"
          type="file"
          accept="application/pdf,image/jpeg,image/png"
          class="form-control form-control-sm"
          required
          @change="nuovo.file = ($event.target as HTMLInputElement).files?.[0] ?? null"
        />
      </div>
      <button class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">Carica</button>
    </form>
  </div>
</template>
