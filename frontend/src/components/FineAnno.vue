<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { api, type AnniGruppo, type ArchivioGruppo, type EsitoImportazione } from '@/api/qdc'
import SezioneApribile from '@/components/SezioneApribile.vue'
import { useErrore } from '@/composables/useErrore'

// For the capigruppo (DEC-44…DEC-46, DEC-209…DEC-213): close a year once accounts and
// checks are done, reopen it for a correction until a chosen day; archive who left more
// than two years ago to the group's shared Drive; import a file from another group.
// Online only.
const { errore, inCorso, esegui } = useErrore()
const anni = ref<AnniGruppo | null>(null)
const archivio = ref<ArchivioGruppo | null>(null)
const esito = ref('')
const importato = ref<EsitoImportazione | null>(null)
const oggi = () => new Date().toLocaleDateString('sv')
const data = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString('it-IT') : '')

onMounted(async () => {
  anni.value = (await esegui(() => api.anniGruppo())) ?? null
  archivio.value = (await esegui(() => api.archivio())) ?? null
})

const riapertura = reactive({ anno: 0, fino_al: '', motivo: '' })

async function chiudi(anno: number) {
  const nuovi = await esegui(() => api.chiudiAnno(anno))
  if (nuovi) {
    anni.value = nuovi
    esito.value = 'Anno chiuso.'
  }
}

async function riapri() {
  const nuovi = await esegui(() =>
    api.riapriAnno(riapertura.anno, riapertura.fino_al, riapertura.motivo),
  )
  if (nuovi) {
    anni.value = nuovi
    riapertura.anno = 0
    esito.value = 'Anno riaperto fino alla data indicata.'
  }
}

const confermando = ref(0)
async function archivia(id: number) {
  const nuovi = await esegui(() => api.archivia(id))
  confermando.value = 0
  if (nuovi) {
    archivio.value = nuovi
    esito.value = 'Archiviato sul Drive del gruppo: nell’app restano nome e anni nel gruppo.'
  }
}

// Units with only archived people in their history (DEC-275): a change of state, back
// by themselves when one of them returns.
async function archiviaUnita(id: number) {
  const nuovi = await esegui(() => api.archiviaUnita(id))
  if (nuovi) {
    archivio.value = nuovi
    esito.value = 'Unità archiviata: torna da sola se rientra qualcuno che ne ha fatto parte.'
  }
}

async function ripristinaUnita(id: number) {
  const nuovi = await esegui(() => api.ripristinaUnita(id))
  if (nuovi) {
    archivio.value = nuovi
    esito.value = 'Unità ripristinata: è di nuovo tra le unità chiuse.'
  }
}

async function importa(evento: Event) {
  const input = evento.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  importato.value = (await esegui(() => api.importaTrasferimento(file))) ?? null
  input.value = ''
}
</script>

<template>
  <section v-if="anni || archivio" class="mt-5">
    <div v-if="errore" class="alert theme-danger small" role="alert">{{ errore }}</div>
    <div v-if="esito" class="alert theme-success small" role="status">
      <div>{{ esito }}</div>
    </div>

    <template v-if="anni">
      <h2 class="h5">Anni associativi</h2>
      <p class="small fg-2">
        Chiudi un anno quando rendiconto e verifiche sono fatti: da allora presenze, Progressione,
        quote e prima nota di quell'anno non si modificano. Per una correzione lo puoi riaprire fino
        a un giorno che scegli (al massimo 30 giorni).
      </p>
      <div v-if="anni.da_chiudere" class="alert theme-warning small" role="status">
        <div>L'anno appena finito è ancora aperto.</div>
      </div>
      <ul class="list-group mb-5">
        <li v-for="a in anni.anni" :key="a.anno" class="list-group-item small">
          <div class="d-flex flex-wrap align-items-center gap-3">
            <strong>{{ a.etichetta }}</strong>
            <span v-if="a.in_corso" class="badge theme-secondary">in corso</span>
            <span v-else-if="a.riaperto_fino_al" class="badge theme-warning">
              riaperto fino al {{ data(a.riaperto_fino_al) }}: {{ a.motivo_riapertura }}
            </span>
            <span v-else-if="a.chiuso_il" class="badge theme-success">
              chiuso il {{ data(a.chiuso_il) }}
            </span>
            <span v-else class="badge theme-info">aperto</span>
            <template v-if="!a.in_corso">
              <button
                v-if="!a.chiuso_il || a.riaperto_fino_al"
                type="button"
                class="btn btn-sm btn-outline theme-primary ms-auto"
                :disabled="inCorso"
                @click="chiudi(a.anno)"
              >
                Chiudi
              </button>
              <button
                v-else
                type="button"
                class="btn btn-sm btn-link ms-auto"
                @click="Object.assign(riapertura, { anno: a.anno, fino_al: oggi(), motivo: '' })"
              >
                Riapri…
              </button>
            </template>
          </div>
          <form
            v-if="riapertura.anno === a.anno"
            class="d-flex flex-wrap align-items-end gap-3 mt-1"
            @submit.prevent="riapri"
          >
            <div>
              <label class="form-label small" :for="`fino-${a.anno}`">Fino al</label>
              <input
                :id="`fino-${a.anno}`"
                v-model="riapertura.fino_al"
                type="date"
                :min="oggi()"
                class="form-control form-control-sm"
                required
              />
            </div>
            <div class="flex-grow-1">
              <label class="form-label small" :for="`motivo-${a.anno}`">Perché</label>
              <input
                :id="`motivo-${a.anno}`"
                v-model="riapertura.motivo"
                class="form-control form-control-sm"
                required
              />
            </div>
            <button type="submit" class="btn btn-sm btn-solid theme-warning" :disabled="inCorso">
              Riapri
            </button>
            <button type="button" class="btn btn-sm btn-link" @click="riapertura.anno = 0">
              Annulla
            </button>
          </form>
        </li>
      </ul>
    </template>

    <template v-if="archivio">
      <h2 class="h5">Archivio</h2>
      <p class="small fg-2">
        Due anni dopo l'uscita il fascicolo va sul Drive condiviso del gruppo (un file ZIP con il
        fascicolo, un PDF per anno, foto e allegati); verificato il caricamento, nell'app restano
        solo nome e anni nel gruppo, per riconoscere chi rientra. Con l'ultimo figlio vanno anche i
        genitori che non hanno altri figli nel gruppo: di loro nell'app non resta nulla.
      </p>
      <div v-if="!archivio.drive_configurato" class="alert theme-warning small" role="status">
        <div>
          L'archivio non è ancora configurato (Drive del gruppo e chiave per riconoscere chi
          rientra): lo configura chi ha installato l'app.
        </div>
      </div>
      <p v-if="!archivio.da_archiviare.length" class="small">Nessuno da archiviare.</p>
      <ul v-else class="list-group mb-3">
        <li
          v-for="p in archivio.da_archiviare"
          :key="p.id"
          class="list-group-item small d-flex flex-wrap align-items-center gap-3"
        >
          <span>
            {{ p.nome }} · uscito il {{ data(p.uscita) }}
            <template v-if="p.genitori.length">
              · con i genitori {{ p.genitori.join(', ') }} (nessun altro figlio nel gruppo)
            </template>
          </span>
          <template v-if="archivio.drive_configurato">
            <button
              v-if="confermando !== p.id"
              type="button"
              class="btn btn-sm btn-outline theme-primary ms-auto"
              @click="confermando = p.id"
            >
              Archivia…
            </button>
            <span v-else class="ms-auto d-flex align-items-center gap-1">
              Carica sul Drive e poi cancella dall'app{{
                p.genitori.length ? ' (i genitori del tutto)' : ''
              }}?
              <button
                type="button"
                class="btn btn-sm btn-solid theme-danger"
                :disabled="inCorso"
                @click="archivia(p.id)"
              >
                Confermo
              </button>
              <button type="button" class="btn btn-sm btn-link" @click="confermando = 0">No</button>
            </span>
          </template>
        </li>
      </ul>
      <SezioneApribile
        v-if="archivio.archiviate.length"
        :titolo="`Già archiviati (${archivio.archiviate.length})`"
        class="mb-5"
      >
        <ul class="mb-0">
          <li v-for="a in archivio.archiviate" :key="a.nome_file">
            {{ a.nome }} · {{ data(a.archiviata_il) }} · sul Drive: «{{ a.nome_file }}»
          </li>
        </ul>
      </SezioneApribile>

      <h3 class="h6">Unità</h3>
      <p class="small fg-2">
        Un'unità chiusa in cui tutti sono stati archiviati si archivia: sparisce dagli elenchi e
        torna da sola, sempre chiusa, se rientra qualcuno che ne ha fatto parte.
      </p>
      <p v-if="!archivio.unita_da_archiviare?.length" class="small">Nessuna unità da archiviare.</p>
      <ul v-else class="list-group mb-3">
        <li
          v-for="u in archivio.unita_da_archiviare"
          :key="u.id"
          class="list-group-item small d-flex flex-wrap align-items-center gap-3"
        >
          <span>{{ u.nome }}</span>
          <button
            type="button"
            class="btn btn-sm btn-outline theme-primary ms-auto"
            :disabled="inCorso"
            @click="archiviaUnita(u.id)"
          >
            Archivia
          </button>
        </li>
      </ul>
      <SezioneApribile
        v-if="archivio.unita_archiviate?.length"
        :titolo="`Unità archiviate (${archivio.unita_archiviate.length})`"
        class="mb-5"
      >
        <ul class="list-unstyled mb-0">
          <li
            v-for="u in archivio.unita_archiviate"
            :key="u.id"
            class="d-flex flex-wrap align-items-center gap-3 mb-1"
          >
            <span>{{ u.nome }} · archiviata il {{ data(u.archiviata_il) }}</span>
            <button
              type="button"
              class="btn btn-sm btn-link"
              :disabled="inCorso"
              @click="ripristinaUnita(u.id)"
            >
              Ripristina
            </button>
          </li>
        </ul>
      </SezioneApribile>

      <h2 class="h5">Fascicolo da un altro gruppo o dall'archivio</h2>
      <p class="small fg-2">
        Chi arriva da un altro gruppo che usa il Quaderno di Caccia: carica il file che ti ha
        mandato il suo capogruppo. Chi rientra nel gruppo dopo l'archiviazione, anche come capo:
        carica lo ZIP dell'archivio preso dal Drive. La persona deve essere già nell'anagrafica, da
        BuonaStrada. Tornano la Progressione, le note non riservate, il percorso scout (gli anni nel
        gruppo di provenienza diventano anni in un altro gruppo; quelli che ci sono già si saltano)
        e, per un capo, servizio e formazione; per chi rientra, anche gli anni già passati nel
        gruppo.
      </p>
      <label class="btn btn-sm btn-outline theme-primary" for="importa-fascicolo">
        Carica il file
      </label>
      <input
        id="importa-fascicolo"
        type="file"
        accept="application/json,.json,application/zip,.zip"
        class="d-none"
        @change="importa"
      />
      <div v-if="importato" class="alert theme-success small mt-3" role="status">
        <div>
          Importato per {{ importato.persona }}: {{ importato.periodi }} periodi di Progressione,
          {{ importato.note }} note, {{ importato.anni_di_servizio }} anni di servizio,
          {{ importato.formazione }} voci di formazione, {{ importato.percorso }} periodi del
          percorso scout.
        </div>
      </div>
    </template>
  </section>
</template>
