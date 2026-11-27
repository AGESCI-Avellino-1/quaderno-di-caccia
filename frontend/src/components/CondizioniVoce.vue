<script setup lang="ts">
import type { CondizioneVoce, LibroCerimonie } from '@/api/qdc'

// The conditions of an entry of the book of ceremonies (DEC-437): groups of conditions, all
// of a group must hold, one group is enough. Each kind brings its own choices.
const props = defineProps<{ libro: LibroCerimonie }>()
const gruppi = defineModel<CondizioneVoce[][]>({ required: true })

type Tipo = CondizioneVoce['tipo']
const TIPI: { tipo: Tipo; nome: string }[] = [
  { tipo: 'unita', nome: "È in un'unità" },
  { tipo: 'branca', nome: 'È in una branca' },
  { tipo: 'incarico', nome: 'Ha un incarico' },
  { tipo: 'consiglio_capi', nome: 'È nel Consiglio capi' },
  { tipo: 'alta_squadriglia', nome: "È nell'Alta Squadriglia quest'anno" },
  { tipo: 'totem', nome: 'Ha il nome di totem' },
  { tipo: 'passaggio', nome: "Passa da una branca all'altra" },
  { tipo: 'promessa', nome: 'Ha fatto la Promessa' },
  { tipo: 'tappa', nome: 'Ha raggiunto una tappa' },
  { tipo: 'partenza', nome: 'Ha preso la Partenza' },
  { tipo: 'partecipazione', nome: 'Ha vissuto una voce del libro' },
]
const BRANCHE = [
  { valore: 'LC', nome: 'Lupetti e Coccinelle' },
  { valore: 'EG', nome: 'Esploratori e Guide' },
  { valore: 'RS', nome: 'Rover e Scolte' },
]
const FASI = [
  { valore: 'SCOPERTA', nome: 'Scoperta' },
  { valore: 'COMPETENZA', nome: 'Competenza' },
  { valore: 'RESPONSABILITA', nome: 'Responsabilità' },
]

/** A condition of that kind with its first choices filled in. */
function nuova(tipo: Tipo): CondizioneVoce {
  switch (tipo) {
    case 'unita':
      return { tipo, unita: props.libro.unita_condizioni[0]?.id }
    case 'branca':
      return { tipo, branca: 'EG' }
    case 'incarico':
      return { tipo, ruolo: props.libro.incarichi[0]?.valore }
    case 'passaggio':
      return { tipo, da: 'LC', a: 'EG' }
    case 'tappa':
      return { tipo, branca: 'EG', fase: 'SCOPERTA' }
    case 'partecipazione':
      return { tipo, voce: props.libro.voci[0]?.id }
    default:
      return { tipo }
  }
}

function cambiaTipo(g: number, c: number, tipo: Tipo) {
  gruppi.value[g]![c] = nuova(tipo)
}

function aggiungi(g: number) {
  gruppi.value[g]!.push(nuova('unita'))
}

function togli(g: number, c: number) {
  gruppi.value[g]!.splice(c, 1)
  if (!gruppi.value[g]!.length) gruppi.value.splice(g, 1)
}

function nuovoGruppo() {
  gruppi.value.push([nuova('unita')])
}
</script>

<template>
  <fieldset>
    <legend class="form-label small">Condizioni</legend>
    <p v-if="!gruppi.length" class="small fg-2 mb-3">
      Nessuna condizione: dei ragazzi/e la leggono solo quelli scelti a mano qui sotto.
    </p>
    <template v-for="(gruppo, g) in gruppi" :key="g">
      <p v-if="g > 0" class="small fw-bold my-3">oppure</p>
      <div class="card card-body mb-3" :data-gruppo="g">
        <p class="small fg-2 mb-3">
          {{ gruppo.length > 1 ? 'Valgono tutte insieme:' : 'Vale questa:' }}
        </p>
        <div
          v-for="(c, i) in gruppo"
          :key="i"
          class="d-flex flex-wrap gap-3 align-items-center mb-3"
          data-condizione
        >
          <select
            :value="c.tipo"
            class="form-control form-control-sm w-auto"
            aria-label="Condizione"
            @change="cambiaTipo(g, i, ($event.target as HTMLSelectElement).value as Tipo)"
          >
            <option v-for="t in TIPI" :key="t.tipo" :value="t.tipo">{{ t.nome }}</option>
          </select>
          <select
            v-if="c.tipo === 'unita'"
            v-model="c.unita"
            class="form-control form-control-sm w-auto"
            aria-label="Unità"
          >
            <option v-for="u in libro.unita_condizioni" :key="u.id" :value="u.id">
              {{ u.nome }}
            </option>
          </select>
          <select
            v-if="c.tipo === 'branca' || c.tipo === 'tappa'"
            v-model="c.branca"
            class="form-control form-control-sm w-auto"
            aria-label="Branca"
          >
            <option v-for="b in BRANCHE" :key="b.valore" :value="b.valore">{{ b.nome }}</option>
          </select>
          <select
            v-if="c.tipo === 'tappa'"
            v-model="c.fase"
            class="form-control form-control-sm w-auto"
            aria-label="Tappa"
          >
            <option v-for="f in FASI" :key="f.valore" :value="f.valore">{{ f.nome }}</option>
          </select>
          <select
            v-if="c.tipo === 'incarico'"
            v-model="c.ruolo"
            class="form-control form-control-sm w-auto"
            aria-label="Incarico"
          >
            <option v-for="r in libro.incarichi" :key="r.valore" :value="r.valore">
              {{ r.nome }}
            </option>
          </select>
          <select
            v-if="c.tipo === 'partecipazione'"
            v-model="c.voce"
            class="form-control form-control-sm w-auto"
            aria-label="Voce del libro"
          >
            <option v-for="v in libro.voci" :key="v.id" :value="v.id">{{ v.titolo }}</option>
          </select>
          <template v-if="c.tipo === 'passaggio'">
            <select v-model="c.da" class="form-control form-control-sm w-auto" aria-label="Da">
              <option v-for="b in BRANCHE" :key="b.valore" :value="b.valore">
                da {{ b.nome }}
              </option>
            </select>
            <select v-model="c.a" class="form-control form-control-sm w-auto" aria-label="A">
              <option v-for="b in BRANCHE" :key="b.valore" :value="b.valore">a {{ b.nome }}</option>
            </select>
          </template>
          <button
            type="button"
            class="btn btn-sm btn-link"
            :aria-label="`Togli la condizione ${i + 1}`"
            @click="togli(g, i)"
          >
            Togli
          </button>
        </div>
        <div>
          <button type="button" class="btn btn-sm btn-outline theme-primary" @click="aggiungi(g)">
            Aggiungi una condizione
          </button>
        </div>
      </div>
    </template>
    <button type="button" class="btn btn-sm btn-outline theme-primary" @click="nuovoGruppo">
      {{ gruppi.length ? 'Aggiungi un altro gruppo, in alternativa' : 'Aggiungi una condizione' }}
    </button>
  </fieldset>
</template>
