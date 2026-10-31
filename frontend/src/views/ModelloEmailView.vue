<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { api, type AnteprimaEmail, type ModelloEmail } from '@/api/qdc'
import EditorTesto from '@/components/EditorTesto.vue'
import { useErrore } from '@/composables/useErrore'
import { useNomePagina } from '@/composables/useNomePagina'

// One email template (DEC-250): subject and formatted text with placeholders; the plain
// text version is derived by the server. Indispensable placeholders must be there, or
// the server refuses to save.
const props = defineProps<{ chiave: string }>()
const { errore, inCorso, esegui } = useErrore()
const modello = ref<ModelloEmail | null>(null)
const oggetto = ref('')
const corpo = ref('')
const esito = ref('')
const anteprima = ref<AnteprimaEmail | null>(null)
const editor = ref<InstanceType<typeof EditorTesto> | null>(null)

useNomePagina(() => modello.value?.nome)

function mostra(dati: ModelloEmail) {
  modello.value = dati
  oggetto.value = dati.oggetto
  corpo.value = dati.corpo
}

onMounted(async () => {
  const dati = await esegui(() => api.modelloEmail(props.chiave))
  if (dati) mostra(dati)
})

const usati = computed(() => (oggetto.value + ' ' + corpo.value).toLowerCase())
const mancanti = computed(
  () =>
    modello.value?.segnaposto.filter(
      (s) => s.indispensabile && !usati.value.includes(`[${s.nome.toLowerCase()}]`),
    ) ?? [],
)

async function salva() {
  esito.value = ''
  const dati = await esegui(() =>
    api.salvaModelloEmail(props.chiave, { oggetto: oggetto.value, corpo: corpo.value }),
  )
  if (!dati) return
  mostra(dati)
  esito.value = 'Modello salvato: da ora le email partono con questo testo.'
}

async function ripristina() {
  esito.value = ''
  const dati = await esegui(() => api.ripristinaModelloEmail(props.chiave))
  if (!dati) return
  mostra(dati)
  anteprima.value = null
  esito.value = 'Tornato al testo di base.'
}

async function piede(attivo: boolean) {
  const dati = await esegui(() => api.piedeDelModello(props.chiave, attivo))
  if (dati && modello.value) modello.value.con_piede = dati.con_piede
}

async function vedi() {
  anteprima.value =
    (await esegui(() =>
      api.anteprimaModelloEmail(props.chiave, { oggetto: oggetto.value, corpo: corpo.value }),
    )) ?? null
}
</script>

<template>
  <section>
    <RouterLink to="/impostazioni" class="small">Torna alle impostazioni</RouterLink>
    <div v-if="errore" class="alert theme-danger small mt-3" role="alert">{{ errore }}</div>
    <template v-if="modello">
      <h1 class="h4 mb-1 mt-3">{{ modello.nome }}</h1>
      <p class="fg-2 small">{{ modello.descrizione }}</p>
      <div v-if="modello.da_correggere" class="alert theme-warning small" role="status">
        <div>
          Questo modello non contiene più tutto quello che serve: finché non lo correggi, l'email
          parte con il testo di base.
        </div>
      </div>
      <div v-if="esito" class="alert theme-success small" role="status">
        <div>{{ esito }}</div>
      </div>
      <form class="card card-body mb-5" @submit.prevent="salva">
        <label class="form-label small mb-0" for="email-oggetto">Oggetto</label>
        <input id="email-oggetto" v-model="oggetto" class="form-control mb-3" required />
        <EditorTesto ref="editor" v-model="corpo" etichetta="Testo dell'email" immagini />
        <div class="form-field mt-3">
          <div class="switch">
            <input
              id="email-piede"
              type="checkbox"
              role="switch"
              :checked="modello.con_piede !== false"
              :disabled="inCorso"
              @change="piede(($event.target as HTMLInputElement).checked)"
            />
          </div>
          <label for="email-piede">
            Aggiungi il <RouterLink to="/impostazioni/email-piede">piè di pagina comune</RouterLink>
          </label>
        </div>
        <p v-if="modello.facoltativa" class="form-text">
          In fondo l'app aggiunge sempre la riga per scegliere quali email ricevere.
        </p>
        <div class="mt-3">
          <span class="small">Segnaposto: tocca per inserirlo nel testo</span>
          <div class="d-flex flex-wrap gap-1 mt-1">
            <button
              v-for="s in modello.segnaposto"
              :key="s.nome"
              type="button"
              class="btn btn-sm"
              :class="s.indispensabile ? 'btn-solid theme-primary' : 'btn-outline theme-primary'"
              :title="s.descrizione"
              @click="editor?.inserisci(`[${s.nome}]`)"
            >
              [{{ s.nome }}]
            </button>
          </div>
          <ul class="small fg-2 mt-3 mb-0">
            <li v-for="s in modello.segnaposto" :key="s.nome">
              <code>[{{ s.nome }}]</code>: {{ s.descrizione
              }}<strong v-if="s.indispensabile"> (indispensabile)</strong>
            </li>
          </ul>
        </div>
        <div v-if="mancanti.length" class="alert theme-warning small mt-3" role="status">
          <div>
            Mancano: {{ mancanti.map((s) => `[${s.nome}]`).join(', ') }}. Senza questi il modello
            non si può salvare.
          </div>
        </div>
        <div class="d-flex flex-wrap gap-3 mt-3">
          <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
            Salva
          </button>
          <button
            type="button"
            class="btn btn-sm btn-outline theme-primary"
            :disabled="inCorso"
            @click="vedi"
          >
            Anteprima
          </button>
          <button
            v-if="modello.personalizzato"
            type="button"
            class="btn btn-sm btn-link"
            :disabled="inCorso"
            @click="ripristina"
          >
            Torna al testo di base
          </button>
        </div>
      </form>
      <section v-if="anteprima" class="mb-5">
        <h2 class="h5">Anteprima, con dati di esempio</h2>
        <p class="small"><strong>Oggetto:</strong> {{ anteprima.oggetto }}</p>
        <!-- Sandboxed: the HTML is already cleaned by the server, this is one more fence. -->
        <iframe
          class="qdc-anteprima-email card w-100"
          sandbox=""
          :srcdoc="anteprima.html"
          title="Anteprima dell'email formattata"
        ></iframe>
        <details class="small mt-3">
          <summary>Versione solo testo</summary>
          <pre class="mt-1 mb-0 qdc-testo-email">{{ anteprima.testo }}</pre>
        </details>
      </section>
    </template>
  </section>
</template>
