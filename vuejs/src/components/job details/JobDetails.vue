<script>
import NoPoster from "@/components/job details/NoPoster.vue";
import axios from "axios";
import Poster from "@/components/job details/Poster.vue";
import NotMusic from "@/components/job details/NotMusic.vue";
import TrackList from "@/components/job details/TrackList.vue";
import {ref} from "vue";
export default {
  components: {TrackList, NotMusic, Poster, NoPoster},
  props: ['job_id'],

  data() {
    return {
      jobs: [],
      jsoncomments:[],
      tracks: [],
      config: [],
      jobs_background: ref(""),
      showPlot: ref(false),
      arm_API: this.armapi
    };
  },

  methods: {
    async getData(jobid) {
      try {
        let jobUrl = this.arm_API + "/jobs/"+ jobid
        const response = await axios.get(jobUrl);
        // JSON responses are automatically parsed.
        this.jobs = response.data;
        console.log(response.data)
        //this.jsoncomments = response.data.comments
        this.tracks = response.data.tracks
        console.log(this.tracks)
        this.config = response.data.config
        this.jobs_background = response.data.background
      } catch (error) {
        console.log(error);
      }
    },
  },

  created() {
    this.getData(this.$route.params.job_id);
  },
};
</script>

<template>
  <link rel="stylesheet" href="/src/assets/css/job-details.css">
  <div class="container">
    <div class="row">
      <div class="col-sm-12">
        <div class="table-responsive">
          <div class="card text-center">
            <!-- GF Comment -->
            <div class="card-header text-center">
              <h4>{{ jobs.title }} - {{ jobs.video_type }} ({{ jobs.year }})</h4>
              <div class="ratings float-right mt-0">
                <!-- Proof that just because you CAN doesnt mean you should! -->
              </div>
            </div>
            <!-- poster found -->
            <div v-if="jobs.poster_url" class="card-header background-poster">
                <img v-bind:src="jobs.poster_url" class="img-thumbnail" :class="{ 'float-left': jobs.background }"
                     alt="Poster image">
              <div v-if="jobs.video_type !== Music" class="btn-group float-right mt-2" role="group">
                <router-link :to="'/titlesearch/' + jobs.job_id" class="btn btn-primary">Title
                  Search</router-link>
                  <router-link :to="'/customTitle/' + jobs.job_id" class="btn btn-primary">Custom
                    Title</router-link>
                <a id="plot" class="btn btn-primary" @click="showPlot = !showPlot"> Plot </a>
              </div>
            </div>
            <!-- No poster found -->
            <div v-else class="card-header background-poster">
              <a v-if="jobs.video_type === Music" id="posterClick" href="#">
                <img src="/src/assets/img/music.png" alt="Not found" width="800" class="img-thumbnail"></a>
              <a v-else id="posterClick" href="#">
                <img src="/src/assets/img/none.png" alt="Not found" width="512" class="img-thumbnail"></a>
              <div v-if="jobs.video_type !== Music" class="btn-group float-right mt-2" role="group">
                <router-link :to="'/titlesearch/' + jobs.job_id" class="btn btn-primary">Title
                  Search</router-link>
                <router-link :to="'/customTitle/'+ jobs.job_id" class="btn btn-primary">Custom
                  Title</router-link>
                <a class="btn btn-primary" @click="showPlot = !showPlot">Plot</a>
              </div>
            </div>
            <Transition>
            <div id="plotInfo" class="alert alert-info text-center" v-show="showPlot" role="alert">
              <h4 class="alert-heading">Plot for {{ jobs.title }}</h4>
              <hr>
              <p class="mb-0">{{ jobs.plot }}</p>
            </div>
            </Transition>
            <div class="card-body">
              <table id="jobtable" class="table table-striped" aria-label="Job details">
                <thead class="bg-secondary">
                <tr>
                  <th class="rounded-top" scope="col" style="text-align:left">Field</th>
                  <th scope="col" style="text-align:left">Value</th>
                </tr>
                </thead>
                <tbody>
                <tr>
                  <td style="text-align:left"><strong>job_id</strong></td>
                  <td style="text-align:left">{{ jobs.job_id }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>arm_version</strong></td>
                  <td style="text-align:left">{{ jobs.arm_version }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>crc_id</strong></td>
                  <td style="text-align:left">{{ jobs.crc_id }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>logfile</strong></td>
                  <td style="text-align:left">
                    <router-link :to="'/logs/'+ jobs.logfile + '/full/' +  jobs.job_id">{{ jobs.logfile }}</router-link>
                  </td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>disc</strong></td>
                  <td style="text-align:left">{{ jobs.disc }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>start_time</strong></td>
                  <td style="text-align:left">{{ jobs.start_time }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>stop_time</strong></td>
                  <td style="text-align:left">{{ jobs.stop_time }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>job_length</strong></td>
                  <td style="text-align:left">{{ jobs.job_length }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>status</strong></td>
                  <td style="text-align:left">{{ jobs.status }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>video_type</strong></td>
                  <td style="text-align:left">{{ jobs.video_type }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>video_type_auto</strong></td>
                  <td style="text-align:left">{{ jobs.video_type_auto }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>video_type_manual</strong></td>
                  <td style="text-align:left">{{ jobs.video_type_manual }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>title</strong></td>
                  <td style="text-align:left">{{ jobs.title }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>title_auto</strong></td>
                  <td style="text-align:left">{{ jobs.title_auto }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>title_manual</strong></td>
                  <td style="text-align:left">{{ jobs.title_manual }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>year</strong></td>
                  <td style="text-align:left">{{ jobs.year }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>year_auto</strong></td>
                  <td style="text-align:left">{{ jobs.year_auto }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>year_manual</strong></td>
                  <td style="text-align:left">{{ jobs.year_manual }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>imdb_id</strong></td>
                  <td style="text-align:left">{{ jobs.imdb_id }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>imdb_id_auto</strong></td>
                  <td style="text-align:left">{{ jobs.imdb_id_auto }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>imdb_id_manual</strong></td>
                  <td style="text-align:left">{{ jobs.imdb_id_manual }}</td>
                </tr>
                <Poster v-if="jobs.poster_url" :jobs="jobs"/>
                <NoPoster v-else :jobs="jobs"/>
                <tr>
                  <td style="text-align:left"><strong>devpath</strong></td>
                  <td style="text-align:left">{{ jobs.devpath }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>mountpoint</strong></td>
                  <td style="text-align:left">{{ jobs.mountpoint }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>hasnicetitle</strong></td>
                  <td style="text-align:left">{{ jobs.hasnicetitle }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>errors</strong></td>
                  <td style="text-align:left">{{ jobs.errors }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>disctype</strong></td>
                  <td style="text-align:left">{{ jobs.disctype }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>label</strong></td>
                  <td style="text-align:left">{{ jobs.label }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>ejected</strong></td>
                  <td style="text-align:left">{{ jobs.ejected }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>pid</strong></td>
                  <td style="text-align:left">{{ jobs.pid }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>pid hash</strong></td>
                  <td style="text-align:left">{{ jobs.pid_hash }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>path</strong></td>
                  <td style="text-align:left">{{ jobs.path }}</td>
                </tr>
                <tr>
                  <td style="text-align:left"><strong>Config ID</strong></td>
                  <td style="text-align:left"> {{ config.CONFIG_ID }}</td>
                </tr>
                <!--<NotMusic :jobs="jobs"/>-->
                </tbody>
              </table>
              <hr class="test d-none">
             <TrackList :tracks="tracks"/>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
div.card div.background-poster {
  background-position: center;
  background-repeat: no-repeat;
  background-size: cover;
  background-size: 100% 100%;
  /* Must come pre-wrapped with url */
  background-image: v-bind(jobs_background);
}
img.img-thumbnail{
  min-height: 300px;
  min-width: 200px;
}
td a img{
  min-height: 150px;
  min-width: 100px;
}

div.metacritic {
  background-position: center;
  background-repeat: no-repeat;
  background-size: cover;
  /*
  background-size: 100% 100%;
  */
  background-color: #fc3;
  border-radius: 50% !important;
}

div.internet-movie-database {
  background: url("https://m.media-amazon.com/images/S/sash/7n0KRCHny73GkBG.png") no-repeat 0 -80px;
  padding-left: 20px;
  font-weight: bolder;
}

div.rotten-tomatoes {
  padding-left: 23px;
  font-weight: bolder;
  background-size: 33% 100%;
  background: url("https://www.rottentomatoes.com/assets/pizza-pie/images/icons/tomatometer/tomatometer-fresh.149b5e8adc3.svg") no-repeat left;
}

div.rotten-tomatoes-rotten {
  padding-left: 23px;
  font-weight: bolder;
  background-size: 33% 100%;
  background: url("https://www.rottentomatoes.com/assets/pizza-pie/images/icons/tomatometer/tomatometer-rotten.f1ef4f02ce3.svg") no-repeat left;

}

div.ratings {
  margin-top: -50px !important;
}
/* we will explain what these classes do next! */
.v-enter-active,
.v-leave-active {
  transition: opacity .5s ease;
}

.v-enter-from,
.v-leave-to {
  opacity: 0;
}
.force-wrap{
  word-wrap: break-word;
  min-width: 160px;
  max-width: 160px;
}
</style>