<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute, useRouter, type RouteLocationRaw } from 'vue-router'

import Icona from '@/components/Icona.vue'
import { briciole as calcola, type Anello } from '@/navigazione/briciole'
import { gruppiMenu, vociProfilo } from '@/navigazione/menu'
import { PAGINE } from '@/router/pagine'
import { useNavigazioneStore } from '@/stores/navigazione'
import { useSessioneStore } from '@/stores/sessione'

// The breadcrumb (DEC-244): Home (a tent), then navigazione/briciole.ts; the pages keep
// the names their views gave them (usaPagina).
const rotta = useRoute()
const router = useRouter()
const sessione = useSessioneStore()
const navigazione = useNavigazioneStore()

const percorsoDi = (to: RouteLocationRaw) => {
  try {
    return router.resolve(to).path
  } catch {
    return null
  }
}

const briciole = computed(() => {
  const p = sessione.profilo
  if (!p || rotta.name === 'home' || !PAGINE[String(rotta.name)]) return []
  // From this page up, by `sopra`; the parameters (`id`) are the same along the chain.
  const catena: Anello[] = []
  let nome: string | undefined = String(rotta.name)
  while (nome) {
    const pagina: (typeof PAGINE)[string] | undefined = PAGINE[nome]
    if (!pagina) break
    const percorso = percorsoDi({ name: nome, params: rotta.params })
    if (percorso === null) break
    catena.unshift({ pagina: nome, percorso, nome: navigazione.nomi[percorso] ?? pagina.titolo })
    nome = pagina.sopra
  }
  return calcola(catena, gruppiMenu(p, navigazione.contatori), vociProfilo(p), p.capo, (v) =>
    percorsoDi(v.to),
  )
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
