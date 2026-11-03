<script setup lang="ts">
import Icona from '@/components/Icona.vue'

// One section that opens and closes, as a small Bootstrap 6 accordion (DEC-298).
defineProps<{ titolo: string; aperta?: boolean }>()
</script>

<template>
  <div class="accordion accordion-sm">
    <details class="accordion-item" :open="aperta">
      <summary class="accordion-header">
        {{ titolo }}
        <Icona nome="chevron-down" class="accordion-icon" />
      </summary>
      <div class="accordion-body">
        <slot />
      </div>
    </details>
  </div>
</template>
