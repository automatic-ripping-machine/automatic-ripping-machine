<script setup>
import JobCardLeft from "@/components/jobcards/Job Card Ideas/JobCardBlurayCase.vue";

defineEmits(['abandon', 'fixPerms'])
defineProps({
  joblist: {
    type: Object,
    required: true
  },
})

function titleManual(job) {
  console.log( "title man = "+job.title_manual)
  let x;
  if (job.title_manual !== "None" && job.title_manual !== null) {
    x = `${job.title_manual}(${job.year})`;
  } else {
    x = `${job.title}(${job.year})`;
  }
  return x;
}
</script>

<template>
    <!-- Start creating the card with job id and header title -->
    <div v-for="job in joblist" :key="job.id" v-bind:id="'job_id' + job.job_id " class="wrapper">
        <div class="main_card content">
          <JobCardLeft :job="job" :showJobID="job.job_id+'Show'"
                       :titleManual="titleManual(job)" @abandon="$emit('abandon', job);" @fixPerms="$emit('fixPerms', job);"/>
        </div>
      </div>
</template>

<style>
.wrapper{
  margin: 11px;
}
.click_details{
  border-radius: 0 8% 8% 0;
  float: inline-end;
  width: 100%;
  height: 100%;
}
.btn-primary{
  background-image: linear-gradient(#6d94bf, #1b6eca 50%, #113b6a);
}
.main_card {
  color: #fff;
  height: 390px;
  margin: 50px auto;
  display: -webkit-box;
  display: -ms-flexbox;
  display: flex;
  max-width: 770px;
  background: #3a3f48;
  background: -webkit-linear-gradient(to right, #1e519a, #26292d);
  background: -webkit-gradient(linear, left top, right top, from(#1e519a), to(#3a3f48));
  background: -webkit-linear-gradient(left, #1e519a, rgba(58, 63, 72, 0.98));
  background: -o-linear-gradient(left, #1e519a, rgba(58, 63, 72, 0.98));
  background: linear-gradient(to right, rgba(13, 13, 13, 0.69), rgba(58, 63, 72, 0.6));
  -webkit-box-shadow: 0 0 40px rgba(0,0,0,0.3);
  box-shadow: 3px 4px 8px #1b6eca;
  border-radius: 5% 8% 8% 5%;
  width: min-content;
}
.content{
  line-height: 1.5em;
}

.card_datails  h1 {
  font-size: 30px;
}
.card_right img {
  height: 390px;
  border-radius: 2px;
  width: auto;
}
.card_right {
  border-radius: 2px;
}

a {
  color: darkcyan;
  display: block;
  text-decoration: none;
}

.play_btn {
  height: 100%;
  margin: -390px auto;
  position: relative;
  text-align: center;
  box-shadow: 0 0 50px rgba(0,0,0,0.2);
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

a{
  color: #1b3881;
  text-decoration: none;
}
</style>