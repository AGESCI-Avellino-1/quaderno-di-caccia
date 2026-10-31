<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import Icona from '@/components/Icona.vue'
import { gruppiMenu, vociProfilo, type Gruppo } from '@/navigazione/menu'
import { useNavigazioneStore } from '@/stores/navigazione'
import { useSessioneStore } from '@/stores/sessione'

// The Home shows the menu's groups as cards (DEC-241): a group with nothing the user
// may use is not there at all.
const sessione = useSessioneStore()
const navigazione = useNavigazioneStore()
const router = useRouter()

const gruppi = computed<Gruppo[]>(() => {
  const p = sessione.profilo
  if (!p) return []
  const profilo = vociProfilo(p)
  return [
    ...gruppiMenu(p, navigazione.contatori),
    ...(profilo.length
      ? [{ chiave: 'profilo', titolo: 'Profilo', icona: 'person-circle' as const, voci: profilo }]
      : []),
  ]
})

onMounted(async () => {
  // The counters on the cards change while the app is open: read the profile again.
  if (navigator.onLine) await sessione.carica()
  // An account waiting for approval has nothing else to see.
  if (!sessione.profilo?.persona && sessione.profilo?.mie_iscrizioni) {
    await router.replace('/mia-iscrizione')
    return
  }
  const p = sessione.profilo
  if (p) await navigazione.caricaContatori(p.capogruppo || p.amministratore_tecnico)
})
</script>

<template>
  <section v-if="sessione.profilo">
    <h1 class="h4 mb-5">Ciao {{ sessione.profilo.persona?.nome ?? sessione.profilo.email }}</h1>
    <div v-if="sessione.profilo.capo_in_attesa" class="alert theme-info small" role="status">
      <div>
        Sei iscritto dall'app e non ancora in BuonaStrada: fino ad allora non vedi i contatti, i
        dati sanitari e gli altri dati delicati dei soci.
      </div>
    </div>
    <section v-for="g in gruppi" :key="g.chiave" class="mb-7">
      <!-- A group with one entry of the same name (Bacheca) needs no heading. -->
      <h2
        v-if="!(g.voci.length === 1 && g.voci[0]!.nome === g.titolo)"
        class="h5 d-flex align-items-center gap-3"
      >
        <Icona :nome="g.icona" />
        {{ g.titolo }}
      </h2>
      <div class="row g-5">
        <div v-for="v in g.voci" :key="`${v.nome}-${JSON.stringify(v.to)}`" class="col-12 md:col-6">
          <a
            v-if="v.esterna"
            :href="String(v.to)"
            target="_blank"
            rel="noopener"
            class="card card-body h-100 text-decoration-none"
          >
            <strong class="d-flex align-items-center gap-3">
              <Icona :nome="v.icona" />
              {{ v.nome }}
            </strong>
            <span v-if="v.descrizione" class="fg-2 small">{{ v.descrizione }}</span>
          </a>
          <RouterLink v-else :to="v.to" class="card card-body h-100 text-decoration-none">
            <strong class="d-flex align-items-center gap-3">
              <Icona :nome="v.icona" />
              {{ v.nome }}
              <span v-if="v.contatore" class="badge theme-warning">{{ v.contatore }}</span>
            </strong>
            <span v-if="v.descrizione" class="fg-2 small">{{ v.descrizione }}</span>
          </RouterLink>
        </div>
      </div>
    </section>
  </section>
</template>
