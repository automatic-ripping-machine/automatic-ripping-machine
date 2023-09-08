<template style="position: relative;">
  <h1 class="ribbon" style="display: inline;">{{ titleManual }}</h1>
  <div v-show="showing">
    <div class="card_left d-flex align-items-center justify-content-center">
      <div class="card_datails">
        <div><router-link style="float: right" class="btn btn-primary" :to="'/job-details/'+ job.job_id">Full details</router-link>
        </div>

        <div class="card_cat">
          <p class="PG">{{ job.disctype }}</p>
          <p class="PG">{{ job.year }}</p>
          <p class="PG">{{ job.devpath }}</p>
          <p class="PG"><img width="22px" height="22px" id="jobId67_status"
                             v-bind:src="'/src/assets/img/' + job.status + '.png'" alt="transcoding"
                             title="transcoding">
          </p>
        </div>
        <div class="disc">{{ job.plot }}
          <TranscodingStatus :job="job"/>
          <JobCardConfig :job="job" :ripper-name="getRipperName(job)"/>
        </div>
        <JobCardButtons :job="job" @abandon="$emit('abandon', job);" @fixPerms="$emit('fixPerms', job);"/>
      </div>
    </div>
  </div>
  <!-- Poster -->
  <div class="card_right">
    <div class="img_container" style="border-radius: 0% 8% 8% 0%;">
      <img v-bind:src="job.poster_url" alt="" style="border-radius: 0 8% 8% 0;">
    </div>
    <div class="play_btn" style="border-radius: 0% 8% 8% 0%;">
      <a class="click_details"
         title="Click for more details...." @click.prevent="showing = ! showing">
      </a>
    </div>
  </div>
</template>
<script>

import JobCardButtons from "@/components/jobcards/JobCardButtons.vue";
import TranscodingStatus from "@/components/jobcards/TranscodingStatus.vue";
import JobCardConfig from "@/components/jobcards/JobCardConfig.vue";

export default {
  name: 'JobCardLeft',
  components: {JobCardConfig, TranscodingStatus, JobCardButtons},
  props: {
    job: {},
    showJobID: "",
    titleManual: ""
  },
  data() {
    return {
      showing: false
    };
  },
  computed: {
    showCard() {
      console.log(this.showing)
      this.showing = !this.showing
      console.log(this.showing)
      return this.showing
    }
  },
  methods: {
    getRipperName: function (job) {
      console.log(job.job_id);
      // TODO Fix this as the split is not working correctly when in docker
      let idsplit = JSON.stringify(job.job_id).split("_");
      console.log(idsplit)
      console.log(job.ripper)
      console.log(idsplit[0])
      let ripperName;
      if (job.ripper) {
        ripperName = job.ripper;
      } else {
        if (idsplit[1] === "0") {
          ripperName = "Local";
        } else {
          ripperName = "";
        }
      }
      return ripperName;
    }

  }
}
</script>
<style>
.play_btn {
  min-width: 263px;
}

.img_container {
  min-width: 261px;
  min-height: 200px;
}

.card_left {
  margin-top: inherit;
}

.card_datails {
  padding: 15px;
  margin-top: -8px;
  position: relative;
  height: 100%;
}

.card_datails h1 {
  font-size: 30px;
}

.card_right img {
  height: 390px;
  border-radius: 2px;
  width: auto;
}

.card_cat {
  margin-top: 45px;
  width: 100%;
  display: -webkit-box;
  display: -ms-flexbox;
  display: flex;
  -webkit-box-pack: justify;
  -ms-flex-pack: justify;
  justify-content: space-between;
}

.PG {
  color: #fff;
  background-color: #373737;
  display: inline-block;
  font-size: 122%;
  font-weight: 700;
  line-height: 2;
  text-align: center;
  white-space: nowrap;
  vertical-align: baseline;
  border-radius: .25rem;
  transition: color .15s ease-in-out, background-color .15s ease-in-out, border-color .15s ease-in-out, box-shadow .15s ease-in-out;
  padding: 7px;
  box-shadow: 2px 2px 5px rgb(0, 0, 0) inset;
}

.disc {
  font-weight: 100;
  height: 78%;
}

a {
  color: #1b6dc9;
  display: block;
  text-decoration: none;
}

.social-btn {
  margin-left: 30px;
  position: absolute;
  bottom: -235px;
  left: 10px;
  height: 100%;
}

.btn {
  font-size: 0.6rem;
}

@-webkit-keyframes bounce {
  8% {
    transform: scale(0.3);
    -webkit-transform: scale(0.8);
    opacity: 1;
  }
  10% {
    transform: scale(1.8);
    -webkit-transform: scale2);
    opacity: 0;
  }
}

@keyframes bounce {
  8% {
    transform: scale(0.3);
    -webkit-transform: scale(0.8);
    opacity: 1;
  }
  20% {
    transform: scale(1.8);
    -webkit-transform: scale2);
    opacity: 0;
  }
}

@-webkit-keyframes rotation {
  from {
    -webkit-transform: rotate(0deg);
  }
  to {
    -webkit-transform: rotate(359deg);
  }
}

h1, h2 {
  font-family: 'Crete Round', serif;
}

a {
  color: #12158d;
  text-decoration: none;
}

.click_details:hover {
  cursor: pointer;
}

.ribbon {
  position: absolute;
  padding: 0 3em;
  font-size: 1.4em;
  margin: 0 0 0 0;
  line-height: 1.875em;
  color: #e6e2c8;
  min-width: 264px;
  border-radius: 0 1.2em 0.156em 0;
  background: rgb(27, 110, 202);
  box-shadow: -1px 2px 3px rgba(0, 0, 0, 0.5);
}

.ribbon:before, .ribbon:after {
  position: absolute;
  content: '';
  display: block;
}

.ribbon:before {
  width: 0.5em;
  height: 100%;
  padding: 0 0 0.438em;
  top: 0;
  left: -0.5em;
  background: inherit;
  border-radius: 0.313em 0 0 0.313em;
}

.ribbon:after {
  width: 0.313em;
  height: 0.313em;
  background: rgba(0, 0, 0, 0.35);
  bottom: -0.313em;
  left: -0.313em;
  border-radius: 0.313em 0 0 0.313em;
  box-shadow: inset -1px 2px 2px rgba(0, 0, 0, 0.3);
}

.btn-primary:not(.disabled):hover{
  background-image: linear-gradient(#516e8e, #13549b 50%, #0b2644);
  box-shadow: 1px 2px 5px #bdb3ba;
}
</style>