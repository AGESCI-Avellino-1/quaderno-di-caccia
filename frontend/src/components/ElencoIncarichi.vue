<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { api, type DoveIncarico, type Incarico, type PersonaBreve, type Scelta } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Active roles of the group, a unit or a patrol, with "assign" and "close" for the roles
// the backend says this user may handle (`nomina`). Online only, like invitations.
const props = defineProps<{
  incarichi: Incarico[]
  nomina: Scelta[]
  dove: DoveIncarico
  /** Who can hold a role: capi, or the ragazzi of the unit for CSQ/VCSQ. */
  candidati: (ruolo: string) => Promise<PersonaBreve[]>
  vuoto?: string
}>()
const emit = defineEmits<{ cambiato: [] }>()

const { errore, inCorso, esegui } = useErrore()
const ruolo = ref('')
const persona = ref<number | null>(null)
const elenco = ref<PersonaBreve[]>([])
const daChiudere = ref<number | null>(null)

const gestibili = computed(() => new Set(props.nomina.map((n) => n.valore)))

watch(ruolo, async (valore) => {
  persona.value = null
  elenco.value = valore ? ((await esegui(() => props.candidati(valore))) ?? []) : []
})

async function assegna() {
  if (!ruolo.value || persona.value === null) return
  const fatto = await esegui(() =>
    api.nomina({ persona_id: persona.value!, ruolo: ruolo.value, ...props.dove }),
  )
  if (!fatto) return
  ruolo.value = ''
  emit('cambiato')
}

async function chiudi(id: number) {
  const fatto = await esegui(() => api.terminaIncarico(id))
  daChiudere.value = null
  if (fatto) emit('cambiato')
}

const data = (iso: string) => new Date(iso).toLocaleDateString('it-IT')
</script>

<template>
  <div>
    <div v-if="errore" class="alert theme-danger py-3 small" role="alert">{{ errore }}</div>
    <ul class="list-unstyled mb-3">
      <li v-for="i in incarichi" :key="i.id" class="d-flex flex-wrap align-items-baseline gap-3">
        <span class="fg-2 small">{{ i.ruolo_nome }}</span>
        <span>{{ i.persona.nome }} {{ i.persona.cognome }}</span>
        <span class="fg-2 small">dal {{ data(i.data_inizio) }}</span>
        <template v-if="gestibili.has(i.ruolo)">
          <button
            v-if="daChiudere !== i.id"
            type="button"
            class="btn btn-link btn-sm p-0"
            @click="daChiudere = i.id"
          >
            chiudi
          </button>
          <span v-else class="small">
            Chiudere da oggi?
            <button
              type="button"
              class="btn btn-sm btn-solid theme-danger py-0"
              :disabled="inCorso"
              @click="chiudi(i.id)"
            >
              Sì
            </button>
            <button type="button" class="btn btn-sm btn-link py-0" @click="daChiudere = null">
              No
            </button>
          </span>
        </template>
      </li>
      <li v-if="!incarichi.length" class="fg-2 small">
        {{ vuoto ?? 'Nessun incarico.' }}
      </li>
    </ul>

    <form v-if="nomina.length" class="row g-3 align-items-end" @submit.prevent="assegna">
      <div class="col-12 sm:col-4">
        <select v-model="ruolo" class="form-control form-control-sm" aria-label="Incarico">
          <option value="">Assegna un incarico…</option>
          <option v-for="n in nomina" :key="n.valore" :value="n.valore">{{ n.etichetta }}</option>
        </select>
      </div>
      <div v-if="ruolo" class="col-12 sm:col-5">
        <select
          v-model="persona"
          class="form-control form-control-sm"
          aria-label="Persona"
          required
        >
          <option :value="null" disabled>Chi</option>
          <option v-for="p in elenco" :key="p.id" :value="p.id">
            {{ p.cognome }} {{ p.nome }}
          </option>
        </select>
      </div>
      <div v-if="ruolo" class="col-12 sm:col-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary w-100" :disabled="inCorso">
          Assegna
        </button>
      </div>
    </form>
  </div>
</template>
