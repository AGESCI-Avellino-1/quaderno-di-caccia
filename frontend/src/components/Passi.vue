<script
  setup
  lang="ts"
  generic="P extends { etichetta: string; fatto?: boolean; corrente?: boolean }"
>
// Steps in a row, Bootstrap 6 stepper as the theme's ag_stepper (DEC-298): the steps done
// are coloured with the line joining them, the current one is marked for screen readers.
// Horizontal (a few short steps) scrolls sideways on a narrow phone; vertical takes a slot
// for what to say about each step.
withDefaults(
  defineProps<{
    passi: P[]
    orizzontale?: boolean
  }>(),
  { orizzontale: false },
)
</script>

<template>
  <div :class="{ 'stepper-overflow': orizzontale }">
    <ol class="stepper mb-0" :class="{ 'stepper-horizontal': orizzontale }">
      <li
        v-for="(p, i) in passi"
        :key="i"
        class="stepper-item"
        :class="{ active: p.fatto }"
        :aria-current="p.corrente ? 'step' : undefined"
      >
        <div>
          <slot :passo="p">{{ p.etichetta }}</slot>
        </div>
      </li>
    </ol>
  </div>
</template>
