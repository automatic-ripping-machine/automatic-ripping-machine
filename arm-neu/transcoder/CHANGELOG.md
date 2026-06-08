# Changelog

## [19.0.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v19.0.0...v19.0.1) (2026-06-05)


### Bug Fixes

* **progress:** parse HandBrake --json progress (fixes UI showing jobs hung at 0%) ([13c9711](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/13c97111d4f593335f1f28c9d6f15060d2e98d86))

## [19.0.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v18.1.1...v19.0.0) (2026-05-27)


### ⚠ BREAKING CHANGES

* contracts has breaking commits in this bump. Review the commit list above and verify consumer code still compiles before merging. release-please will cut a major consumer release when this PR lands.

### Features

* bump components/contracts to 3c73257 ([58de7f3](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/58de7f3e6a51f73652e385ae4898c2e1686fd998))
* bump components/contracts to 5e9a6c2 ([6cce1da](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/6cce1da7ce5eb64126514146af3b3b4eea387b1e))

## [18.1.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v18.1.0...v18.1.1) (2026-05-18)


### Bug Fixes

* **progress:** scale per-file progress to overall for multi-file jobs ([6ad4ad3](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/6ad4ad38ebab87a8e15196e926c21eaf16535614))

## [18.1.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v18.0.0...v18.1.0) (2026-05-10)


### Features

* **presets:** add /api/v1/handbrake-presets endpoint ([b11681c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/b11681c86aea9413c999754e669839b2362b1c0d))
* **rsync:** add run_rsync_async helper ([d09f929](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d09f929b0e9a55d6c02f60f0df8f941ff7e7a214))
* **transcoder:** drive copying_source/finalizing progress from rsync ([54e9f36](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/54e9f3697963916637178d145f623868a3ec4f5a))


### Bug Fixes

* **tests:** use pytest.approx for rsync progress final-event assertion ([ff63251](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/ff6325189ccfde25746fcea6c9c162550354e320))
* **transcoder:** chunk-and-split stdout reader to avoid CR-overwrite deadlock ([1c886a2](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/1c886a23a969907421fbc00f6bd959321356195f))
* **transcoder:** retain strong refs to fire-and-forget progress tasks ([fd4b035](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/fd4b035ba4487440055b2ce19b055edb8bded16f))
* **webhook:** raise body cap to 64KB so multi-track 4K BD payloads pass ([1774cad](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/1774cad0c4f713042f092717e49bf6101714e715))

## [18.0.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v17.6.0...v18.0.0) (2026-05-08)


### ⚠ BREAKING CHANGES

* MOVIES_SUBDIR / TV_SUBDIR / AUDIO_SUBDIR env vars are no longer read. Operators must remove them from transcoder host .env (no harm if left, but they are inert) and set the equivalent on the ARM ripper host instead. Webhook payloads from arm-neu < the matching breaking release will be rejected without input_path.
* contracts has breaking commits in this bump. Review the commit list above and verify consumer code still compiles before merging. release-please will cut a major consumer release when this PR lands.

### Features

* adopt arm_contracts v0.7.0 (WebhookEventType narrowing) ([98335f6](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/98335f6b9a0f64ec54044f3f660d46f635acb33f))
* adopt arm_contracts v2.0.0 (lockstep submodule bump) ([3eacea6](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/3eacea6a8f0a76d3e366241393d9ee1f1c096829))
* bump components/contracts to 37d3fd4 ([c42d9cd](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/c42d9cd9fc41174400cc9917e7fdf799db201e6d))


### Code Refactoring

* drop subdir settings, accept output_path from webhook ([4839f8a](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/4839f8a38b0cf6d9de4009d9ce06cc958a2c87b5))

## [17.6.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v17.5.1...v17.6.0) (2026-04-30)


### Features

* **phase:** track sub-status phase on TranscodeJobDB ([c56cc09](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/c56cc093bf54006e8c2da273dad4ca701235717d))


### Bug Fixes

* bump components/contracts to 67eba7b for rip_progress float fix ([8e61248](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/8e612481568bf7a27a6ac63a256f891c405436f2))

## [17.5.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v17.5.0...v17.5.1) (2026-04-29)


### Bug Fixes

* **callback:** route informational callback through TranscodeCallbackPayload ([639cb08](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/639cb08db69269d9a277ae403bb0bdeefe5bb3e3))
* **callback:** stamp X-Api-Version header on terminal callback POSTs ([afb052f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/afb052f57fc7299f8d9a8241d0ad03a9ed89d25b))

## [17.5.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v17.4.0...v17.5.0) (2026-04-29)


### Features

* bump components/contracts to 1f17568 ([08bf30f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/08bf30f7a66b8791d3a69e53203e111684f6a24c))
* **ci:** build all 4 RC variants in pre-release workflow ([f49b3aa](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/f49b3aa41d0a025bd2c951375a3e6ac4560ea2d5))
* **version:** stamp build identity into VERSION at image-build time ([25ced45](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/25ced453ccc36d6235d6517f4d50a7da5f786ad8))

## [17.4.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v17.3.0...v17.4.0) (2026-04-26)


### Features

* adopt contracts WebhookPayload + TranscodeCallbackPayload ([a068be8](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/a068be86a1b0b552f57f63fa5ec8da712ede6171))

## [17.3.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v17.2.1...v17.3.0) (2026-04-25)


### Features

* **progress:** expose current encoder FPS on transcode jobs ([bfc5207](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/bfc52071e06f70982a69cb4c90381f66aacb514f))


### Bug Fixes

* **progress:** use ReDoS-safe regexes + 100% coverage on fps parsing ([ab50cec](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/ab50cecbc1708a547f20d8b9a91585ecc29a5e5b))

## [17.2.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v17.2.0...v17.2.1) (2026-04-23)


### Bug Fixes

* COPY components/contracts before pip install in Dockerfile.dev ([9d24251](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/9d242516c33c74576e075220a94b89fc4326b297))

## [17.2.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v17.1.1...v17.2.0) (2026-04-23)


### Features

* _notify_arm_callback enqueues to pending_callbacks table ([6237c42](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/6237c428989909c2e942dcdc74fd30850a05a715))
* add arm-contracts as components/contracts submodule ([f923d38](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/f923d3895c778f262a1509338461fefa31008ab7))
* add backoff_seconds schedule for callback drainer ([afb9964](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/afb9964b0bd4ee4933784daf87e2e09d618d77dd))
* add is_permanent_error classifier for callback drainer ([e0a7728](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/e0a7728cf8c7163c4d95f7a56a710a8fb56c56f8))
* add PendingCallbackDB model ([85cb3ae](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/85cb3ae20313b36c1b25649ea173cd4c7943cea1))
* add TranscodeCallbackDrainer.run() background loop ([4e9aa29](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/4e9aa299af664c4d4d7f0c7ebf4532d0cf7cba77))
* add TranscodeCallbackDrainer.send_one ([935dd23](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/935dd2352c4ef4e32a959516880190daa104b1b1))
* add TranscodeCallbackDrainer.sweep_once ([d331574](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d33157464e5b7c85085a0dcd2de4ae4648ec2c85))
* parse webhook config_overrides into TranscodeJobConfig ([ac61c45](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/ac61c459f0021f6cb2759f9b85b7f7fb298d8ce1))
* start callback drainer in main.py lifespan ([0372cf1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/0372cf1d46e35fd6c8550c2b5455481498d92306))


### Bug Fixes

* harden webhook 422 detail shape and preserve explicit nulls ([cb1b568](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/cb1b568f73b7b4e0e1c0e460f3d6f05b8a54b36b))
* **tests:** eliminate timing race in test_worker_processes_queued_job ([63a0a97](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/63a0a97b5a8048feb3a2550d6e496058b0c39580))

## [17.1.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v17.1.0...v17.1.1) (2026-04-22)


### Bug Fixes

* guard snapshot against non-string settings values ([bbd1e45](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/bbd1e45831ce10bcbc4cb1602c18646162a6dbdb))
* pin HANDBRAKE_TAG default to 1.10.2 for reproducible local builds ([9c990f6](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/9c990f6a9bcf250ba3a155052725de80afd6e00e))
* **presets:** clear selected_preset_slug when the active preset is deleted ([0c7ab3c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/0c7ab3c35099bf37f203522d792c598117f71f6b))
* require X-Api-Version header on webhook (flip N+2 back-compat) ([794e488](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/794e48817e5ff9d5e16a50ff5f477b0c7e42fee3))


### Performance Improvements

* snapshot resolved preset at job start ([bf30b75](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/bf30b7561f1e04ed0c8c1c3c8164154ce81b8f5f))

## [17.1.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v17.0.0...v17.1.0) (2026-04-21)


### Features

* API_VERSION constant for cross-service handshake ([c615069](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/c61506906f85689d945f2ca7ea001f412fbe10ff))
* expose api_version in /health response ([0516c78](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/0516c786f7152e624075508c0edb8f70342b28a9))
* validate X-Api-Version on webhook receiver ([d4e7073](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d4e7073cf5b5049f91a50592f621ac3d637d76a2))


### Bug Fixes

* **config:** deserialize dict/list fields from JSON on load ([872c733](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/872c733834677a6af3a7338e795cfacbd86da357))
* **config:** drop legacy ConfigOverrideDB rows on startup with WARN ([be84f77](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/be84f77ce231e38266f4839315d4bae2e516fdc1))
* **config:** serialize dict/list fields as JSON on persist ([26c5b3e](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/26c5b3e184b890941f03b2d108bd0e869dea43c3))
* retry ARM callback with exponential backoff ([d42f60d](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d42f60db16ccbe50893b8fcb2727d1e13f859600))

## [17.0.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v16.0.3...v17.0.0) (2026-04-20)


### ⚠ BREAKING CHANGES

* Old flat config fields (video_encoder, video_quality, handbrake_preset, etc.) replaced by scheme/preset system. Clients must use GET /api/v1/scheme and GET /api/v1/presets instead.

### Features

* add CustomPresetDB model and wire up scheme loading at startup ([bab8019](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/bab80192f822f5092b09ab887dc38a456d1d75bc))
* add preset CRUD API endpoints and integration tests ([ceabbc8](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/ceabbc89fe1c168f152667a3993d1ece903f70c3))
* add Pydantic models for Scheme/Preset/Encoder + resolve_preset ([84a6cb8](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/84a6cb883c7b9fbbe3bc997a45392cfa2f45dd5f))
* preset/scheme system replaces flat encoding config (breaking) ([d286b2d](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d286b2d00bd294ae1b3c0dc8c33c917633888933))
* **presets:** implement full scheme modules for nvidia, intel, amd, software ([b6fb114](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/b6fb114457be9627871f99b0b2990c3ffa3f2f33))
* resolve encoding settings via scheme/preset system ([57d2964](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/57d2964ffe8624ef99b04c74cb05d627e635b7e1))


### Bug Fixes

* accept dict global_overrides in PATCH /config, decode in GET /config ([e4c28b5](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/e4c28b5f565bd2956cf2e457339e5f32ae6e77f4))
* address code review - tier validation, empty presets guard, AttributeError catch, test fixture types ([2fa2067](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/2fa2067fc862661e3bc31b61095f1e57e225d04b))
* advanced_fields type to dict, fix stubs and test assertions ([dbece2d](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/dbece2dcc309f9538b2e453630ee76e09f234065))
* align Dockerfile.dev UID to 1000 matching production ([b414e42](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/b414e42c2ae3f90e4182d4019885842ab48c0a3c))
* clean up stale comments and help text in setup-arm.sh ([1286899](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/128689960cad483fc4eb5250c11dab65c0c6787c))
* **docs:** correct manual setup to use TRANSCODER_URL instead of JSON_URL ([326d854](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/326d854b9a230bcc65a06e336a0f527f8f242f47))
* gate ffmpeg encoder probe on functional hardware test ([45c75ea](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/45c75eaa008d1881ab1006bf4befd8349f136a8a))
* remove COPY presets/ from Dockerfile.dev (file-based presets retired) ([f157705](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/f157705c8cc0c3e42e249c809dafb2c679cab1cd))
* setup-arm.sh uses TRANSCODER_URL instead of JSON_URL ([803fd10](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/803fd109785ee09cd48f632704b281c57c9c41b7))
* **sonar:** extract HandBrake preset constants, document endpoint responses, split validation helper ([b2fc9a9](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/b2fc9a9902a635f3a16d088769584fed4c5f69e4))
* **sonar:** use https scheme in ASGITransport test fixture base_url ([2d105bf](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/2d105bf1c740e6d4f3949bccc81f0ff91abffd4e))
* tolerate NFS root_squash in entrypoint chown ([a625d71](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/a625d71693ca6de21bdd3ac5ebeb357bf92ea2eb))
* update final test files for preset refactor ([6d66cce](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/6d66ccee5c7673665820ba6e4bc486b89c12473e))
* update remaining test files for preset refactor ([f94c55f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/f94c55f32655fcd8cdaf02b5a7731177080dddd6))
* update test_config.py and health endpoint for preset refactor ([1856c52](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/1856c52c0a16239badb12b30799e6c55a2a6dcd9))
* update test_transcoder.py for scheme/preset system ([a326ecf](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/a326ecf9d9babefd00aebe4281a556e4047210eb))
* use 256x256 frame for GPU encoder probe (NVENC minimum size) ([30880a7](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/30880a7e6bd46ee2f9907e86c506a1f2a3c34704))

## [16.0.3](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v16.0.2...v16.0.3) (2026-04-14)


### Bug Fixes

* default ARM_CALLBACK_URL to arm-rippers:8080 in .env.example ([eaef695](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/eaef695cc6bcdac6b42f8c598d41574398d9d66a))

## [16.0.2](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v16.0.1...v16.0.2) (2026-04-13)


### Bug Fixes

* CPU-only image skips GPU detection to prevent false QSV selection ([9ce1acc](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/9ce1acca716b4071117014a1e7904831d8c1a1e6))

## [16.0.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v16.0.0...v16.0.1) (2026-04-12)


### Bug Fixes

* Intel QSV broken — missing oneVPL runtime and driver permissions ([5d06cb4](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/5d06cb4c9585457a12887cb1ad0487e42fd9a9ca))

## [16.0.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v15.0.2...v16.0.0) (2026-04-05)


### ⚠ BREAKING CHANGES

* Worker API changed — run() now requires worker_id parameter, _current_job replaced with _active_jobs dict, sentinel-based shutdown replaces shutdown_event-only pattern. Health and stats endpoints now include active_count and max_concurrent fields. New /workers endpoint. main.py restructured into routers/ package.

### Features

* multi-worker concurrency with per-worker tracking ([8004886](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/80048868926400bdd9a57dd22aaedc7456a14b1f))


### Bug Fixes

* add fallback for killpg failure in restart endpoint ([21f1333](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/21f13334a7aa32cda2659ea59dd4dd95962f27d8))
* align default UID to 1000 to match ARM ripper ([5ac7b6b](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/5ac7b6b434d677d8f71ff79f457caa8650a7e12f))
* increase asyncio StreamReader limit for HandBrake/FFmpeg output ([1bfda8b](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/1bfda8b0b688c1d379e551f469c84be413d4c37c))
* move blocking filesystem ops off event loop ([0a627fb](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/0a627fbf57c8612e4bbf615cc5e00df9c25ec255))
* reorder Dockerfile COPY so VERSION layer is never stale ([08e97f3](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/08e97f38736222f580fc785243fc9447ede3691b))
* resolve SonarCloud issues — Annotated DI, redundant exception, unused vars ([0650180](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/065018004bb5ebdee2b8afdac522c5e52458b6f1))
* wrap remaining NFS path.exists calls in run_in_executor ([2e8e808](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/2e8e808de0f2d28cc49860afa757e9d1f966814f))

## [15.0.2](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v15.0.1...v15.0.2) (2026-03-30)


### Bug Fixes

* add rsync to Docker image - required by file_transfer.py ([17e6ddb](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/17e6ddb177530daee2f7332d910a5c552ccbc46b))

## [15.0.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v15.0.0...v15.0.1) (2026-03-30)


### Bug Fixes

* replace blocking shutil with async rsync subprocess for NFS file operations ([ab651b8](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/ab651b85da448f45dd7b4c47a4a2e2f62d333946))

## [15.0.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v14.0.1...v15.0.0) (2026-03-29)


### ⚠ BREAKING CHANGES

* `latest` tag is now CPU-only (software x265/x264). NVIDIA users must switch to `latest-nvidia` or `docker-compose.nvidia.yml`. AMD and Intel tags are unchanged.

### Features

* add gpu_monitor with nvidia, amd, and intel backends ([d687666](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d687666efbf0e9bf5d270ac3678cbcebb98983d4))
* add gpu_vendor setting for GPU monitoring selection ([984fea1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/984fea11e9ba027ce2cce95c328a5baf53e26bf3))
* add power draw, power limit, core clock, and memory clock to GPU metrics ([324abe9](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/324abe9727bfa8254d414cc6b3e6430f163a778e))
* make CPU-only the default image, NVIDIA moves to -nvidia suffix ([797082d](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/797082d8ba3c80d14f8b62e502e282c1f85e495f))
* set GPU_VENDOR env in Docker layers, add intel-gpu-tools and capabilities ([668c735](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/668c735e9e4fd83c69b9ab92d2a92addbd651612))
* wire GPU monitor into /system/stats endpoint ([9212a05](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/9212a055526e7435910563d0dc78b8c1297fce93))


### Bug Fixes

* improve gpu_monitor coverage to 100% and remove redundant IOError catch ([d147248](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d1472481cbbd203fe13d1be1f1279fe87afd91b9))
* remove dead conditional in multi-title naming test (SonarCloud reliability) ([58aa9c3](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/58aa9c39ea2985ea7c3731adec7d8213c86a3c99))
* remove redundant json.JSONDecodeError (subclass of ValueError) ([2b094fb](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/2b094fb423e511a6653df5c29c97dad352bc6f9b))
* use pytest.approx for float comparisons (SonarCloud S1244) ([74d1375](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/74d1375af8efb9966b629ca54b04b9e3b6ead3c6))

## [14.0.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v14.0.0...v14.0.1) (2026-03-26)


### Bug Fixes

* multi-title main feature embeds source filename for metadata matching ([27698ef](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/27698efa3b5f81667fd36cb87e195a698d13e308))
* refresh naming metadata on job re-queue ([7d0ab2e](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/7d0ab2ee727be2dd4c45e0f12de159f81cedbda9))

## [14.0.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v13.1.1...v14.0.0) (2026-03-25)


### Features

* use ARM track manifest for naming regardless of multi_title ([e1a221e](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/e1a221ebadd13dd31ae4a174a09984b96b7c2b83))

## [13.1.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v13.1.0...v13.1.1) (2026-03-22)


### Bug Fixes

* mock os.killpg instead of sys.exit in restart endpoint test ([b34b4b9](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/b34b4b970e76ed4d9df83e83f2645455f493a32e))
* use os.killpg for restart endpoint to terminate entire process group ([31b28cc](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/31b28ccc6d5f0e0de51ed600ff805ee97e0f3ba0))

## [13.1.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v13.0.1...v13.1.0) (2026-03-20)


### Features

* add POST /system/restart endpoint ([f317b02](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/f317b02294262da02cc6ea69deab36224b1726a9))


### Bug Fixes

* use sys.exit instead of os.kill for SonarCloud hotspot ([6163832](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/616383293e6f09656bd20e71fbb4279ae88bb193))

## [13.0.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v13.0.0...v13.0.1) (2026-03-18)


### Bug Fixes

* add missing config vars to .env.example and docker-compose ([26ac440](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/26ac4404a82aadc2d9e70a0828ab4f44b97ee3b1))
* address SonarCloud security hotspot and reliability issues ([f6500a1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/f6500a177baab3477aa88b02969c438fe9090368))
* resolve SonarCloud security hotspot and reliability bug ([249f7e9](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/249f7e99f4b8878a745edd28fa09a6a83d2a3d5e))

## [13.0.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v12.0.0...v13.0.0) (2026-03-14)


### ⚠ BREAKING CHANGES

* version alignment for v12 release

### Features

* add /system/stats endpoint for live CPU, temp, and memory metrics ([9f4326c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/9f4326c5bf4cf0fa0276cd73a37acd82450b7645))
* add ARM callback and NFS wait for source path ([84a27d7](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/84a27d724bf9bebc8345693070f044e97230722f))
* Add ARM setup automation script ([c00d34c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/c00d34c38e8848a3724c9c99ec7a5b2c28fa597d))
* add arm_job_id filter to /jobs endpoint ([7d9db3a](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/7d9db3a8647c1a8047b77b7176061137b41f7f0e))
* Add audio CD passthrough to music folder ([ee49572](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/ee49572c0ef44c4aacf39c786e8f32ecff27cdf3))
* Add authentication and security improvements ([12f8a35](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/12f8a35ad7839812d639a85e40cd2b3118c520eb))
* Add comprehensive test suite and fix documentation ([e6c9b7a](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/e6c9b7ace7711908242b3bab8601d0a1ba070276))
* add config persistence model and psutil dependency ([39aefd7](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/39aefd7c923cfb7cf412c93d7f7824d80f97f978))
* add GPU auto-detection, config management, and system monitoring ([94db4fa](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/94db4fa42df444f8e71c26a351c390d097461e1d))
* add LOG_LEVEL_LIBRARIES setting for third-party logger levels ([5fbef84](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/5fbef84a346d69b93dcdf93ca57fa0923fffceb1))
* Add media metadata to output folder and file names ([6b1fb39](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/6b1fb39bd00ce4424a29d5fd91dd0cf707e53531))
* Add multi-GPU support (AMD VAAPI/AMF, Intel QSV, software) ([6964d2a](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/6964d2ad440d92f92f7786ce0bb43ee0ed179552))
* Add optical drive watcher for ARM container auto-restart ([27bde1f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/27bde1f5a59b5e41423e09666220e47ebf4c694c))
* add poster_url to webhook payload, DB, and /jobs API ([2d2f059](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/2d2f059e176058b2c72125e7cfec872b032dfab7))
* Add resolution-based preset selection for all GPU backends ([717cb67](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/717cb67ad869b75a60d0fbbc5f60b2e0387054dc))
* add rotating file logging and log viewer API ([84f8c5e](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/84f8c5e4460aac9e00a941142698f45eb9aa433a))
* Add security infrastructure and validation (Phase 1) ([76f93a5](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/76f93a54dd5a8ba733ba2b266488d6698f73c452))
* Add stable optical drive symlink script ([6334854](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/63348548fb8c363de888b8c7181281537c13403f))
* add storage disk usage to /system/stats endpoint ([0b50d57](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/0b50d57555a9650c55c96dc5bc5122f006dc7280))
* enhance ARM notification script with raw path support ([98188ef](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/98188ef18d21a8cf7e40b6bba70a90c3e20d71f3))
* expose version from VERSION file in API and health endpoint ([703465e](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/703465e6cf7c8380ee909c02b02e17f7202215c4))
* extract HandBrake build into separately-published image ([f384d9f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/f384d9f25845cbd035a5107796cc565b06c2c803))
* forward ARM metadata through webhook to transcoder ([affa688](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/affa688e903400ea8564ce3133be58f7b5c80c0f))
* multi-title disc support — per-track output routing ([e4b802e](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/e4b802edc5b8557e00a0f59846e48388d6d3cab1))
* notify ARM-neu to update submodule on release ([c63ae6c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/c63ae6cd39924c9c9e51a7ed45135238dc61b1d6))
* per-device debounce in drive watcher ([776b890](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/776b890f5dd8212c7e06ecfb3cd33208067e4353))
* per-job transcode config overrides ([95d7b10](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/95d7b102bdecb13996668cd09bbf56d27a6437c1))
* per-job transcoder log files ([4510352](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/4510352d5439c7f5bb36e97070e546307f950729))
* per-track failure handling, resilient metadata matching, partial status ([683e8c1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/683e8c154bf2953bd73bf4057c541cfffa29b1a2))
* split Dockerfile into base image + thin GPU layers ([f3b3c3f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/f3b3c3fee415d6f51554ab474c6b0b0d267c5004))
* structured logging with structlog ([773b291](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/773b2917ec588ccdd6660843dafbf832b2911671))
* unified multi-GPU Dockerfile with HandBrake 1.10.2 ([37e8b2c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/37e8b2c1f572d8ba5eefce37e6b820091ab1add1))
* use ARM-provided naming instead of local folder name logic ([26a0491](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/26a04918fcb08b44853c8de2e785eaec652f1945))
* Use local scratch storage to avoid heavy I/O on NFS ([09c2954](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/09c29540cc6ee687bae61b7ea4c98f7ff0b10918))


### Bug Fixes

* add --reload to Dockerfile.dev CMD for hot-reload support ([edd4d30](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/edd4d30dfc6b265b6039e9e274545b0c49c75ea9))
* add audio-copy-mask to preserve all audio codecs in passthrough ([cc21c29](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/cc21c29b546e61901fda55129c2d29e86a334c1d))
* add defaults for volume paths, fix stale image namespace ([05408b4](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/05408b43e3b811d6514a8866f46ff4d8f4c47b36))
* add folder_name and title_name to database migration list ([7d19152](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/7d19152e8ae6af850de457f830bf81b6061cfc31))
* add LOG_PATH env var to test conftest to prevent CI failure ([221ef88](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/221ef88130919237475a81e7f7a29c13d5db17d3))
* Add worker 503 guards, graceful shutdown, and import cleanup ([f06e1b9](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/f06e1b97ce7a51b767b468870bcca7b6eb196b72))
* address SonarCloud reliability bugs ([2bc0104](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/2bc010418959a822cbb6514b5b98b651fe15c1cf))
* Apprise webhook compatibility and ARM integration config ([83a6b49](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/83a6b495cae5be9b100623c9f61cb135c1780597))
* check /etc/arm-transcoder-version for dev compose VERSION mount ([18e5865](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/18e58652c7541cb81a037478d3c5eaf3665b0723))
* coerce job_id to string in webhook payload validation ([802d83f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/802d83f507c3ff877c2dbb6bf855cff157306b16))
* configure release-please to update VERSION file ([61a132f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/61a132f88fe3ef029fe4633f3042f2b0d14019d3))
* Correct HandBrake preset name to match built-in presets ([eba50a2](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/eba50a21d6bca3a7c0e264a1fabe73e2398bd62a))
* Create render group in Intel and AMD Dockerfiles ([b089af6](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/b089af6b5eaa56609efef80d8302c75d7be3d1b7))
* deduplicate webhook — skip if job already queued for same source ([866a924](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/866a9241be60d5e88e4915ff16cad533aa1344cf))
* disambiguate output filenames for tracks without custom titles ([7e1a6c9](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/7e1a6c950254d7442ef8a68e21ae80d5117ee7ea))
* Increase drive watcher debounce default to 60s ([9520288](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/95202881ce91ceb4cab763cc1757d58b8e9fa14c))
* Install HandBrake from PPA instead of Alpine multi-stage copy ([d3f3322](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d3f33224af53c63fa9691af021d05c02338c6ab9))
* line too long in /system/stats endpoint ([02423b3](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/02423b37a88065bd606cc6e8eb5613223df9cf8b))
* Make audio passthrough source cleanup non-fatal ([a43383e](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/a43383e8fbdacb9b1e628b037193705f280f6c97))
* make per-job log handler creation non-fatal ([9dd2dc7](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/9dd2dc713a39ed07be4a84e017d5a1bc54060b75))
* match production UID/GID in Dockerfile.dev ([3fffc8d](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/3fffc8d98525dfd408dce613fe93200c24b30cb1))
* mount raw volume as rw so DELETE_SOURCE can clean up after transcode ([e55cb64](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/e55cb641cf95d7c5ee2582029ee6afa12116a793))
* notify ARM when transcoding starts so job status updates to transcoding ([8fc72c5](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/8fc72c567e1ae1a73df3603416cd5969536a30a6))
* only restart container when rescan script is missing (rc 126/127) ([83ba5fc](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/83ba5fcd1fda27abb9590bc76ab1bb018abf3a3a))
* Pass all application settings through Docker compose environment ([0dbb17f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/0dbb17f1936fffe763526b7e0d3c90f548a16a97))
* Prevent restart loop by checking device visibility in container ([0d76b52](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/0d76b522010109900ea1b9a109a0d147dc9636be))
* Re-resolve source path after stabilization when no files found ([2f50791](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/2f50791c6db9e6ce04c7b5f3c9af8fab1f4e8319))
* remove invalid opus from audio-copy-mask, add mp2 and aac fallback ([757f1ee](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/757f1eebc3e55a27c84560c74b79294f926b197a))
* Replace device visibility check with container uptime check ([4023f52](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/4023f52789ca37d559193a8259cedff100db8064))
* resolve 9 pre-existing test failures in CI ([a061809](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/a0618099743ea8d282c6b9650828c5e86488ded6))
* Resolve ARM subdirectory paths for ripped media ([a28403f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/a28403f10c1d156cbe70bd89a066b510ab6aa3f7))
* resolve flake8 lint errors ([29489ae](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/29489aefa837ba4a5df2dacb156ddc507e065b4a))
* resolve SonarCloud HIGH issues (S7688, S8415, S1192, S3776) ([6c04900](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/6c04900b464eebb3cc89fac48e44805c3c7fc730))
* resolve SonarCloud issues in test files ([de3335d](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/de3335d030b8d9d8c2cd5aa00dab23663b1adb36))
* scope workflow permissions to job level (S8264/S8233) ([e58c08d](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/e58c08dd7da2d11456a6540d9306b333a6b10763))
* search parent directory for VERSION file ([d06c5b6](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d06c5b61f8287cf12d94ec47623eea316605587d))
* serialize dedup check with asyncio.Lock to prevent race condition ([d30a316](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d30a316b30a3c70e9f18a12760c84b8c51da2824))
* set VERSION to 12.0.0 for v13 release alignment ([51a67a4](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/51a67a43348040047c30c37fff126d9be23cf5a5))
* Short-lived DB sessions, progress rate limiting, stream mapping, and disk space checks ([c0e200b](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/c0e200b593721a92fb104f14f4aa8f1f31fd1df5))
* silence noisy third-party loggers at WARNING level ([d6b8c72](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d6b8c7207034593259cf56c5e0bfce6834639b76))
* Update Intel Dockerfile for Debian Trixie package names ([50bccb6](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/50bccb6c6b616784a43a8b39ccdab22251d7b6f1))
* update tests for queue_job tuple return and overrides kwarg ([ef8d535](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/ef8d535281e44d1cad09ab561dd547b7cc5780ba))
* update webhook title fallback test for new extraction logic ([9776b05](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/9776b054eeb859ac4af5969f8dbef7f122a3425c))
* use ARM title_name directly, only add track suffix as fallback ([9bf2807](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/9bf28075ad475a44010eceefccd6b9c8530adb71))
* use constant-time comparison for API key and webhook secret auth ([2fc4441](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/2fc4441ce77427e244d056237bdd70e84871c7b2))
* Use copy instead of move for audio passthrough ([d5302e5](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d5302e5af3ffcb8dcc81ecbe29a3728f84b7f880))
* use DOCKERHUB_USERNAME secret for image name ([8f01c7c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/8f01c7c5c11624596ea368dd15d1032305af4c43))
* Use extracted media title for job naming and graceful cleanup ([5f44c76](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/5f44c76776908ceb8449db007a2c97009f659ae2))
* use final path from ARM webhook instead of parsing body text ([5b48982](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/5b489829ac4d0cc2d331cb4e8fe74ba0be1dc86d))
* use PAT for release-please so releases trigger publish workflow ([fd72f4b](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/fd72f4b516c2a58c99d47d2932f6e93081fcf535))
* use RELEASE_PAT for parent repo dispatch ([5d16cda](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/5d16cda1160f4c554a7f64459ebce9f89261936b))
* Use Ubuntu universe repo for HandBrake instead of PPA ([912bcef](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/912bcef1b06f178d6d459e251abab503cc0d64c5))


### Miscellaneous Chores

* set pre-release version for 12.0.0 ([27aea55](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/27aea5556b157c3187aa11a048f6952946ae9e2f))

## [10.10.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v10.9.1...v10.10.0) (2026-03-09)


### Features

* add /system/stats endpoint for live CPU, temp, and memory metrics ([9f4326c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/9f4326c5bf4cf0fa0276cd73a37acd82450b7645))
* add ARM callback and NFS wait for source path ([84a27d7](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/84a27d724bf9bebc8345693070f044e97230722f))
* Add ARM setup automation script ([c00d34c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/c00d34c38e8848a3724c9c99ec7a5b2c28fa597d))
* Add audio CD passthrough to music folder ([ee49572](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/ee49572c0ef44c4aacf39c786e8f32ecff27cdf3))
* Add authentication and security improvements ([12f8a35](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/12f8a35ad7839812d639a85e40cd2b3118c520eb))
* Add comprehensive test suite and fix documentation ([e6c9b7a](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/e6c9b7ace7711908242b3bab8601d0a1ba070276))
* add config persistence model and psutil dependency ([39aefd7](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/39aefd7c923cfb7cf412c93d7f7824d80f97f978))
* add GPU auto-detection, config management, and system monitoring ([94db4fa](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/94db4fa42df444f8e71c26a351c390d097461e1d))
* add LOG_LEVEL_LIBRARIES setting for third-party logger levels ([5fbef84](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/5fbef84a346d69b93dcdf93ca57fa0923fffceb1))
* Add media metadata to output folder and file names ([6b1fb39](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/6b1fb39bd00ce4424a29d5fd91dd0cf707e53531))
* Add multi-GPU support (AMD VAAPI/AMF, Intel QSV, software) ([6964d2a](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/6964d2ad440d92f92f7786ce0bb43ee0ed179552))
* Add optical drive watcher for ARM container auto-restart ([27bde1f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/27bde1f5a59b5e41423e09666220e47ebf4c694c))
* add poster_url to webhook payload, DB, and /jobs API ([2d2f059](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/2d2f059e176058b2c72125e7cfec872b032dfab7))
* Add resolution-based preset selection for all GPU backends ([717cb67](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/717cb67ad869b75a60d0fbbc5f60b2e0387054dc))
* add rotating file logging and log viewer API ([84f8c5e](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/84f8c5e4460aac9e00a941142698f45eb9aa433a))
* Add security infrastructure and validation (Phase 1) ([76f93a5](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/76f93a54dd5a8ba733ba2b266488d6698f73c452))
* Add stable optical drive symlink script ([6334854](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/63348548fb8c363de888b8c7181281537c13403f))
* add storage disk usage to /system/stats endpoint ([0b50d57](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/0b50d57555a9650c55c96dc5bc5122f006dc7280))
* enhance ARM notification script with raw path support ([98188ef](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/98188ef18d21a8cf7e40b6bba70a90c3e20d71f3))
* expose version from VERSION file in API and health endpoint ([703465e](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/703465e6cf7c8380ee909c02b02e17f7202215c4))
* extract HandBrake build into separately-published image ([f384d9f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/f384d9f25845cbd035a5107796cc565b06c2c803))
* forward ARM metadata through webhook to transcoder ([affa688](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/affa688e903400ea8564ce3133be58f7b5c80c0f))
* notify ARM-neu to update submodule on release ([c63ae6c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/c63ae6cd39924c9c9e51a7ed45135238dc61b1d6))
* per-device debounce in drive watcher ([776b890](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/776b890f5dd8212c7e06ecfb3cd33208067e4353))
* per-job transcode config overrides ([95d7b10](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/95d7b102bdecb13996668cd09bbf56d27a6437c1))
* per-job transcoder log files ([4510352](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/4510352d5439c7f5bb36e97070e546307f950729))
* split Dockerfile into base image + thin GPU layers ([f3b3c3f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/f3b3c3fee415d6f51554ab474c6b0b0d267c5004))
* structured logging with structlog ([773b291](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/773b2917ec588ccdd6660843dafbf832b2911671))
* unified multi-GPU Dockerfile with HandBrake 1.10.2 ([37e8b2c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/37e8b2c1f572d8ba5eefce37e6b820091ab1add1))
* Use local scratch storage to avoid heavy I/O on NFS ([09c2954](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/09c29540cc6ee687bae61b7ea4c98f7ff0b10918))


### Bug Fixes

* add --reload to Dockerfile.dev CMD for hot-reload support ([edd4d30](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/edd4d30dfc6b265b6039e9e274545b0c49c75ea9))
* add audio-copy-mask to preserve all audio codecs in passthrough ([cc21c29](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/cc21c29b546e61901fda55129c2d29e86a334c1d))
* add defaults for volume paths, fix stale image namespace ([05408b4](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/05408b43e3b811d6514a8866f46ff4d8f4c47b36))
* add LOG_PATH env var to test conftest to prevent CI failure ([221ef88](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/221ef88130919237475a81e7f7a29c13d5db17d3))
* Add worker 503 guards, graceful shutdown, and import cleanup ([f06e1b9](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/f06e1b97ce7a51b767b468870bcca7b6eb196b72))
* address SonarCloud reliability bugs ([2bc0104](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/2bc010418959a822cbb6514b5b98b651fe15c1cf))
* Apprise webhook compatibility and ARM integration config ([83a6b49](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/83a6b495cae5be9b100623c9f61cb135c1780597))
* coerce job_id to string in webhook payload validation ([802d83f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/802d83f507c3ff877c2dbb6bf855cff157306b16))
* configure release-please to update VERSION file ([61a132f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/61a132f88fe3ef029fe4633f3042f2b0d14019d3))
* Correct HandBrake preset name to match built-in presets ([eba50a2](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/eba50a21d6bca3a7c0e264a1fabe73e2398bd62a))
* Create render group in Intel and AMD Dockerfiles ([b089af6](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/b089af6b5eaa56609efef80d8302c75d7be3d1b7))
* deduplicate webhook — skip if job already queued for same source ([866a924](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/866a9241be60d5e88e4915ff16cad533aa1344cf))
* Increase drive watcher debounce default to 60s ([9520288](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/95202881ce91ceb4cab763cc1757d58b8e9fa14c))
* Install HandBrake from PPA instead of Alpine multi-stage copy ([d3f3322](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d3f33224af53c63fa9691af021d05c02338c6ab9))
* line too long in /system/stats endpoint ([02423b3](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/02423b37a88065bd606cc6e8eb5613223df9cf8b))
* Make audio passthrough source cleanup non-fatal ([a43383e](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/a43383e8fbdacb9b1e628b037193705f280f6c97))
* make per-job log handler creation non-fatal ([9dd2dc7](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/9dd2dc713a39ed07be4a84e017d5a1bc54060b75))
* match production UID/GID in Dockerfile.dev ([3fffc8d](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/3fffc8d98525dfd408dce613fe93200c24b30cb1))
* mount raw volume as rw so DELETE_SOURCE can clean up after transcode ([e55cb64](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/e55cb641cf95d7c5ee2582029ee6afa12116a793))
* notify ARM when transcoding starts so job status updates to transcoding ([8fc72c5](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/8fc72c567e1ae1a73df3603416cd5969536a30a6))
* only restart container when rescan script is missing (rc 126/127) ([83ba5fc](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/83ba5fcd1fda27abb9590bc76ab1bb018abf3a3a))
* Pass all application settings through Docker compose environment ([0dbb17f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/0dbb17f1936fffe763526b7e0d3c90f548a16a97))
* Prevent restart loop by checking device visibility in container ([0d76b52](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/0d76b522010109900ea1b9a109a0d147dc9636be))
* Re-resolve source path after stabilization when no files found ([2f50791](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/2f50791c6db9e6ce04c7b5f3c9af8fab1f4e8319))
* remove invalid opus from audio-copy-mask, add mp2 and aac fallback ([757f1ee](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/757f1eebc3e55a27c84560c74b79294f926b197a))
* Replace device visibility check with container uptime check ([4023f52](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/4023f52789ca37d559193a8259cedff100db8064))
* resolve 9 pre-existing test failures in CI ([a061809](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/a0618099743ea8d282c6b9650828c5e86488ded6))
* Resolve ARM subdirectory paths for ripped media ([a28403f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/a28403f10c1d156cbe70bd89a066b510ab6aa3f7))
* resolve flake8 lint errors ([29489ae](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/29489aefa837ba4a5df2dacb156ddc507e065b4a))
* resolve SonarCloud HIGH issues (S7688, S8415, S1192, S3776) ([6c04900](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/6c04900b464eebb3cc89fac48e44805c3c7fc730))
* scope workflow permissions to job level (S8264/S8233) ([e58c08d](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/e58c08dd7da2d11456a6540d9306b333a6b10763))
* serialize dedup check with asyncio.Lock to prevent race condition ([d30a316](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d30a316b30a3c70e9f18a12760c84b8c51da2824))
* Short-lived DB sessions, progress rate limiting, stream mapping, and disk space checks ([c0e200b](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/c0e200b593721a92fb104f14f4aa8f1f31fd1df5))
* silence noisy third-party loggers at WARNING level ([d6b8c72](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d6b8c7207034593259cf56c5e0bfce6834639b76))
* Update Intel Dockerfile for Debian Trixie package names ([50bccb6](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/50bccb6c6b616784a43a8b39ccdab22251d7b6f1))
* update tests for queue_job tuple return and overrides kwarg ([ef8d535](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/ef8d535281e44d1cad09ab561dd547b7cc5780ba))
* update webhook title fallback test for new extraction logic ([9776b05](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/9776b054eeb859ac4af5969f8dbef7f122a3425c))
* use constant-time comparison for API key and webhook secret auth ([2fc4441](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/2fc4441ce77427e244d056237bdd70e84871c7b2))
* Use copy instead of move for audio passthrough ([d5302e5](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d5302e5af3ffcb8dcc81ecbe29a3728f84b7f880))
* use DOCKERHUB_USERNAME secret for image name ([8f01c7c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/8f01c7c5c11624596ea368dd15d1032305af4c43))
* Use extracted media title for job naming and graceful cleanup ([5f44c76](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/5f44c76776908ceb8449db007a2c97009f659ae2))
* use final path from ARM webhook instead of parsing body text ([5b48982](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/5b489829ac4d0cc2d331cb4e8fe74ba0be1dc86d))
* use PAT for release-please so releases trigger publish workflow ([fd72f4b](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/fd72f4b516c2a58c99d47d2932f6e93081fcf535))
* use RELEASE_PAT for parent repo dispatch ([5d16cda](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/5d16cda1160f4c554a7f64459ebce9f89261936b))
* Use Ubuntu universe repo for HandBrake instead of PPA ([912bcef](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/912bcef1b06f178d6d459e251abab503cc0d64c5))

## [10.9.1-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v10.9.0-alpha.1...v10.9.1-alpha.1) (2026-03-05)


### Bug Fixes

* only restart container when rescan script is missing (rc 126/127) ([83ba5fc](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/83ba5fcd1fda27abb9590bc76ab1bb018abf3a3a))

## [10.9.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v10.8.4-alpha.1...v10.9.0-alpha.1) (2026-03-04)


### Features

* per-device debounce in drive watcher ([776b890](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/776b890f5dd8212c7e06ecfb3cd33208067e4353))

## [10.8.4-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v10.8.3-alpha.1...v10.8.4-alpha.1) (2026-03-03)


### Bug Fixes

* resolve SonarCloud HIGH issues (S7688, S8415, S1192, S3776) ([6c04900](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/6c04900b464eebb3cc89fac48e44805c3c7fc730))

## [10.8.3-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v10.8.2-alpha.1...v10.8.3-alpha.1) (2026-03-02)


### Bug Fixes

* address SonarCloud reliability bugs ([2bc0104](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/2bc010418959a822cbb6514b5b98b651fe15c1cf))

## [10.8.2-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v10.8.1-alpha.1...v10.8.2-alpha.1) (2026-03-02)


### Bug Fixes

* scope workflow permissions to job level (S8264/S8233) ([e58c08d](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/e58c08dd7da2d11456a6540d9306b333a6b10763))

## [10.8.1-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v10.8.0-alpha.1...v10.8.1-alpha.1) (2026-03-02)


### Bug Fixes

* notify ARM when transcoding starts so job status updates to transcoding ([8fc72c5](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/8fc72c567e1ae1a73df3603416cd5969536a30a6))

## [10.8.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v10.7.0-alpha.1...v10.8.0-alpha.1) (2026-03-01)


### Features

* add ARM callback and NFS wait for source path ([84a27d7](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/84a27d724bf9bebc8345693070f044e97230722f))

## [10.7.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v10.6.0-alpha.1...v10.7.0-alpha.1) (2026-03-01)


### Features

* extract HandBrake build into separately-published image ([f384d9f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/f384d9f25845cbd035a5107796cc565b06c2c803))

## [10.6.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v10.5.0-alpha.1...v10.6.0-alpha.1) (2026-03-01)


### Features

* per-job transcode config overrides ([95d7b10](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/95d7b102bdecb13996668cd09bbf56d27a6437c1))
* split Dockerfile into base image + thin GPU layers ([f3b3c3f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/f3b3c3fee415d6f51554ab474c6b0b0d267c5004))


### Bug Fixes

* add --reload to Dockerfile.dev CMD for hot-reload support ([edd4d30](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/edd4d30dfc6b265b6039e9e274545b0c49c75ea9))
* deduplicate webhook — skip if job already queued for same source ([866a924](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/866a9241be60d5e88e4915ff16cad533aa1344cf))
* match production UID/GID in Dockerfile.dev ([3fffc8d](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/3fffc8d98525dfd408dce613fe93200c24b30cb1))
* mount raw volume as rw so DELETE_SOURCE can clean up after transcode ([e55cb64](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/e55cb641cf95d7c5ee2582029ee6afa12116a793))
* serialize dedup check with asyncio.Lock to prevent race condition ([d30a316](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d30a316b30a3c70e9f18a12760c84b8c51da2824))
* update tests for queue_job tuple return and overrides kwarg ([ef8d535](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/ef8d535281e44d1cad09ab561dd547b7cc5780ba))

## [10.5.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v10.4.0-alpha.1...v10.5.0-alpha.1) (2026-02-28)


### Features

* add poster_url to webhook payload, DB, and /jobs API ([2d2f059](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/2d2f059e176058b2c72125e7cfec872b032dfab7))

## [10.4.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v10.3.0-alpha.1...v10.4.0-alpha.1) (2026-02-28)


### Features

* per-job transcoder log files ([4510352](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/4510352d5439c7f5bb36e97070e546307f950729))


### Bug Fixes

* make per-job log handler creation non-fatal ([9dd2dc7](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/9dd2dc713a39ed07be4a84e017d5a1bc54060b75))

## [10.3.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v10.2.0-alpha.1...v10.3.0-alpha.1) (2026-02-28)


### Features

* add LOG_LEVEL_LIBRARIES setting for third-party logger levels ([5fbef84](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/5fbef84a346d69b93dcdf93ca57fa0923fffceb1))
* structured logging with structlog ([773b291](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/773b2917ec588ccdd6660843dafbf832b2911671))


### Bug Fixes

* silence noisy third-party loggers at WARNING level ([d6b8c72](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d6b8c7207034593259cf56c5e0bfce6834639b76))

## [10.2.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v10.1.3-alpha.1...v10.2.0-alpha.1) (2026-02-26)


### Features

* unified multi-GPU Dockerfile with HandBrake 1.10.2 ([37e8b2c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/37e8b2c1f572d8ba5eefce37e6b820091ab1add1))


### Bug Fixes

* update webhook title fallback test for new extraction logic ([9776b05](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/9776b054eeb859ac4af5969f8dbef7f122a3425c))

## [10.1.3-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v10.1.2-alpha.1...v10.1.3-alpha.1) (2026-02-25)


### Bug Fixes

* add defaults for volume paths, fix stale image namespace ([05408b4](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/05408b43e3b811d6514a8866f46ff4d8f4c47b36))

## [10.1.2-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v10.1.1-alpha.1...v10.1.2-alpha.1) (2026-02-25)


### Bug Fixes

* coerce job_id to string in webhook payload validation ([802d83f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/802d83f507c3ff877c2dbb6bf855cff157306b16))

## [10.1.1-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v10.1.0-alpha.1...v10.1.1-alpha.1) (2026-02-25)


### Bug Fixes

* use constant-time comparison for API key and webhook secret auth ([2fc4441](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/2fc4441ce77427e244d056237bdd70e84871c7b2))

## [10.1.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v10.0.0-alpha.1...v10.1.0-alpha.1) (2026-02-25)


### Features

* add /system/stats endpoint for live CPU, temp, and memory metrics ([9f4326c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/9f4326c5bf4cf0fa0276cd73a37acd82450b7645))
* Add ARM setup automation script ([c00d34c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/c00d34c38e8848a3724c9c99ec7a5b2c28fa597d))
* Add audio CD passthrough to music folder ([ee49572](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/ee49572c0ef44c4aacf39c786e8f32ecff27cdf3))
* Add authentication and security improvements ([12f8a35](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/12f8a35ad7839812d639a85e40cd2b3118c520eb))
* Add comprehensive test suite and fix documentation ([e6c9b7a](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/e6c9b7ace7711908242b3bab8601d0a1ba070276))
* add config persistence model and psutil dependency ([39aefd7](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/39aefd7c923cfb7cf412c93d7f7824d80f97f978))
* add GPU auto-detection, config management, and system monitoring ([94db4fa](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/94db4fa42df444f8e71c26a351c390d097461e1d))
* Add media metadata to output folder and file names ([6b1fb39](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/6b1fb39bd00ce4424a29d5fd91dd0cf707e53531))
* Add multi-GPU support (AMD VAAPI/AMF, Intel QSV, software) ([6964d2a](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/6964d2ad440d92f92f7786ce0bb43ee0ed179552))
* Add optical drive watcher for ARM container auto-restart ([27bde1f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/27bde1f5a59b5e41423e09666220e47ebf4c694c))
* Add resolution-based preset selection for all GPU backends ([717cb67](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/717cb67ad869b75a60d0fbbc5f60b2e0387054dc))
* add rotating file logging and log viewer API ([84f8c5e](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/84f8c5e4460aac9e00a941142698f45eb9aa433a))
* Add security infrastructure and validation (Phase 1) ([76f93a5](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/76f93a54dd5a8ba733ba2b266488d6698f73c452))
* Add stable optical drive symlink script ([6334854](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/63348548fb8c363de888b8c7181281537c13403f))
* add storage disk usage to /system/stats endpoint ([0b50d57](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/0b50d57555a9650c55c96dc5bc5122f006dc7280))
* enhance ARM notification script with raw path support ([98188ef](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/98188ef18d21a8cf7e40b6bba70a90c3e20d71f3))
* expose version from VERSION file in API and health endpoint ([703465e](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/703465e6cf7c8380ee909c02b02e17f7202215c4))
* forward ARM metadata through webhook to transcoder ([affa688](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/affa688e903400ea8564ce3133be58f7b5c80c0f))
* notify ARM-neu to update submodule on release ([c63ae6c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/c63ae6cd39924c9c9e51a7ed45135238dc61b1d6))
* Use local scratch storage to avoid heavy I/O on NFS ([09c2954](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/09c29540cc6ee687bae61b7ea4c98f7ff0b10918))


### Bug Fixes

* add audio-copy-mask to preserve all audio codecs in passthrough ([cc21c29](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/cc21c29b546e61901fda55129c2d29e86a334c1d))
* add LOG_PATH env var to test conftest to prevent CI failure ([221ef88](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/221ef88130919237475a81e7f7a29c13d5db17d3))
* Add worker 503 guards, graceful shutdown, and import cleanup ([f06e1b9](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/f06e1b97ce7a51b767b468870bcca7b6eb196b72))
* Apprise webhook compatibility and ARM integration config ([83a6b49](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/83a6b495cae5be9b100623c9f61cb135c1780597))
* configure release-please to update VERSION file ([61a132f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/61a132f88fe3ef029fe4633f3042f2b0d14019d3))
* Correct HandBrake preset name to match built-in presets ([eba50a2](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/eba50a21d6bca3a7c0e264a1fabe73e2398bd62a))
* Create render group in Intel and AMD Dockerfiles ([b089af6](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/b089af6b5eaa56609efef80d8302c75d7be3d1b7))
* Increase drive watcher debounce default to 60s ([9520288](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/95202881ce91ceb4cab763cc1757d58b8e9fa14c))
* Install HandBrake from PPA instead of Alpine multi-stage copy ([d3f3322](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d3f33224af53c63fa9691af021d05c02338c6ab9))
* line too long in /system/stats endpoint ([02423b3](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/02423b37a88065bd606cc6e8eb5613223df9cf8b))
* Make audio passthrough source cleanup non-fatal ([a43383e](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/a43383e8fbdacb9b1e628b037193705f280f6c97))
* Pass all application settings through Docker compose environment ([0dbb17f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/0dbb17f1936fffe763526b7e0d3c90f548a16a97))
* Prevent restart loop by checking device visibility in container ([0d76b52](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/0d76b522010109900ea1b9a109a0d147dc9636be))
* Re-resolve source path after stabilization when no files found ([2f50791](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/2f50791c6db9e6ce04c7b5f3c9af8fab1f4e8319))
* remove invalid opus from audio-copy-mask, add mp2 and aac fallback ([757f1ee](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/757f1eebc3e55a27c84560c74b79294f926b197a))
* Replace device visibility check with container uptime check ([4023f52](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/4023f52789ca37d559193a8259cedff100db8064))
* resolve 9 pre-existing test failures in CI ([a061809](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/a0618099743ea8d282c6b9650828c5e86488ded6))
* Resolve ARM subdirectory paths for ripped media ([a28403f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/a28403f10c1d156cbe70bd89a066b510ab6aa3f7))
* resolve flake8 lint errors ([29489ae](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/29489aefa837ba4a5df2dacb156ddc507e065b4a))
* Short-lived DB sessions, progress rate limiting, stream mapping, and disk space checks ([c0e200b](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/c0e200b593721a92fb104f14f4aa8f1f31fd1df5))
* Update Intel Dockerfile for Debian Trixie package names ([50bccb6](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/50bccb6c6b616784a43a8b39ccdab22251d7b6f1))
* Use copy instead of move for audio passthrough ([d5302e5](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d5302e5af3ffcb8dcc81ecbe29a3728f84b7f880))
* use DOCKERHUB_USERNAME secret for image name ([8f01c7c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/8f01c7c5c11624596ea368dd15d1032305af4c43))
* Use extracted media title for job naming and graceful cleanup ([5f44c76](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/5f44c76776908ceb8449db007a2c97009f659ae2))
* use final path from ARM webhook instead of parsing body text ([5b48982](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/5b489829ac4d0cc2d331cb4e8fe74ba0be1dc86d))
* use PAT for release-please so releases trigger publish workflow ([fd72f4b](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/fd72f4b516c2a58c99d47d2932f6e93081fcf535))
* use RELEASE_PAT for parent repo dispatch ([5d16cda](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/5d16cda1160f4c554a7f64459ebce9f89261936b))
* Use Ubuntu universe repo for HandBrake instead of PPA ([912bcef](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/912bcef1b06f178d6d459e251abab503cc0d64c5))

## [0.5.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v0.4.1...v0.5.0) (2026-02-20)


### Features

* forward ARM metadata through webhook to transcoder ([affa688](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/affa688e903400ea8564ce3133be58f7b5c80c0f))

## [0.4.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v0.4.0...v0.4.1) (2026-02-16)


### Bug Fixes

* configure release-please to update VERSION file ([61a132f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/61a132f88fe3ef029fe4633f3042f2b0d14019d3))

## [0.4.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v0.3.0...v0.4.0) (2026-02-16)


### Features

* notify ARM-neu to update submodule on release ([c63ae6c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/c63ae6cd39924c9c9e51a7ed45135238dc61b1d6))


### Bug Fixes

* use PAT for release-please so releases trigger publish workflow ([fd72f4b](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/fd72f4b516c2a58c99d47d2932f6e93081fcf535))
* use RELEASE_PAT for parent repo dispatch ([5d16cda](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/5d16cda1160f4c554a7f64459ebce9f89261936b))

## [0.3.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v0.2.1...v0.3.0) (2026-02-16)


### Features

* add /system/stats endpoint for live CPU, temp, and memory metrics ([9f4326c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/9f4326c5bf4cf0fa0276cd73a37acd82450b7645))
* add storage disk usage to /system/stats endpoint ([0b50d57](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/0b50d57555a9650c55c96dc5bc5122f006dc7280))


### Bug Fixes

* line too long in /system/stats endpoint ([02423b3](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/02423b37a88065bd606cc6e8eb5613223df9cf8b))
* resolve flake8 lint errors ([29489ae](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/29489aefa837ba4a5df2dacb156ddc507e065b4a))

## [0.2.1](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v0.2.0...v0.2.1) (2026-02-16)


### Bug Fixes

* add LOG_PATH env var to test conftest to prevent CI failure ([221ef88](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/221ef88130919237475a81e7f7a29c13d5db17d3))
* resolve 9 pre-existing test failures in CI ([a061809](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/a0618099743ea8d282c6b9650828c5e86488ded6))
* use DOCKERHUB_USERNAME secret for image name ([8f01c7c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/8f01c7c5c11624596ea368dd15d1032305af4c43))

## [0.2.0](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/compare/v0.1.0...v0.2.0) (2026-02-15)


### Features

* Add ARM setup automation script ([c00d34c](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/c00d34c38e8848a3724c9c99ec7a5b2c28fa597d))
* Add audio CD passthrough to music folder ([ee49572](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/ee49572c0ef44c4aacf39c786e8f32ecff27cdf3))
* Add authentication and security improvements ([12f8a35](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/12f8a35ad7839812d639a85e40cd2b3118c520eb))
* Add comprehensive test suite and fix documentation ([e6c9b7a](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/e6c9b7ace7711908242b3bab8601d0a1ba070276))
* add config persistence model and psutil dependency ([39aefd7](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/39aefd7c923cfb7cf412c93d7f7824d80f97f978))
* add GPU auto-detection, config management, and system monitoring ([94db4fa](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/94db4fa42df444f8e71c26a351c390d097461e1d))
* Add media metadata to output folder and file names ([6b1fb39](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/6b1fb39bd00ce4424a29d5fd91dd0cf707e53531))
* Add multi-GPU support (AMD VAAPI/AMF, Intel QSV, software) ([6964d2a](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/6964d2ad440d92f92f7786ce0bb43ee0ed179552))
* Add optical drive watcher for ARM container auto-restart ([27bde1f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/27bde1f5a59b5e41423e09666220e47ebf4c694c))
* Add resolution-based preset selection for all GPU backends ([717cb67](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/717cb67ad869b75a60d0fbbc5f60b2e0387054dc))
* add rotating file logging and log viewer API ([84f8c5e](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/84f8c5e4460aac9e00a941142698f45eb9aa433a))
* Add security infrastructure and validation (Phase 1) ([76f93a5](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/76f93a54dd5a8ba733ba2b266488d6698f73c452))
* Add stable optical drive symlink script ([6334854](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/63348548fb8c363de888b8c7181281537c13403f))
* enhance ARM notification script with raw path support ([98188ef](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/98188ef18d21a8cf7e40b6bba70a90c3e20d71f3))
* Use local scratch storage to avoid heavy I/O on NFS ([09c2954](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/09c29540cc6ee687bae61b7ea4c98f7ff0b10918))


### Bug Fixes

* Add worker 503 guards, graceful shutdown, and import cleanup ([f06e1b9](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/f06e1b97ce7a51b767b468870bcca7b6eb196b72))
* Apprise webhook compatibility and ARM integration config ([83a6b49](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/83a6b495cae5be9b100623c9f61cb135c1780597))
* Correct HandBrake preset name to match built-in presets ([eba50a2](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/eba50a21d6bca3a7c0e264a1fabe73e2398bd62a))
* Create render group in Intel and AMD Dockerfiles ([b089af6](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/b089af6b5eaa56609efef80d8302c75d7be3d1b7))
* Increase drive watcher debounce default to 60s ([9520288](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/95202881ce91ceb4cab763cc1757d58b8e9fa14c))
* Install HandBrake from PPA instead of Alpine multi-stage copy ([d3f3322](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d3f33224af53c63fa9691af021d05c02338c6ab9))
* Make audio passthrough source cleanup non-fatal ([a43383e](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/a43383e8fbdacb9b1e628b037193705f280f6c97))
* Pass all application settings through Docker compose environment ([0dbb17f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/0dbb17f1936fffe763526b7e0d3c90f548a16a97))
* Prevent restart loop by checking device visibility in container ([0d76b52](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/0d76b522010109900ea1b9a109a0d147dc9636be))
* Re-resolve source path after stabilization when no files found ([2f50791](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/2f50791c6db9e6ce04c7b5f3c9af8fab1f4e8319))
* Replace device visibility check with container uptime check ([4023f52](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/4023f52789ca37d559193a8259cedff100db8064))
* Resolve ARM subdirectory paths for ripped media ([a28403f](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/a28403f10c1d156cbe70bd89a066b510ab6aa3f7))
* Short-lived DB sessions, progress rate limiting, stream mapping, and disk space checks ([c0e200b](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/c0e200b593721a92fb104f14f4aa8f1f31fd1df5))
* Update Intel Dockerfile for Debian Trixie package names ([50bccb6](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/50bccb6c6b616784a43a8b39ccdab22251d7b6f1))
* Use copy instead of move for audio passthrough ([d5302e5](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/d5302e5af3ffcb8dcc81ecbe29a3728f84b7f880))
* Use extracted media title for job naming and graceful cleanup ([5f44c76](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/5f44c76776908ceb8449db007a2c97009f659ae2))
* Use Ubuntu universe repo for HandBrake instead of PPA ([912bcef](https://github.com/uprightbass360/automatic-ripping-machine-transcoder/commit/912bcef1b06f178d6d459e251abab503cc0d64c5))

## Changelog
# Breaking change marker
