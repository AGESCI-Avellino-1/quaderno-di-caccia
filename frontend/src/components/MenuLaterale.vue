<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import Icona from '@/components/Icona.vue'
import { useRete } from '@/composables/useRete'
import { gruppiMenu, vociProfilo, type Gruppo, type Voce } from '@/navigazione/menu'
import { blocca, stato } from '@/sicurezza/cassaforte'
import { useNavigazioneStore } from '@/stores/navigazione'
import { useSessioneStore } from '@/stores/sessione'

// The side menu (DEC-241) with the markup of django-agesci-campania-theme's sidebar
// (_sidebar.scss): in the page from lg up, a drawer opened from the header below.
// Bootstrap's JavaScript is not loaded: the drawer is a <dialog> opened here, and the
// profile menu opens in place above the avatar instead of floating.
const sessione = useSessioneStore()
const navigazione = useNavigazioneStore()
const rotta = useRoute()
const router = useRouter()
const { inCoda, conErrori } = useRete()

const cassetto = ref<HTMLDialogElement | null>(null)
// An accordion (DEC-241): every group starts closed and one opens at a time; the group
// of the page shown opens by itself. In memory only (no device storage for app state).
const gruppoAperto = ref<string | null>(null)
const ridotto = ref(false)
const profiloAperto = ref(false)

const gruppi = computed<Gruppo[]>(() =>
  sessione.profilo ? gruppiMenu(sessione.profilo, navigazione.contatori) : [],
)
const profilo = computed<Voce[]>(() => (sessione.profilo ? vociProfilo(sessione.profilo) : []))
const inImpersonazione = computed(() => !!sessione.profilo?.impersonazione)

/** A group with one entry of the same name (Bacheca, a child's own path) is one link. */
const singola = (g: Gruppo) => g.voci.length === 1 && g.voci[0]!.nome === g.titolo

const nome = computed(() => {
  const p = sessione.profilo
  if (!p) return ''
  return p.persona ? `${p.persona.nome} ${p.persona.cognome}` : p.email
})
const iniziali = computed(() => {
  const p = sessione.profilo?.persona
  if (p) return `${p.nome[0] ?? ''}${p.cognome[0] ?? ''}`.toUpperCase()
  return (sessione.profilo?.email[0] ?? '?').toUpperCase()
})

function apri() {
  cassetto.value?.showModal()
}

function chiudi() {
  if (cassetto.value?.open) cassetto.value.close()
}

// Tapping the dimmed page around the drawer closes it.
function suClic(evento: MouseEvent) {
  if (evento.target === cassetto.value) chiudi()
}

const percorsoDi = (v: Voce) => (v.esterna ? null : router.resolve(v.to).path)

/** The group holding the page shown, or a page under one of its entries. */
function gruppoDellaPagina(): string | null {
  let migliore: { chiave: string; lunghezza: number } | null = null
  for (const g of gruppi.value) {
    if (singola(g)) continue
    for (const v of g.voci) {
      const p = percorsoDi(v)
      if (!p || p === '/') continue
      const dentro = rotta.path === p || rotta.path.startsWith(`${p}/`)
      if (dentro && (!migliore || p.length > migliore.lunghezza)) {
        migliore = { chiave: g.chiave, lunghezza: p.length }
      }
    }
  }
  return migliore?.chiave ?? null
}

function alterna(chiave: string) {
  gruppoAperto.value = gruppoAperto.value === chiave ? null : chiave
}

const aperto = (g: Gruppo) => gruppoAperto.value === g.chiave

/** Counters of a closed group, shown on its title. */
const contatoreDi = (g: Gruppo) => g.voci.reduce((somma, v) => somma + (v.contatore ?? 0), 0)

watch(
  () => rotta.fullPath,
  () => {
    chiudi()
    profiloAperto.value = false
    const g = gruppoDellaPagina()
    if (g) gruppoAperto.value = g
  },
  { immediate: true },
)

function bloccaOra() {
  blocca()
  void router.push({ name: 'sblocco' })
}

async function esci() {
  await sessione.esci()
  await router.push({ name: 'accesso' })
}

defineExpose({ apri })
</script>

<template>
  <dialog
    ref="cassetto"
    class="ag-sidebar ag-sidebar--dark lg:drawer drawer-start"
    :class="{ 'ag-sidebar--collapsed': ridotto }"
    aria-label="Menu laterale"
    @click="suClic"
  >
    <button
      type="button"
      class="ag-sidebar__toggle d-none lg:d-flex"
      :aria-expanded="!ridotto"
      :aria-label="ridotto ? 'Allarga il menu' : 'Riduci il menu alle icone'"
      @click="ridotto = !ridotto"
    >
      <Icona nome="layout-sidebar-inset" />
      <span class="ag-sidebar__toggle-label ms-3">Menu</span>
    </button>
    <button
      type="button"
      class="ag-sidebar__close lg:d-none"
      aria-label="Chiudi il menu"
      @click="chiudi"
    >
      <Icona nome="x-lg" />
    </button>

    <ul class="ag-sidebar__nav">
      <li>
        <RouterLink
          to="/"
          class="ag-sidebar__nav-link"
          :class="{ active: rotta.name === 'home' }"
          title="Home"
        >
          <Icona nome="tenda" /><span class="ag-sidebar__label">Home</span>
        </RouterLink>
      </li>
      <template v-for="g in gruppi" :key="g.chiave">
        <li v-if="!singola(g)">
          <button
            type="button"
            class="ag-sidebar__nav-link qdc-voce-pulsante"
            :class="{ 'qdc-gruppo-aperto': aperto(g) }"
            :aria-expanded="aperto(g)"
            :title="g.titolo"
            @click="alterna(g.chiave)"
          >
            <Icona :nome="g.icona" />
            <span class="ag-sidebar__label">{{ g.titolo }}</span>
            <span v-if="!aperto(g) && contatoreDi(g)" class="badge theme-warning ms-auto">{{
              contatoreDi(g)
            }}</span>
            <Icona
              :nome="aperto(g) ? 'chevron-up' : 'chevron-down'"
              class="ag-sidebar__label qdc-freccia"
              :class="{ 'ms-auto': aperto(g) || !contatoreDi(g) }"
            />
          </button>
        </li>
        <li
          v-for="v in aperto(g) || singola(g) ? g.voci : []"
          :key="`${g.chiave}-${v.nome}-${JSON.stringify(v.to)}`"
        >
          <a
            v-if="v.esterna"
            :href="String(v.to)"
            class="ag-sidebar__nav-link qdc-nel-gruppo"
            :title="v.nome"
            target="_blank"
            rel="noopener"
          >
            <Icona :nome="v.icona" /><span class="ag-sidebar__label">{{ v.nome }}</span>
          </a>
          <RouterLink
            v-else
            :to="v.to"
            class="ag-sidebar__nav-link"
            :class="{ 'qdc-nel-gruppo': !singola(g), 'qdc-sottovoce': v.sottovoce }"
            active-class=""
            exact-active-class="active"
            :title="v.nome"
          >
            <Icona :nome="v.icona" />
            <span class="ag-sidebar__label">{{ v.nome }}</span>
            <span v-if="v.contatore" class="badge theme-warning ms-auto">{{ v.contatore }}</span>
          </RouterLink>
        </li>
      </template>
    </ul>

    <div v-if="sessione.profilo" class="ag-sidebar__user">
      <ul v-if="profiloAperto" id="menu-profilo" class="ag-sidebar__nav qdc-menu-profilo">
        <li v-for="v in profilo" :key="v.nome">
          <RouterLink :to="v.to" class="ag-sidebar__nav-link" :title="v.nome">
            <Icona :nome="v.icona" /><span class="ag-sidebar__label">{{ v.nome }}</span>
          </RouterLink>
        </li>
        <li v-if="inCoda || conErrori">
          <RouterLink to="/modifiche" class="ag-sidebar__nav-link" title="Modifiche da inviare">
            <Icona nome="cloud-upload" />
            <span class="ag-sidebar__label">Modifiche da inviare</span>
            <span class="badge theme-warning ms-auto">{{ inCoda + conErrori }}</span>
          </RouterLink>
        </li>
        <li v-if="stato === 'sbloccata' && !inImpersonazione">
          <button
            type="button"
            class="ag-sidebar__nav-link qdc-voce-pulsante"
            title="Blocca l'app: per riaprirla servirà il PIN"
            @click="bloccaOra"
          >
            <Icona nome="lock" /><span class="ag-sidebar__label">Blocca l'app</span>
          </button>
        </li>
        <!-- Logging out while acting as someone else would wipe the capo's device. -->
        <li v-if="!inImpersonazione">
          <button type="button" class="ag-sidebar__nav-link qdc-voce-pulsante" @click="esci">
            <Icona nome="box-arrow-right" /><span class="ag-sidebar__label">Esci</span>
          </button>
        </li>
      </ul>
      <button
        type="button"
        class="ag-sidebar__user-toggle qdc-voce-pulsante"
        :aria-expanded="profiloAperto"
        aria-controls="menu-profilo"
        :title="nome"
        @click="profiloAperto = !profiloAperto"
      >
        <span class="ag-sidebar__user-avatar" aria-hidden="true">{{ iniziali }}</span>
        <span class="ag-sidebar__label text-truncate">{{ nome }}</span>
        <Icona :nome="profiloAperto ? 'chevron-down' : 'chevron-up'" class="ms-auto" />
      </button>
    </div>
  </dialog>
</template>
