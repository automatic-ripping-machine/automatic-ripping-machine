<template>
  <tr>
    <td style="text-align:left"><strong>HB_PRESET_DVD</strong></td>
    <td style="text-align:left"> {{ jobs.config.HB_PRESET_DVD }}</td>
  </tr>
  <tr>
    <td style="text-align:left"><strong>HB_ARGS_DVD</strong></td>
    <td style="text-align:left"> {{ jobs.config.HB_ARGS_DVD }}</td>
  </tr>
  <tr>
    <td style="text-align:left"><strong>HB_PRESET_BD</strong></td>
    <td style="text-align:left">{{ jobs.config.HB_PRESET_BD }}</td>
  </tr>
  <tr>
    <td style="text-align:left"><strong>HB_ARGS_BD</strong></td>
    <td style="text-align:left">{{ jobs.config.HB_ARGS_BD }}</td>
  </tr>
</template>
<script>
export default {
  name: 'NotMusic',
  props: {
    jobs: {}
  }
}
</script>