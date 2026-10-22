/**
 * Who is using the app, and what they may see (from /api/v1/io).
 *
 * The profile is cached (encrypted) on the device so the app opens at camp without
 * network. Visibility rules live ONLY in the backend (apps/permessi/policy.py): the
 * flags here just hide menu items, they never protect data.
 */
import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

import { allauth } from '@/api/allauth'
import { api, type Profilo } from '@/api/qdc'
import { leggiConCache } from '@/offline/cache'
import * as cassaforte from '@/sicurezza/cassaforte'

export const useSessioneStore = defineStore('sessione', () => {
  const profilo = ref<Profilo | null>(null)
  const pronta = ref(false)
  /** Set when the profile comes from the device copy (offline start). */
  const profiloDel = ref<string | null>(null)

  const autenticato = computed(() => profilo.value !== null)
  const capo = computed(() => profilo.value?.capo ?? false)
  const capogruppo = computed(() => profilo.value?.capogruppo ?? false)
  const puoImportare = computed(
    () => !!profilo.value && (profilo.value.capogruppo || profilo.value.amministratore_tecnico),
  )

  async function carica() {
    try {
      let sessione = null
      try {
        sessione = await allauth.sessione()
      } catch {
        sessione = null // offline: fall back to the cached profile below
      }
      if (sessione && !sessione.meta?.is_authenticated) {
        profilo.value = null
        return
      }
      const letto = await leggiConCache('profilo', api.profilo)
      // Another account on this device: the previous one's data must go (DEC-97).
      const proprietario = cassaforte.proprietario()
      if (proprietario && proprietario !== letto.dati.email) {
        await cassaforte.cancella('altro_account')
      }
      profilo.value = letto.dati
      profiloDel.value = letto.copiaDel
    } catch {
      profilo.value = null
    } finally {
      pronta.value = true
    }
  }

  function dimentica() {
    profilo.value = null
    profiloDel.value = null
    pronta.value = false
  }

  async function esci() {
    try {
      await allauth.esci()
    } finally {
      dimentica()
      await cassaforte.cancella('uscita')
    }
  }

  // Branch colours (DEC-72): <html data-branca="eg"> switches the CSS variables.
  watch(
    () => profilo.value?.branca ?? 'generico',
    (branca) => {
      document.documentElement.dataset.branca = branca
    },
    { immediate: true },
  )

  return {
    profilo,
    pronta,
    profiloDel,
    autenticato,
    capo,
    capogruppo,
    puoImportare,
    carica,
    dimentica,
    esci,
  }
})
