<template>
  <div v-for="item in results" class="col-sm col-md col-xl-4 col-lg-4 text-center p-2">
    <div class="card text-center h-100" :class="{ 'card-active' : job.imdb_id === item['imdbID']}">
      <div class="card-header">
        <a v-bind:href="item['Poster']" target="_blank">
          <img v-bind:src="item['Poster']" width="120px" class="img-thumbnail thumbnail zoom" alt="Poster image">
        </a>
        <div v-if="item['imdbID'] === job.imdb_id" title="Currently Matched" class="d-inline align-text-bottom float-right">
          <Match/>
        </div>
        <br>
        <strong>{{ item["Title"] }}</strong>
      </div>
      <div class="card-body">
        <strong>{{ item["Type"] }}
        ({{ item["Year"] }})</strong>
        <br>
        <strong>Plot: </strong>{{ item['details']['Plot'] }}
        <br>
      </div>
      <div class="card-footer">
        <a type="button" class="btn btn-primary btn-lg btn-block"
           v-on:click="updateJob(job, item)">Match Job</a>
      </div>
    </div>
  </div>
</template>
<script>
import {ref} from "vue";
import Match from "@/components/icons/Match.vue";
import axios from "axios";

export default {
  name: 'RemoteAPISearch',
  components: {Match},
  props: {
    job: {},
    results: ref({}),
    item: {},
  },
  data() {
    return {
      arm_API: this.armapi
    }
  },
  methods: {
    updateJob: function (job, item) {
      console.log(job)
      console.log(item)
      let getURL = 'title=' + item["Title"] + '&year=' + item["Year"] + '&imdbID=' + item["imdbID"] + '&type=' + item["Type"] + '&poster=' + item['Poster'] + '&job_id=' + job.job_id
      console.log(getURL)
      axios.get(this.arm_API +'/json?mode=update_title&' + getURL)
          .then(res => this.search(res))
    },
    search: function (response) {
        this.job.title = response.data.title
        this.job.year = response.data.year
        this.job.imdb_id = response.data.imdb_id
        this.currentLoading = false
    }
  }
}
</script>
<style>
.img-thumbnail{
  height: 150px;
  width: 100px;
}
ul.gallery{
  margin-left: 3vw;
  margin-right:3vw;
}
.card-active{
  border-color: rgb(13, 110, 253);
  box-shadow: 0px 0px 10px 2px rgb(13, 110, 253);
}
.zoom {
  -webkit-transition: all 0.35s ease-in-out;
  -moz-transition: all 0.35s ease-in-out;
  transition: all 0.35s ease-in-out;
  cursor: -webkit-zoom-in;
  cursor: -moz-zoom-in;
  cursor: zoom-in;
}

.zoom:hover,
.zoom:active,
.zoom:focus {
  /**adjust scale to desired size,
  add browser prefixes**/
  -ms-transform: scale(2.5);
  -moz-transform: scale(2.5);
  -webkit-transform: scale(2.5);
  -o-transform: scale(2.5);
  transform: scale(2.5);
  position:relative;
  z-index:100;
}

/**To keep upscaled images visible on mobile,
increase left & right margins a bit**/
@media only screen and (max-width: 768px) {
  ul.gallery {
    margin-left: 15vw;
    margin-right: 15vw;
  }

  /**TIP: Easy escape for touch screens,
  give gallery's parent container a cursor: pointer.**/
  .DivName {cursor: pointer}
}
</style>