<template>
  <tr>
    <td style="text-align:left"><strong>poster_url</strong></td>
    <td style="text-align:left" class="force-wrap"><a v-bind:href="jobs.poster_url" target="_blank"><img
        alt="Poster image"
        v-bind:src="jobs.poster_url" v-bind:title="jobs.poster_url"
        width=50></a><br/>{{ jobs.poster_url }}
    </td>
  </tr>
  <tr>
    <td style="text-align:left"><strong>poster_url_auto</strong></td>
    <td style="text-align:left" class="force-wrap"><a v-bind:href="jobs.poster_url_auto" target="_blank"><img
        alt="Poster image"
        v-bind:src="jobs.poster_url_auto" v-bind:title="jobs.poster_url_auto"
        width=50></a><br/>{{ jobs.poster_url_auto }}
    </td>
  </tr>
  <tr>
    <td style="text-align:left"><strong>poster_url_manual</strong></td>
    <td style="text-align:left" class="force-wrap"><a v-bind:href="jobs.poster_url_manual" target="_blank"><img
        alt="Poster image"
        v-bind:src="jobs.poster_url_manual" v-bind:title="jobs.poster_url_manual"
        width=50> </a><br/>{{ jobs.poster_url_manual }}
    </td>
  </tr>
</template>
<script>
export default {
  name: 'Poster',
  props: {
    jobs: {}
  }
}
</script>