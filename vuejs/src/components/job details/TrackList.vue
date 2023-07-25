<template>
  <table id="tracktable" class="table table-striped" aria-label="Tracks">
    <thead class="bg-secondary">
    <tr>
      <th scope="col" style="text-align:left">Track #</th>
      <th scope="col" style="text-align:left">Track Name</th>
      <th scope="col" style="text-align:left">Length (sec)</th>
      <th scope="col" style="text-align:left">FPS</th>
      <th scope="col" style="text-align:left">Aspect Ratio</th>
      <th scope="col" style="text-align:left">Main Feature</th>
      <th scope="col" style="text-align:left">Ripped</th>
    </tr>
    </thead>
    <tbody>
    <tr v-for="track in tracks">
      <td style="text-align:left"><strong>{{ track.track_number }}</strong></td>
      <td style="text-align:left"><strong>{{ track.filename}}</strong></td>
      <td style="text-align:left">{{ track.length }}</td>
      <td style="text-align:left">{{ track.fps }}</td>
      <td style="text-align:left">{{ track.aspect_ratio }}</td>
      <td style="text-align:left">{{ track.main_feature }}</td>
      <td style="text-align:left">{{ track.ripped }}</td>
    </tr>
    </tbody>

  </table>
</template>
<script>
export default {
  name: 'TrackList',
  props: {
    jobs: {},
    tracks: {}
  }
}
</script>