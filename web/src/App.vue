<script setup>
import { timers } from '@/timers.js'
import Navigation from './components/Navigation.vue'

</script>
<template>
  <progress class="progress is-primary is-small" :value="timers.tick.elapsed"
    :max="timers.tick.duration"></progress>
  <div class="hero-body">
    <div class="container is-fullhd">
      <Navigation />
    </div>
  </div>
</template>

<style lang="scss">
// @charset "utf-8";

// $primary: #EF233C;
// $link: $primary;

// $family-primary: 'Fira Code', monospace;
// $body-background-color:  hsl(0, 0%, 96%);

// $radius: 0px;
// $progress-border-radius: 0px;
// $progress-bar-background-color: transparent;
// $progress-value-background-color: transparent;

// @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;500&display=swap');

// @import "../node_modules/bulma/sass/base/_all.sass";
// @import "../node_modules/bulma/sass/components/card.sass";
// @import "../node_modules/bulma/sass/elements/container.sass";
// @import "../node_modules/bulma/sass/elements/progress.sass";
// @import "../node_modules/bulma/sass/elements/title.sass";
// @import "../node_modules/bulma/sass/grid/_all.sass";
// @import "../node_modules/bulma/sass/helpers/_all.sass";
// @import "../node_modules/bulma/sass/layout/_all.sass";
// @import "../node_modules/bulma/sass/utilities/_all.sass";

// @import "../node_modules/@creativebulma/bulma-tooltip/dist/bulma-tooltip.min.css";
@import "../dist/assets/index-74c7fafb.css"
</style>
