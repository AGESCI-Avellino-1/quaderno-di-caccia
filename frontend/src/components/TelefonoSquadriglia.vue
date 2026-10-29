<script setup lang="ts">
import { ref, watch } from 'vue'

import { api, type ImpostazioneTelefono } from '@/api/qdc'
import { useErrore } from '@/composables/useErrore'

// Which phone the patrol sees for this person, and whether to hide it (DEC-13): set by
// the parents of a minor, the adult member, the unit staff and the capigruppo. The
// backend answers 404 to anyone else. Online only.
// Order (maintainer, 2026-10-29): the child's own BuonaStrada mobile; else the parent or
// guardian chosen for this child; else the one chosen for all the children; else none.
const props = defineProps<{ id: number }>()
const { errore, inCorso, esegui } = useErrore()
const stato = ref<ImpostazioneTelefono | null>(null)
const genitore = ref('')
const perTutti = ref(false)
const nascosto = ref(false)
const salvato = ref(false)

function mostra(dati: ImpostazioneTelefono) {
  stato.value = dati
  const scelto = dati.genitore_id ?? dati.famiglia_id
  genitore.value = scelto ? String(scelto) : ''
  perTutti.value = !dati.genitore_id && !!dati.famiglia_id
  nascosto.value = dati.nascosto
}

watch(
  () => props.id,
  async (id) => {
    try {
      mostra(await api.telefonoSquadriglia(id))
    } catch {
      stato.value = null
    }
  },
  { immediate: true },
)

async function salva() {
  salvato.value = false
  const dati = await esegui(() =>
    api.impostaTelefonoSquadriglia(props.id, {
      genitore_id: genitore.value ? Number(genitore.value) : null,
      per_tutti_i_figli: !!genitore.value && perTutti.value,
      nascosto: nascosto.value,
    }),
  )
  if (!dati) return
  mostra(dati)
  salvato.value = true
}
</script>

<template>
  <section v-if="stato?.in_squadriglia" class="card card-body mb-5">
    <h2 class="h5 mb-1">Telefono in squadriglia</h2>
    <p class="form-text mb-3">
      Gli altri ragazzi della squadriglia vedono questo numero; il capo squadriglia vede anche
      quelli dei genitori. Niente email.
    </p>
    <div v-if="errore" class="alert theme-danger py-3 small" role="alert">{{ errore }}</div>
    <form class="vstack gap-3" @submit.prevent="salva">
      <p v-if="stato.proprio" class="small mb-0">
        Numero in squadriglia: <strong>{{ stato.proprio }}</strong
        >, il suo cellulare registrato in BuonaStrada.
      </p>
      <template v-else>
        <div>
          <label class="form-label small" for="telefono-squadriglia">
            Non ha un cellulare suo: quale numero mostrare?
          </label>
          <select
            id="telefono-squadriglia"
            v-model="genitore"
            class="form-control form-control-sm"
            @change="salvato = false"
          >
            <option value="">Nessun numero</option>
            <option v-for="g in stato.genitori" :key="g.valore" :value="g.valore">
              Cellulare di {{ g.etichetta }}
            </option>
          </select>
          <p v-if="!stato.genitori.length" class="form-text mb-0">
            Nessun genitore o tutore ha un cellulare registrato.
          </p>
        </div>
        <div v-if="genitore" class="form-field">
          <input
            id="telefono-per-tutti"
            v-model="perTutti"
            type="checkbox"
            class="check"
            @change="salvato = false"
          />
          <label class="small" for="telefono-per-tutti">
            Usalo per tutti i figli senza cellulare
          </label>
        </div>
      </template>
      <div class="form-field">
        <input
          id="telefono-nascosto"
          v-model="nascosto"
          type="checkbox"
          class="check"
          @change="salvato = false"
        />
        <label class="small" for="telefono-nascosto">
          Non mostrarlo agli altri ragazzi (il capo squadriglia lo vede comunque)
        </label>
      </div>
      <div class="d-flex align-items-center gap-3">
        <button type="submit" class="btn btn-sm btn-solid theme-primary" :disabled="inCorso">
          Salva
        </button>
        <span v-if="salvato" class="small fg-success" role="status">Salvato</span>
      </div>
    </form>
  </section>
</template>
