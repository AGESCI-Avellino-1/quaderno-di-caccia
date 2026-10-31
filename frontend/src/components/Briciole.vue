<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute, useRouter, type RouteLocationRaw } from 'vue-router'

import Icona from '@/components/Icona.vue'
import { gruppiMenu, vociProfilo } from '@/navigazione/menu'
import { PAGINE } from '@/router/pagine'
import { useNavigazioneStore } from '@/stores/navigazione'
import { useSessioneStore } from '@/stores/sessione'

// The breadcrumb (DEC-244): Home (a tent), the menu group, the pages above this one
// (router/pagine.ts) with their own names when a view gave one, then this page.
const rotta = useRoute()
const router = useRouter()
const sessione = useSessioneStore()
const navigazione = useNavigazioneStore()

interface Briciola {
  nome: string
  percorso: string | null
}

const percorsoDi = (to: RouteLocationRaw) => {
  try {
    return router.resolve(to).path
  } catch {
    return null
  }
}

const briciole = computed<Briciola[]>(() => {
  const p = sessione.profilo
  if (!p || rotta.name === 'home' || !PAGINE[String(rotta.name)]) return []
  const gruppi = gruppiMenu(p, navigazione.contatori)
  const visibili = new Set(
    [...gruppi.flatMap((g) => g.voci), ...vociProfilo(p)].map((v) => percorsoDi(v.to)),
  )
  // From this page up, by `sopra`; the parameters (`id`) are the same along the chain.
  const catena: { nome: string; percorso: string }[] = []
  let nome: string | undefined = String(rotta.name)
  while (nome) {
    const pagina: (typeof PAGINE)[string] | undefined = PAGINE[nome]
    if (!pagina) break
    const percorso = percorsoDi({ name: nome, params: rotta.params })
    if (percorso === null) break
    catena.unshift({ nome: navigazione.nomi[percorso] ?? pagina.titolo, percorso })
    nome = pagina.sopra
  }
  // A list page above this one that the menu does not offer (a parent on a child's
  // page never sees "Persone") is left out.
  const mostrate = catena.filter(
    (b, i) =>
      i === catena.length - 1 ||
      visibili.has(b.percorso) ||
      PAGINE[String(router.resolve(b.percorso).name)]?.sopra !== undefined,
  )
  const gruppo = gruppi.find(
    (g) =>
      !(g.voci.length === 1 && g.voci[0]!.nome === g.titolo) &&
      g.voci.some((v) => mostrate.some((b) => b.percorso === percorsoDi(v.to))),
  )
  return [
    ...(gruppo ? [{ nome: gruppo.titolo, percorso: null }] : []),
    ...mostrate.map((b, i) => ({
      nome: b.nome,
      percorso: i === mostrate.length - 1 ? null : b.percorso,
    })),
  ]
})
</script>

<template>
  <nav v-if="briciole.length" aria-label="Percorso" class="container pt-3">
    <ol class="breadcrumb mb-0 small">
      <li class="breadcrumb-item">
        <RouterLink to="/" class="breadcrumb-link" title="Home">
          <Icona nome="tenda" /><span class="visually-hidden">Home</span>
        </RouterLink>
      </li>
      <template v-for="(b, i) in briciole" :key="i">
        <li class="breadcrumb-divider" aria-hidden="true"></li>
        <li class="breadcrumb-item">
          <RouterLink v-if="b.percorso" :to="b.percorso" class="breadcrumb-link">{{
            b.nome
          }}</RouterLink>
          <span
            v-else
            class="breadcrumb-link"
            :class="{ active: i === briciole.length - 1 }"
            :aria-current="i === briciole.length - 1 ? 'page' : undefined"
            >{{ b.nome }}</span
          >
        </li>
      </template>
    </ol>
  </nav>
</template>
