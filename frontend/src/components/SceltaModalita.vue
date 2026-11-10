<script setup lang="ts">
import type { ModalitaRiunione } from '@/api/qdc'

// In person, online or mixed, with the platform's link (DEC-402): Co.Ca., staff and
// parents' meetings only; the server checks it again.
const modello = defineModel<{ modalita: ModalitaRiunione; link: string }>({ required: true })
defineProps<{ idCampo: string }>()
const MODI: { valore: ModalitaRiunione; nome: string }[] = [
  { valore: 'PRESENZA', nome: 'In presenza' },
  { valore: 'ONLINE', nome: 'Online' },
  { valore: 'MISTA', nome: 'Mista (in presenza e online)' },
]
</script>

<template>
  <div class="row g-3">
    <div class="md:col-4">
      <label class="form-label small" :for="`${idCampo}-modo`">Come</label>
      <select
        :id="`${idCampo}-modo`"
        v-model="modello.modalita"
        class="form-control form-control-sm"
      >
        <option v-for="m in MODI" :key="m.valore" :value="m.valore">{{ m.nome }}</option>
      </select>
    </div>
    <div v-if="modello.modalita !== 'PRESENZA'" class="md:col-8">
      <label class="form-label small" :for="`${idCampo}-link`">Link della riunione</label>
      <input
        :id="`${idCampo}-link`"
        v-model.trim="modello.link"
        type="url"
        class="form-control form-control-sm"
        placeholder="https://meet.google.com/…"
        pattern="https://.*"
        required
      />
      <p class="form-text mb-0">Il link di Meet o di un'altra piattaforma.</p>
    </div>
  </div>
</template>
