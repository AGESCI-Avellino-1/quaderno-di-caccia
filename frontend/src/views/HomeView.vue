<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import Icona from '@/components/Icona.vue'
import VociHome from '@/components/VociHome.vue'
import {
  leggiGruppoAperto,
  salvaGruppoAperto,
  SEMPRE_APERTI,
  totaleContatori,
} from '@/navigazione/gruppoAperto'
import { gruppiMenu, vociProfilo, type Gruppo } from '@/navigazione/menu'
import { useNavigazioneStore } from '@/stores/navigazione'
import { useSessioneStore } from '@/stores/sessione'

// The Home shows the menu's groups as cards (DEC-241): a group with nothing the user
// may use is not there at all. Groups open and close from their title, one at a time,
// and the one open last opens again (DEC-285); the Bacheca is always shown.
const sessione = useSessioneStore()
const navigazione = useNavigazioneStore()
const router = useRouter()

const gruppi = computed<Gruppo[]>(() => {
  const p = sessione.profilo
  if (!p) return []
  const profilo = vociProfilo(p)
  // The Calendario is in the menu under Eventi, on the Home next to the Bacheca (DEC-286).
  const tutti = gruppiMenu(p, navigazione.contatori)
  const calendario = tutti.flatMap((g) => g.voci).find((v) => v.to === '/calendario')
  const menu = tutti.map((g) => {
    if (g.chiave === 'bacheca' && calendario) {
      return { ...g, voci: [...g.voci, { ...calendario, sottovoce: false }] }
    }
    return { ...g, voci: g.voci.filter((v) => v !== calendario) }
  })
  return [
    ...menu.filter((g) => g.voci.length),
    ...(profilo.length
      ? [{ chiave: 'profilo', titolo: 'Profilo', icona: 'person-circle' as const, voci: profilo }]
      : []),
  ]
})

// The Bacheca stays open on top (DEC-285); the others are the accordion.
const sempreAperti = computed(() => gruppi.value.filter((g) => SEMPRE_APERTI.has(g.chiave)))
const apribili = computed(() => gruppi.value.filter((g) => !SEMPRE_APERTI.has(g.chiave)))

const aperto = ref(leggiGruppoAperto())

// <details name="…"> closes the others by itself; this keeps the choice for next time.
function suToggle(chiave: string, evento: Event) {
  const aprendo = (evento.target as HTMLDetailsElement).open
  if (aprendo) aperto.value = chiave
  else if (aperto.value === chiave) aperto.value = null
  salvaGruppoAperto(aperto.value)
}

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
    <section v-for="g in sempreAperti" :key="g.chiave" class="mb-7">
      <!-- Bacheca and Calendario need no heading. -->
      <VociHome :voci="g.voci" />
    </section>
    <!-- Bootstrap 6 accordion (DEC-298) on <details name>: one group open at a time. -->
    <div v-if="apribili.length" class="accordion accordion-gap theme-primary">
      <details
        v-for="g in apribili"
        :key="g.chiave"
        name="gruppi-home"
        class="accordion-item"
        :open="aperto === g.chiave"
        @toggle="suToggle(g.chiave, $event)"
      >
        <summary class="accordion-header h5 mb-0 gap-3">
          <Icona :nome="g.icona" />
          {{ g.titolo }}
          <span
            v-if="aperto !== g.chiave && totaleContatori(g)"
            class="badge theme-warning"
            :aria-label="`${totaleContatori(g)} da fare`"
            >{{ totaleContatori(g) }}</span
          >
          <Icona nome="chevron-down" class="accordion-icon" />
        </summary>
        <div class="accordion-body">
          <VociHome :voci="g.voci" />
        </div>
      </details>
    </div>
  </section>
</template>
