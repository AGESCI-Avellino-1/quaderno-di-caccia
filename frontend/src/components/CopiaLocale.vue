<script setup lang="ts">
// Tells the user they are looking at the copy saved on this device, and from when.
defineProps<{ del: string | null }>()
</script>

<template>
  <p v-if="del" class="small fg-2">
    Copia salvata sul dispositivo il {{ new Date(del).toLocaleString('it-IT') }}
  </p>
</template>
