<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import {
  api,
  euro,
  fileFotoBC,
  fileLiberatoria,
  fileLiberatoriaFirmata,
  type IscrizioneBC,
  type PassiBC,
  type RiepilogoBC,
  type VersioneScheda,
} from '@/api/qdc'
import RisposteSchedaBC from '@/components/RisposteSchedaBC.vue'
import { useErrore } from '@/composables/useErrore'

// One minor's registration on BuonaCaccia (DEC-158…DEC-163). Who manages it (the staff
// of the member's unit, the capigruppo) keeps the deadlines, the management link, the
// release form, the presentation and the fee; the family downloads and sends back the
// release form and answers the event form. Online only: release forms and photos are
// personal data that do not wait on the phone.
const props = defineProps<{ iscrizione: IscrizioneBC; scheda: VersioneScheda | null }>()
const emit = defineEmits<{ cambiata: [iscrizione: IscrizioneBC] }>()
const { errore, inCorso, esegui } = useErrore()
const i = computed(() => props.iscrizione)
const oggi = () => new Date().toLocaleDateString('sv')
const data = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString('it-IT') : '')

const modifica = reactive({
  link: '',
  scadenzaLiberatoria: '',
  presentazione: '',
  importo: '',
  scadenzaQuota: '',
  motivoRigetto: '',
  chiusura: '' as '' | 'CANCELLATA' | 'NON_AMMESSO',
  chiusaIl: oggi(),
})
const rigetto = ref(false)
const riepilogo = ref<RiepilogoBC | null>(null)
const copiato = ref('')

watch(
  i,
  (nuova) => {
    modifica.link = nuova.link_gestione ?? ''
    modifica.scadenzaLiberatoria = nuova.scadenza_liberatoria_fissata
      ? nuova.scadenza_liberatoria
      : ''
    modifica.presentazione = nuova.presentazione ?? ''
    modifica.importo = nuova.quota && !nuova.quota.annullata ? nuova.quota.importo : ''
    modifica.scadenzaQuota = nuova.quota && !nuova.quota.annullata ? nuova.quota.scadenza : ''
  },
  { immediate: true },
)

async function fai(azione: () => Promise<IscrizioneBC>) {
  const dati = await esegui(azione)
  if (dati) emit('cambiata', dati)
  return dati
}

const aggiorna = (dati: Parameters<typeof api.aggiornaIscrizioneBC>[1]) =>
  fai(() => api.aggiornaIscrizioneBC(i.value.id, dati))
const passo = (dati: PassiBC) => fai(() => api.passiBC(i.value.id, dati))

async function carica(evento: Event, firmata: boolean) {
  const input = evento.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  await fai(() =>
    firmata
      ? api.caricaLiberatoriaFirmataBC(i.value.id, file)
      : api.caricaLiberatoriaBC(i.value.id, file),
  )
  input.value = ''
}

const valida = () => fai(() => api.esitoLiberatoriaBC(i.value.id, 'VALIDATA'))
const salvaPresentazione = () => fai(() => api.presentazioneBC(i.value.id, modifica.presentazione))
const togliQuota = () => fai(() => api.togliQuotaBC(i.value.id))
const salvaQuota = () =>
  fai(() => api.quotaIscrizioneBC(i.value.id, modifica.importo, modifica.scadenzaQuota))

async function rigetta() {
  if (await fai(() => api.esitoLiberatoriaBC(i.value.id, 'RIGETTATA', modifica.motivoRigetto))) {
    rigetto.value = false
    modifica.motivoRigetto = ''
  }
}

async function chiudi() {
  if (!modifica.chiusura) return
  if (
    await fai(() =>
      api.chiudiIscrizioneBC(i.value.id, modifica.chiusura as 'CANCELLATA', modifica.chiusaIl),
    )
  )
    modifica.chiusura = ''
}

async function mostraRiepilogo() {
  riepilogo.value = riepilogo.value
    ? null
    : ((await esegui(() => api.riepilogoBC(i.value.id))) ?? null)
}

async function copia(testo: string, cosa: string) {
  await navigator.clipboard.writeText(testo)
  copiato.value = cosa
}

// Until the staff loaded it on BuonaCaccia, or after a rejection.
const puoCaricareFirmata = computed(
  () =>
    i.value.puo_rispondere &&
    i.value.attiva &&
    i.value.modo_liberatoria === 'APP' &&
    i.value.liberatoria_da_firmare &&
    (!i.value.liberatoria_caricata_il || i.value.esito_liberatoria === 'RIGETTATA'),
)

const manca = computed(() => {
  const elenco: string[] = []
  if (!i.value.liberatoria_caricata_il || i.value.esito_liberatoria === 'RIGETTATA')
    elenco.push('liberatoria')
  if (props.scheda && !i.value.scheda_inviata_il) elenco.push('scheda')
  if (!i.value.pagata_il) elenco.push('pagamento')
  return elenco
})
const scaduta = computed(
  () => i.value.attiva && manca.value.length > 0 && i.value.scadenza < oggi(),
)
</script>

<template>
  <li class="list-group-item">
    <div class="d-flex flex-wrap align-items-baseline justify-content-between gap-3">
      <strong>{{ i.persona }}</strong>
      <span
        class="badge"
        :class="
          i.stato === 'AMMESSO'
            ? 'theme-success'
            : i.stato === 'IN_ATTESA'
              ? 'theme-warning'
              : 'theme-secondary'
        "
      >
        {{ i.stato_nome }}
      </span>
    </div>
    <div v-if="errore" class="alert theme-danger small mt-3" role="alert">{{ errore }}</div>

    <p class="small mb-3">
      Iscritto su BuonaCaccia il {{ data(i.iscritto_il) }}.
      <template v-if="i.attiva">
        Entro il <strong>{{ data(i.scadenza) }}</strong> su BuonaCaccia vanno caricati liberatoria e
        scheda e pagata la quota.
        <template v-if="i.puo_gestire">
          Si cancella senza perdere la quota fino al {{ data(i.limite_cancellazione) }}.
        </template>
      </template>
      <template v-else-if="i.cancellata_il"> Chiusa il {{ data(i.cancellata_il) }}. </template>
    </p>
    <div v-if="i.puo_gestire && scaduta" class="alert theme-danger small" role="status">
      <div>Scadenza superata: manca {{ manca.join(', ') }}.</div>
    </div>

    <!-- Management link (DEC-159) -->
    <div v-if="i.puo_gestire" class="mb-3 small">
      <a v-if="i.link_gestione" :href="i.link_gestione" target="_blank" rel="noopener noreferrer">
        Apri la gestione dell'iscrizione su BuonaCaccia
      </a>
      <span v-else class="fg-2">Link di gestione non ancora inserito.</span>
      <form
        class="d-flex flex-wrap align-items-end gap-3 mt-1"
        @submit.prevent="aggiorna({ link_gestione: modifica.link })"
      >
        <div class="flex-grow-1">
          <label class="form-label small" :for="`link-${i.id}`">
            Link di gestione (dalla prima email di BuonaCaccia; lo vede solo chi gestisce
            l'iscrizione: con quel link l'iscrizione si cancella senza poterla ripristinare)
          </label>
          <input
            :id="`link-${i.id}`"
            v-model="modifica.link"
            type="url"
            class="form-control form-control-sm"
          />
        </div>
        <button type="submit" class="btn btn-sm btn-outline theme-primary" :disabled="inCorso">
          Salva
        </button>
      </form>
    </div>

    <!-- Release form (DEC-160) -->
    <section class="mb-3 pt-3 border-top">
      <h4 class="h6 fw-bold mb-1">Liberatoria</h4>
      <p class="small mb-1">
        <template v-if="i.modo_liberatoria === 'APP'">
          Passa dall'app: la famiglia scarica il PDF, lo completa, lo firma e lo ricarica
        </template>
        <template v-else>Arriva allo staff per altri canali</template>
        entro il {{ data(i.scadenza_liberatoria) }}.
      </p>
      <ul class="small mb-1">
        <li v-if="i.modo_liberatoria === 'APP'">
          Da firmare:
          <a v-if="i.liberatoria_da_firmare" :href="fileLiberatoria(i.id)">scarica il PDF</a>
          <span v-else class="fg-2">lo staff non l'ha ancora caricata</span>
        </li>
        <li>
          Firmata:
          <template v-if="i.liberatoria_ricevuta_il">
            arrivata il {{ data(i.liberatoria_ricevuta_il) }}
            <a v-if="i.liberatoria_firmata" :href="fileLiberatoriaFirmata(i.id)">(apri)</a>
          </template>
          <span v-else class="fg-2">non ancora arrivata</span>
        </li>
        <li v-if="i.liberatoria_caricata_il">
          Caricata su BuonaCaccia il {{ data(i.liberatoria_caricata_il) }}
          <span v-if="i.esito_liberatoria === 'VALIDATA'" class="badge theme-success"
            >validata</span
          >
        </li>
        <li v-if="i.esito_liberatoria === 'RIGETTATA' || i.motivo_rigetto">
          <span class="badge theme-danger">rigettata</span> {{ i.motivo_rigetto }}: ne serve una
          nuova.
        </li>
      </ul>
      <div v-if="puoCaricareFirmata" class="small">
        <label class="form-label small" :for="`firmata-${i.id}`">
          Carica la liberatoria firmata (PDF o foto)
        </label>
        <input
          :id="`firmata-${i.id}`"
          type="file"
          accept="application/pdf,image/jpeg,image/png"
          class="form-control form-control-sm"
          :disabled="inCorso"
          @change="carica($event, true)"
        />
      </div>
      <div v-if="i.puo_gestire && i.attiva" class="d-flex flex-column gap-3 mt-3">
        <div class="d-flex flex-wrap align-items-end gap-3">
          <div>
            <label class="form-label small" :for="`modo-${i.id}`">Come arriva</label>
            <select
              :id="`modo-${i.id}`"
              class="form-control form-control-sm"
              :value="i.modo_liberatoria"
              @change="
                aggiorna({
                  modo_liberatoria: ($event.target as HTMLSelectElement).value as 'APP',
                })
              "
            >
              <option value="APP">Passa dall'app</option>
              <option value="ALTRI_CANALI">Per altri canali</option>
            </select>
          </div>
          <div>
            <label class="form-label small" :for="`scad-lib-${i.id}`"
              >Scadenza per la famiglia</label
            >
            <input
              :id="`scad-lib-${i.id}`"
              v-model="modifica.scadenzaLiberatoria"
              type="date"
              class="form-control form-control-sm"
            />
          </div>
          <button
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            :disabled="inCorso"
            @click="
              aggiorna(
                modifica.scadenzaLiberatoria
                  ? { scadenza_liberatoria: modifica.scadenzaLiberatoria }
                  : { scadenza_liberatoria_predefinita: true },
              )
            "
          >
            Salva la scadenza
          </button>
          <span class="small fg-2">Vuota: 2 giorni prima della scadenza dell'iscrizione.</span>
        </div>
        <div v-if="i.modo_liberatoria === 'APP'">
          <label class="form-label small" :for="`da-firmare-${i.id}`">
            Carica il PDF ricevuto da BuonaCaccia (la famiglia riceve un'email)
          </label>
          <input
            :id="`da-firmare-${i.id}`"
            type="file"
            accept="application/pdf"
            class="form-control form-control-sm"
            :disabled="inCorso"
            @change="carica($event, false)"
          />
        </div>
        <div class="d-flex flex-wrap gap-3">
          <button
            v-if="!i.liberatoria_ricevuta_il"
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            :disabled="inCorso"
            @click="passo({ liberatoria_ricevuta_il: oggi() })"
          >
            Segna arrivata oggi
          </button>
          <button
            v-if="i.liberatoria_ricevuta_il && !i.liberatoria_caricata_il"
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            :disabled="inCorso"
            @click="passo({ liberatoria_caricata_il: oggi() })"
          >
            Segna caricata su BuonaCaccia oggi
          </button>
          <template v-if="i.liberatoria_caricata_il && !i.esito_liberatoria">
            <button
              type="button"
              class="btn btn-sm btn-outline theme-success"
              :disabled="inCorso"
              @click="valida()"
            >
              Validata dalla segreteria
            </button>
            <button
              type="button"
              class="btn btn-sm btn-outline theme-danger"
              @click="rigetto = !rigetto"
            >
              Rigettata…
            </button>
          </template>
        </div>
        <form
          v-if="rigetto"
          class="d-flex flex-wrap align-items-end gap-3"
          @submit.prevent="rigetta"
        >
          <div class="flex-grow-1">
            <label class="form-label small" :for="`rigetto-${i.id}`"
              >Motivo (la famiglia lo legge)</label
            >
            <input
              :id="`rigetto-${i.id}`"
              v-model="modifica.motivoRigetto"
              class="form-control form-control-sm"
              required
            />
          </div>
          <button type="submit" class="btn btn-sm btn-solid theme-danger" :disabled="inCorso">
            Segna rigettata
          </button>
        </form>
      </div>
    </section>

    <!-- Event form (DEC-161, DEC-162) -->
    <section v-if="scheda" class="mb-3 pt-3 border-top">
      <h4 class="h6 fw-bold mb-1">Scheda dell'evento</h4>
      <p v-if="i.risposte_mancanti.length" class="small mb-1">
        Mancano: {{ i.risposte_mancanti.join('; ') }}.
      </p>
      <p v-else-if="i.risposte_il" class="small mb-1">Risposte complete.</p>
      <RisposteSchedaBC
        :iscrizione="i"
        :scheda="scheda"
        :modifica="i.puo_scrivere_scheda"
        @cambiata="emit('cambiata', $event)"
      />
      <template v-if="i.puo_gestire">
        <form class="mt-3" @submit.prevent="salvaPresentazione()">
          <label class="form-label small" :for="`pres-${i.id}`">
            Presentazione dello staff (la vedono solo i capi)
          </label>
          <textarea
            :id="`pres-${i.id}`"
            v-model="modifica.presentazione"
            class="form-control form-control-sm"
            rows="3"
          />
          <button
            type="submit"
            class="btn btn-sm btn-outline theme-primary mt-1"
            :disabled="inCorso"
          >
            Salva la presentazione
          </button>
        </form>
        <div class="d-flex flex-wrap gap-3 mt-3">
          <button
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            @click="mostraRiepilogo"
          >
            {{ riepilogo ? 'Chiudi il riepilogo' : 'Riepilogo da ricopiare su BuonaCaccia' }}
          </button>
          <button
            v-if="i.attiva && !i.scheda_inviata_il"
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            :disabled="inCorso"
            @click="passo({ scheda_inviata_il: oggi() })"
          >
            Segna compilata su BuonaCaccia oggi
          </button>
          <span v-else-if="i.scheda_inviata_il" class="small">
            Compilata su BuonaCaccia il {{ data(i.scheda_inviata_il) }}
          </span>
        </div>
        <div v-if="riepilogo" class="card card-body mt-3 small">
          <div v-for="r in riepilogo.righe" :key="r.domanda" class="mb-3">
            <div class="fg-2">{{ r.domanda }}</div>
            <div v-if="r.tipo === 'FOTO'">
              <a v-if="riepilogo.foto" :href="fileFotoBC(i.id)">Scarica la foto (JPG, max 1 MB)</a>
              <span v-else>—</span>
            </div>
            <div v-else class="d-flex align-items-start gap-3">
              <span class="testo-a-capo flex-grow-1">{{ r.risposta || '—' }}</span>
              <button
                v-if="r.risposta"
                type="button"
                class="btn btn-sm btn-link p-0"
                @click="copia(r.risposta, r.domanda)"
              >
                {{ copiato === r.domanda ? 'Copiata' : 'Copia' }}
              </button>
            </div>
          </div>
          <div class="fg-2">Presentazione dello staff</div>
          <div class="d-flex align-items-start gap-3">
            <span class="testo-a-capo flex-grow-1">{{ riepilogo.presentazione || '—' }}</span>
            <button
              v-if="riepilogo.presentazione"
              type="button"
              class="btn btn-sm btn-link p-0"
              @click="copia(riepilogo.presentazione, 'presentazione')"
            >
              {{ copiato === 'presentazione' ? 'Copiata' : 'Copia' }}
            </button>
          </div>
        </div>
      </template>
    </section>

    <!-- Payment and the family's fee (DEC-163) -->
    <section class="mb-3 pt-3 border-top">
      <h4 class="h6 fw-bold mb-1">Quota</h4>
      <p v-if="i.quota && !i.quota.annullata" class="small mb-1">
        Quota per la famiglia {{ euro(i.quota.importo) }}, entro il {{ data(i.quota.scadenza) }}:
        <template v-if="Number(i.quota.residuo) <= 0">pagata.</template>
        <template v-else>
          da pagare {{ euro(i.quota.residuo) }}.
          <RouterLink v-if="i.puo_rispondere" to="/mie-quote">Le mie quote</RouterLink>
        </template>
      </p>
      <p v-else-if="i.quota?.annullata" class="small mb-1">Quota tolta.</p>
      <p v-else class="small fg-2 mb-1">Nessuna quota per la famiglia.</p>
      <template v-if="i.puo_gestire">
        <p class="small mb-1">
          <template v-if="i.pagata_il">Pagata su BuonaCaccia il {{ data(i.pagata_il) }}.</template>
          <button
            v-else-if="i.attiva"
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            :disabled="inCorso"
            @click="passo({ pagata_il: oggi() })"
          >
            Segna pagata su BuonaCaccia oggi
          </button>
          <span class="fg-2">
            Il pagamento a BuonaCaccia si registra come uscita in
            <RouterLink to="/cassa">prima nota</RouterLink> (voce A.2).
          </span>
        </p>
        <form
          v-if="i.attiva || (i.quota && !i.quota.annullata)"
          class="d-flex flex-wrap align-items-end gap-3"
          @submit.prevent="salvaQuota()"
        >
          <div>
            <label class="form-label small" :for="`importo-${i.id}`">Importo (€)</label>
            <input
              :id="`importo-${i.id}`"
              v-model="modifica.importo"
              type="number"
              min="0.01"
              step="0.01"
              class="form-control form-control-sm"
              required
            />
          </div>
          <div>
            <label class="form-label small" :for="`scad-q-${i.id}`">Da pagare entro</label>
            <input
              :id="`scad-q-${i.id}`"
              v-model="modifica.scadenzaQuota"
              type="date"
              class="form-control form-control-sm"
              required
            />
          </div>
          <button type="submit" class="btn btn-sm btn-outline theme-primary" :disabled="inCorso">
            {{ i.quota && !i.quota.annullata ? 'Cambia la quota' : 'Crea la quota' }}
          </button>
        </form>
        <button
          v-if="i.puo_togliere_quota"
          type="button"
          class="btn btn-sm btn-outline theme-danger mt-1"
          :disabled="inCorso"
          @click="togliQuota()"
        >
          Togli la quota
        </button>
      </template>
    </section>

    <!-- Status -->
    <section v-if="i.puo_gestire && i.attiva" class="d-flex flex-wrap align-items-end gap-3">
      <button
        type="button"
        class="btn btn-sm btn-outline theme-secondary"
        :disabled="inCorso"
        @click="aggiorna({ stato: i.stato === 'AMMESSO' ? 'IN_ATTESA' : 'AMMESSO' })"
      >
        {{ i.stato === 'AMMESSO' ? "Torna in lista d'attesa" : 'Ammesso' }}
      </button>
      <div>
        <label class="form-label small" :for="`chiudi-${i.id}`">Chiudi l'iscrizione</label>
        <select
          :id="`chiudi-${i.id}`"
          v-model="modifica.chiusura"
          class="form-control form-control-sm"
        >
          <option value="">—</option>
          <option value="CANCELLATA">Cancellata su BuonaCaccia</option>
          <option value="NON_AMMESSO">Non ammesso</option>
        </select>
      </div>
      <template v-if="modifica.chiusura">
        <div>
          <label class="form-label small" :for="`chiusa-il-${i.id}`">Il</label>
          <input
            :id="`chiusa-il-${i.id}`"
            v-model="modifica.chiusaIl"
            type="date"
            class="form-control form-control-sm"
          />
        </div>
        <button
          type="button"
          class="btn btn-sm btn-solid theme-danger"
          :disabled="inCorso"
          @click="chiudi"
        >
          Conferma
        </button>
      </template>
    </section>
  </li>
</template>
