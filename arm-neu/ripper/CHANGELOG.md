# Changelog

## [19.1.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v19.0.0...v19.1.0) (2026-05-30)


### Features

* **rip:** skip user-disabled tracks on the per-title rip path ([a7ec97c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a7ec97c019b5db39a368ae22388764af9b7aa076))
* **transcode:** skip user-disabled tracks in webhook manifest ([3dda8ad](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3dda8ad4f7f1d2291c89c6eaaed02f6de82fec0c))

## [19.0.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v18.1.0...v19.0.0) (2026-05-26)


### ⚠ BREAKING CHANGES

* **notifications:** The legacy flat-config notification fields (PB_KEY, IFTTT_KEY, IFTTT_EVENT, PO_USER_KEY, PO_APP_KEY, JSON_URL, APPRISE, BASH_SCRIPT, NOTIFY_RIP, NOTIFY_TRANSCODE) are removed. An alembic migration translates existing values into notification_channel rows and drops the columns. Notification channels are now managed via /api/v1/notifications/ and the arm-ui Notifications page.

### Features

* **api:** GET /api/v1/jobs/{id}/metadata returns merged MediaMetadata ([a5c1b8a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a5c1b8a22d83cdd20eb9174676a4f9a344cc2055))
* **identify:** write full MediaMetadata blob alongside Job columns on match ([e5e1792](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e5e1792b930aeab6c598b7b3ccf898954289f3b8))
* **job:** media_metadata_auto/manual columns + merged-read property ([225a835](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/225a83586d66ef44e3cc7cd973465532a39fb486))
* **job:** migration drops legacy poster_url/artist/album triples after backfill ([8b24542](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8b24542249a48d28fcb04b78489f02bd1cccda7d))
* **metadata:** migrate poster_url consumers to media_metadata ([7163ef8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7163ef8ef7fc76612474a9f9e55794b837aff982))
* **metadata:** MusicBrainz adapter returns MediaMetadata (additive) ([4266257](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4266257f942628711c7c88b2649d28180d681131))
* **metadata:** OMDb adapter returns MediaMetadata (additive) ([ea1089c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ea1089cc97eb95c474fdf483904a35710d860091))
* **metadata:** TMDb adapter returns MediaMetadata (additive) ([bb949e1](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/bb949e12c419a3637b1505fa843e725696fc5936))
* **metadata:** TVDB adapter returns MediaMetadata (additive) ([f9bf4ef](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f9bf4ef4259aaae27953d74669e53afb38579790))
* **naming:** derive PATTERN_VARIABLES from arm_contracts.PATTERN_TOKENS ([0327d42](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0327d4290aec0edcf542c8a1fc7eded7a833231e))
* **notifications:** /test accepts channel_id+fields for editor send ([4ae8a0f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4ae8a0fdae9df456a711b88c9e1fc7cc410815c7))
* **notifications:** add NotificationChannel + NotificationOutbox models ([9e3980c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9e3980ce171c0a818352e67ae2f8715c5d300535))
* **notifications:** add per-event default templates + render with overrides ([50f7aaa](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/50f7aaa60643dab39a9a7550ab17b47597af5c58))
* **notifications:** add publish_event producer entry point ([824bab3](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/824bab3658f403ab76f00d229141572f6b9c9f6f))
* **notifications:** alembic migration creating channel + outbox tables ([3f10541](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3f105413f0713869c6973a0b95494dfeb7d89c75))
* **notifications:** apprise channel sender ([3594d5f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3594d5f48a7c7f4b2e597aee6d93c58772604075))
* **notifications:** apprise URL composer for catalog form submissions ([ca8b557](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ca8b55756ce806c811780ca422777b6b35bf291c))
* **notifications:** bash channel sender with timeout ([3b81b3d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3b81b3dffdfefa54cdde70961a522088eb178143))
* **notifications:** channels CRUD + test send + catalog API ([1b95a4d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1b95a4d911e2831fd691a0ac71eac3d5918f7df5))
* **notifications:** compose apprise url server-side on create ([0139fd0](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0139fd0be9aed30d148920578e8cbef00e532f0d))
* **notifications:** data migration + drop legacy config columns ([e96339c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e96339ce58bd9e54fbef0dbd0e7560934eb8c547))
* **notifications:** dispatcher worker with per-row processing ([4811488](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4811488904db51bd028b035b994cd13c02f9e8b1))
* **notifications:** mask private apprise fields on GET ([ba0f142](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ba0f1428566fa8def78c4e17465abd271d14374c))
* **notifications:** merge apprise fields + recompose url on PATCH ([cce3d85](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/cce3d8535fa3d035346082a040ae4a9cb46a9627))
* **notifications:** migration helpers for legacy config translation ([b3bffa5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b3bffa501d1ef4bc26a836141d4e153ea5c79c69))
* **notifications:** outbox enqueue, dequeue, retry, reaper, cleanup ([1d6371b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1d6371bab8020b1b48686d07a45c12ee809126ae))
* **notifications:** persist apprise service_id on create and patch ([2fae289](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2fae2893fb1b63a3fb9c73c825c9fe5869d51fdf))
* **notifications:** publish manual_wait and duplicate_detected events from makemkv ([ab7bf34](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ab7bf3442f115952a094a77d9f4690802e1afa34))
* **notifications:** publish_event at lifecycle sites in arm_ripper ([3aac573](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3aac5735950acb63fdd3cc7e8ffa09ef47790b85))
* **notifications:** service catalog introspected from apprise ([e5eec16](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e5eec169955d8a925fb5009a31902f0ae537aa38))
* **notifications:** start dispatcher in FastAPI lifespan ([fa7468e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/fa7468ebe709c3d3ed03852deffcec63893fb2ac))
* **notifications:** test-send endpoint for unsaved channel config ([8e86e01](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8e86e01c6531897b0f2d9559258ee1cb283485a1))
* **notifications:** webhook channel sender with HMAC-SHA256 ([d3b986a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d3b986a9541117f878749ed99fd4cc6451932f31))
* **notifications:** wire outbox cleanup into existing periodic hook ([84f5acd](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/84f5acd75e2ba80a32e7c39272cdb9592e4e7edd))


### Bug Fixes

* **jobs:** project media_metadata in list + drive-summary wire shapes ([4a39d66](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4a39d66d81348e85f494bb2401e9977f155346bd))
* **jobs:** project media_metadata into wire shape ([19680dd](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/19680dd0608d615a7db72154c79884fa3bc38240))
* **music:** write MediaMetadata blob from MusicBrainz path ([d18fede](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d18fede73ecc8e6748da4bd80d65029ed53e1dbb))
* **notifications:** clear Sonar http-protocol hotspot in JSON_URL rewrite ([1a351a6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1a351a662bd7f2de25d5cdae10cab2e9042675e5))
* **notifications:** compose apprise url on unsaved-test (Add-form Send test) ([1961ea9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1961ea9943e7703422d14ab9673d3881e36724a3))
* **notifications:** exclude bash from the unsaved-config test endpoint ([d1b4fd7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d1b4fd759dbd7e9c7d74d77908ec541b487d8d3d))
* **notifications:** harden dispatcher against bash retry and commit errors ([2dc2b56](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2dc2b56ff1a41d2f9ad58091b43fc1bc4fb14bd8))
* **notifications:** make async tests CI-safe and clear Sonar hotspot ([23d5914](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/23d5914ea89da4ba9154865781f55a26723908ea))
* **notifications:** put codeql ssrf suppression on the flagged line ([01f93dc](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/01f93dc1b42262d35095be67cc34123733b31436))
* **notifications:** SSRF guard + drop exception text on unsaved test ([7eaf423](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7eaf423bb4facd332da31ec1fc5916b7206f3d61))
* **notifications:** suppress modeled-out SSRF, stop leaking error text ([6ef678f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6ef678fdfdbc95246cb75f236cdbabaa4f4b7cec))
* **notifications:** suppress SSRF in codeql config, clear Sonar hotspots ([1123810](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1123810f62e93b46c4a97e4d8b721fa3fe8c8978))
* **test:** move drives/with-jobs test where the client mounts the drives router ([3c7bb9e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3c7bb9eb4296dce0fc3b508f144e5e73a9530a2d))
* **test:** seed required status/disctype on backfill migration test rows ([519dbca](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/519dbcada390b44684f2ae612d0373179086613e))


### Performance Improvements

* **dispatcher:** interruptible tick sleep so test teardown is instant ([2b00510](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2b00510f9bde5a8ee1048baf5f7af5367892a6d8))


### Documentation

* **notifications:** document the typed multi-channel notification system ([f0e7d01](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f0e7d01ceb202adaa06beb2f2d78be98f8c1c5eb))

## [18.1.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v18.0.0...v18.1.0) (2026-05-10)


### Features

* bump components/contracts to 307bef8 ([98958f7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/98958f7be9d06a875453b62596dfcaef7ad71aac))
* **folder:** drop {success: true, ...} envelope from folder endpoints ([8a41fa8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8a41fa82b41428b76f28c4002e48e0a8d0d29c90))
* **metadata:** unify key-test endpoints under /metadata/test-key ([c8673a2](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c8673a2348e2da138ab42d53f3059da5f78d914a))
* **progress:** /jobs/{id}/progress-state surfaces copy progress ([f5bc4a4](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f5bc4a48b82840315f4aee3dc198b9ca74c1a5ec))
* **progress:** add get_copy_progress reader ([5806be3](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5806be378268b1c0e8b7d400de35de1947ca7ef7))
* **rsync:** add run_rsync_sync helper with progress streaming ([981d172](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/981d1727399ac06c0845f4dee73717de3563d5da))


### Bug Fixes

* **import:** deselect-delete must skip filenames a kept track now claims ([ba36fd5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ba36fd50559f728030daaf1922ae7f4ef8d57192))
* **rsync:** drain stderr concurrently to avoid pipe-buffer deadlock ([0ece454](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0ece4542f2d48eb796e5cc0e28f54ff702e89b7c))

## [18.0.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v17.5.4...v18.0.0) (2026-05-08)


### ⚠ BREAKING CHANGES

* **routing:** webhook output_path for unidentified video discs flips from MOVIES_SUBDIR/<title> to UNIDENTIFIED_SUBDIR/<title>. Operators with rips already landed under Movies/ from 18.0.0-rc need to relocate them manually if desired.
* webhook payloads no longer include folder_name or path; consumers must read input_path/output_path. This commit pairs with the contracts v3.0.0 submodule bump (auto-bump 37d3fd4) and requires arm-transcoder >= the matching breaking release on the same deploy window.
* contracts has breaking commits in this bump. Review the commit list above and verify consumer code still compiles before merging. release-please will cut a major consumer release when this PR lands.

### Features

* bump components/contracts to 37d3fd4 ([0dc39fd](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0dc39fda3531fd41c3f2c0c834690e113531a668))
* **compose:** add opt-in NFS-readiness overlay ([0e5daf9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0e5daf91c410a4a772479b976b072c3cc8c9fb06))
* **compose:** ARM_COMPLETED_PATH bind + configuration reference doc ([f6c49bb](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f6c49bb0a964fde764e48bd9a6135dd0fbdd9c8e))
* **compose:** pass MOVIES_SUBDIR/TV_SUBDIR/AUDIO_SUBDIR/UNIDENTIFIED_SUBDIR to ripper ([d3a0e40](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d3a0e402932a7fb1f5fbfd4888821f398a9ed89a))
* **compose:** pass type_subfolder env vars in ripper-only compose ([3271104](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3271104a718813dfc5e03539f86d66577bc08f01))
* **compose:** remote-transcoder parity with [#339](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/339) ([7de4c67](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7de4c6778f9f698c0be2011b09dc76d829cb55f6))
* **config:** add MOVIES_SUBDIR/TV_SUBDIR/AUDIO_SUBDIR/UNIDENTIFIED_SUBDIR yaml keys ([3883843](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3883843adc206fd342dffd9b8d2145e02a1d05b4))
* **entrypoint:** flow MOVIES_SUBDIR/TV_SUBDIR/AUDIO_SUBDIR/UNIDENTIFIED_SUBDIR env to arm.yaml ([497c9ee](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/497c9eedcc658a8cd8548ddfdb60d0e48c456c56))
* **file_browser:** tag entries with kind and importable flags ([a55f301](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a55f3012f6f2568c8b662ecfe17da952aceb1761))
* **iso-import:** /api/v1/jobs/iso/{scan,create} endpoints + ripper ([bfbc38f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/bfbc38f8e506e496a7968a12b34d1d5e369c61c1))
* **iso-import:** SourceType.iso plumbing in Job model + migration ([6840047](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/68400473e5068af5b1423610fa173866140ac5de))
* **job-model:** type_subfolder reads from arm.yaml ([c12385d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c12385d1229bf9d52df512b8b60f2d0c43eeb470))
* switch webhook to input_path/output_path ([df2b559](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/df2b55936a577300bf2d784c28d9bd0a10a602a2))


### Bug Fixes

* **drives:** silence repeating warning for already-cleaned phantom rows ([5f5ebc8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5f5ebc8c27dfde8299c9f70431a19a070e540849))
* **import:** honor track.process=False on folder + ISO rips ([03497eb](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/03497eb2176abf425fbf3367e15414695b570642))
* **iso:** address CodeQL findings on iso scan endpoints ([c734db3](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c734db3a0ca292ba0404062bb55647ebb0175836))
* **iso:** spawn rip thread when starting ISO job from review ([23691c8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/23691c82ba57945dd38cd0c4acfdb1e45c22ee21))
* **prescan:** skip mdisc resolution for ISO imports ([fc42719](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/fc427190e65dffeb3e80c112565c18c946f90985))
* **routing:** per-track output_path defaults to MOVIES_SUBDIR for video discs ([c5efdaf](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c5efdaf0343515439c90b35d1b602e5a2ebab440))
* **routing:** unidentified DVD/Blu-ray/UHD rips default to MOVIES_SUBDIR ([723a7f6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/723a7f6d717abb4959a1dfc79e05795e6ef4eddb))
* **routing:** unidentified video discs route to UNIDENTIFIED_SUBDIR ([f8651c6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f8651c685b28ca62af84408edc534e5bcbc6c63a))

## [17.5.4](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v17.5.3...v17.5.4) (2026-05-04)


### Bug Fixes

* **system/restart:** graceful shutdown via background SIGTERM ([865c45c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/865c45c1a6bf8d18fca877ed444e2bb7cb79aab2))

## [17.5.3](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v17.5.2...v17.5.3) (2026-05-04)


### Bug Fixes

* **jobs:** include track_counts in /jobs/paginated response ([aa46443](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/aa46443b51e33183c40c5a1609474da91f8c26df))

## [17.5.2](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v17.5.1...v17.5.2) (2026-05-04)


### Bug Fixes

* **setup:** exclude stale rows from drive_count ([7a97895](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7a978953e042bffa7d19db043b057c50f5add253))

## [17.5.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v17.5.0...v17.5.1) (2026-05-04)


### Bug Fixes

* **setup:** unwrap alembic Row in db_version, returning version_num string ([6eae127](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6eae1272fac8e3710a62a2c7b67da58f0750ea4b))

## [17.5.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v17.4.0...v17.5.0) (2026-05-03)


### Features

* add ExpectedTitle ORM model with Job relationship ([8203e34](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8203e34337e479aac0ea270c3685f058b3d36330))
* add parse_runtime helper for metadata-provider runtime strings ([29ec1d4](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/29ec1d407c6cc9135d57138db38e2c8334166a41))
* add Track.skip_reason column for filter-decision tracking ([92e79f2](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/92e79f256c9ebd8c30942e60326aac9a444bdc77))
* alembic migration for expected_title table ([3aedc6d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3aedc6d275f57784c0e21882df70c937817492fc))
* **config:** add get_db_uri() DSN selection helper ([be59622](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/be5962251d39178a6c63b59e89b54e466e995c6b))
* empty-rip jobs fail with structured skip_reason breakdown ([9c72c00](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9c72c00041c7f4040be6005c653d378336ec26c0))
* **enums:** add arm/enums.py with RipMethod and AudioTitleSource ([1e52690](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1e526908f1181540bad3d50fd84006f18e305417))
* folder prescan auto-disable sets skip_reason='too_short' ([1219ca7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1219ca79ceb2e30ca0f75ea5424ab16e060c926c))
* manual UI track toggle writes user_disabled skip_reason ([b93d147](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b93d14740718a35d5944ae0cc6f95fa73118dc50))
* **migration:** backfill old JobState wire strings; extend TrackStatus ([e26e009](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e26e009c184467c165adb0a209f11011b8ec4381))
* **migration:** convert 5 columns to db.Enum + split track status ([6181c10](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6181c10ffbfbe4ac9800194a444e5954753cc1d4))
* parse MakeMKV skip messages and persist skip_reason in all-tracks mode ([d294f8a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d294f8a8e00b48e72cb61bc5e1277505a07132c1))
* persist TVDB episode list as ExpectedTitle rows ([5002508](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/50025081562b9d750c1a4eaef8538bcdc94507ff))
* process_single_tracks persists too_short/too_long skip_reason ([a60c42b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a60c42b8f4a9699b7a60d0360b2560040b54df9e))
* retain runtime_seconds in OMDb/TMDb normalizers ([3d82dff](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3d82dfff4a73851d955e225238c0c214544343a1))
* serialize expected_titles on job detail endpoint ([641ef16](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/641ef1625b328a66f3b4843cf8a690c08d7c5921))
* serialize process and skip_reason on track detail ([6af8534](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6af853484b8e9a8742d394297508891a70ca1985))
* write ExpectedTitle row on successful movie identification ([25dafd4](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/25dafd4e2da17ef6166eddc305b9811b0363133c))


### Bug Fixes

* avoid sqlite side effects in version probe; mask DSN in boot log ([a2dfac7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a2dfac7b926726cb7ee85efb85aa9ab90ac777a1))
* guard movie ExpectedTitle write to type=='movie' only ([e225033](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e2250338a45ab52ea2e447dd434ed76431384751))
* **makemkv:** mark all-tracks rip candidates as process=True ([8577667](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/85776677989c8e359b664ca26e46d08297a6fdc0))
* **migration+sweep:** backfill Job.status NULLs; finish bare-string sweep ([b635ceb](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b635ceb2dfa17cbbd6e3feb3b30a6ff3e822f6da))
* **migration:** remap legacy track.status='fail' rows to 'failed' ([c82f927](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c82f927184162296dc897c5d06e06055cfc967f1))
* **music:** all music-failure paths use _update_music_tracks_ripped_only ([fbebacc](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/fbebacc04c0a5383faf46b11d95ce4e2e661259e))
* parse_runtime rejects bool inputs (int subclass guard) ([01c4341](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/01c4341fd674b0f25c6d26454d4b0cc8f8840653))
* **prescan:** mark too-short/too-long tracks as filtered before review ([f2f1003](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f2f10031c2b27650815e2602f4dbc71f393a99c2))
* **security:** mask DSN password in /api/v1/system/version response ([935dd8d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/935dd8da2e40b97b545beb566ea6b4b4104f3caf))
* **test:** use relative path so migration-module test runs in CI ([d656309](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d6563098279b7125a3cb9937d3593145176fee73))
* **track:** default process=None on init so review widget renders rippable ([1ee6013](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1ee6013570e2d68732469ccd25e7475d95922b61))

## [17.4.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v17.3.0...v17.4.0) (2026-04-30)


### Features

* bump components/contracts to 230a4a8 ([5f78d1b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5f78d1bc95f05c0afca5f95db41938c8d8bf0dfc))


### Bug Fixes

* bump components/contracts to 67eba7b for rip_progress float fix ([97a376d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/97a376d229b8dfc41a5f4ba581e11acfd1ecdbb7))
* **progress:** hold rip percentage during inter-title PRGT transitions ([8f8a4c5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8f8a4c512922ddc736c11a8fbcb7d44f598bbcf5))

## [17.3.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v17.2.0...v17.3.0) (2026-04-29)


### Features

* **api:** add version module and require_api_version dependency ([fac7fe3](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/fac7fe35cdb254a5b96e4d53b31fed986fd87c51))
* **api:** adopt Job/Track/JobSummary/JobProgressState contracts ([cde13ca](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/cde13ca718ba1972d12cad23f4193ac887e4c02a))
* **api:** require_api_version dependency on transcode-callback receiver ([c48a059](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c48a059d274862a78b334a2ad79d80e91c4e8313))
* bump components/contracts to ece12c0 ([ec872e2](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ec872e233d105039f11d404ee9d70672344e1942))
* logs API + realtime progress in progress-state ([3e9eb58](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3e9eb58d84b12eb49508e810d61299508d250646))
* **version:** stamp build identity into VERSION at image-build time ([e102963](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e1029638fee0092499880567ca764c45356cdcae))


### Bug Fixes

* **logs:** defend log_parser against polynomial ReDoS ([6b696d5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6b696d5e13dddffc64639e9de652f2d05836a58d))
* **preflight:** stop blocking event loop in MakeMKV key check ([28a2597](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/28a259709f5ab18d8dc0f4cded2f8012b4af3bb0))

## [17.2.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v17.1.0...v17.2.0) (2026-04-28)


### Features

* decouple arm-ui from ripper-side bind mounts ([1106e9b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1106e9b950e5850acacc6fc26974ee089444720f))

## [17.1.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v17.0.0...v17.1.0) (2026-04-26)


### Features

* adopt contracts WebhookPayload + TranscodeCallbackPayload ([0298283](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0298283ece7cfe419b3858690207689c9ea5e69d))

## [17.0.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v16.3.1...v17.0.0) (2026-04-26)


### ⚠ BREAKING CHANGES

* **api:** The published docker-compose.yml no longer mounts the ripper SQLite database into the arm-ui container, and removes the ARM_UI_ARM_DB_PATH environment variable. Operators running an arm-ui image older than the matching Phase 2a release (which still tries to read the SQLite file directly) will see the UI fall back to "DB unavailable" until upgraded. Bump arm-ui to the Phase 2a release at the same time as this ripper release. The ARM_UI_ARM_DB_PATH env var is now ignored and can be removed from any user-overridden compose / .env files.
* **api:** GET /api/v1/jobs/active and GET /api/v1/jobs/{id}/detail now return track_counts.{total,ripped} computed over the *rippable* track subset (enabled, above MINLENGTH for video discs) rather than raw row counts. The JSON shape is unchanged; the numeric values will be lower for any job that has disabled tracks or video tracks under MINLENGTH. Clients that displayed "ripped X of Y" will see Y shrink to match what the UI was already showing via its own DB-side computation. No API migration is required - this fixes a long-standing ripper/UI divergence.

### Features

* **api:** drop arm-db UI mount; finish API surface for UI Phase 2a ([902b679](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/902b6790ad39f69590460e4a3e56dc1062f7a61e))
* **api:** rebase /jobs/active and /jobs/{id}/detail track_counts on rippable subset ([f286768](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f2867684665e6702c2b7b0a4124ac20ebfcad1dc))

## [16.3.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v16.3.0...v16.3.1) (2026-04-25)


### Bug Fixes

* **compose:** persist UI image cache across container restarts ([615a3d7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/615a3d7dac94acebaa795ea736e1f30a4c2fabd7))

## [16.3.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v16.2.0...v16.3.0) (2026-04-25)


### Features

* port upstream enhancements (imdb_id naming var, UDF stale-handle fix) ([b07daea](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b07daeac060ac428ae5b5efa9b82e1f73e28633f))


### Bug Fixes

* **api:** clean DB session on the worker thread to stop pool leak ([ce5a406](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ce5a406ad9fa6245cf08125b18215c3869fe2ec5))

## [16.2.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v16.1.0...v16.2.0) (2026-04-24)


### Features

* **deploy:** add docker-compose.ripper-only.yml (ARM+UI, no transcoder) ([adfea8f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/adfea8fc9e1013a2ebc1ce27243b524f916fad9f))
* **setup:** force-empty TRANSCODER_URL when ARM_TRANSCODER_ENABLED=false ([b0b2751](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b0b27513085e85f6e3593f016bdc1c9202a33e06))

## [16.1.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v16.0.1...v16.1.0) (2026-04-23)


### Features

* add arm-contracts as components/contracts submodule ([bb753ea](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/bb753eae6fa6ba23f9900c6d95ce9ed6a151cec7))
* validate PATCH /transcode-config via TranscodeJobConfig ([e88a840](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e88a8402f0dabf1922c13fb38ce193a26a1262a5))


### Bug Fixes

* **webhook:** drop corrupt transcode_overrides rather than sending ([30d6838](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/30d683844699aed7a48e930417e554a251b1fc1a))

## [16.0.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v16.0.0...v16.0.1) (2026-04-22)


### Bug Fixes

* validate preset_slug format at ARM boundary ([21ad4a3](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/21ad4a37225492c4f450aaf0475f616f08794162))

## [16.0.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v15.5.0...v16.0.0) (2026-04-21)


### ⚠ BREAKING CHANGES

* TRANSCODE_OVERRIDE_KEYS changed from flat fields (video_encoder, video_quality, handbrake_preset, etc.) to preset_slug + overrides dict. SKIP_TRANSCODE replaces TRANSCODER_URL empty-check as the control for whether jobs are transcoded.

### Features

* add {show} and {episode_name} naming pattern variables ([a6c2f9a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a6c2f9a4f006013de0f06213ef30b44e7c68a105))
* add force-complete endpoint to mark stuck jobs as success ([e5ee173](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e5ee173ada9f5a3bbff27c8af41b7acbb8806cc0))
* add SKIP_TRANSCODE config default to arm.yaml templates ([b9c8066](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b9c80662fbde17c6041174cd27650b5dd23374c5))
* add skip-and-finalize endpoint for stuck transcode jobs ([0647f48](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0647f48948c658935ebfba36b1d455eb5b70c30e))
* breaking change - preset-based transcode system replaces flat config ([b258786](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b258786be1de59216eb3b6a62fa0bfe8a4ea6e3f))
* **migration:** drop legacy transcode_overrides shapes on upgrade ([c7abbef](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c7abbefb133c8146199f9c3006b1668bbe5fba03))
* replace flat transcode override keys with preset-based shape ([b21ab60](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b21ab60ffd5c1a3589333cb1bd399185a96ca06f))
* send X-Api-Version: 2 on transcoder webhook POST ([c1261ba](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c1261bad00453cd76eac183cc4fcbcff9d94485f))
* use SKIP_TRANSCODE as source of truth for transcoder handoff ([0d5ffe7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0d5ffe712dbb6c3ade70fca9db164115f250e7ea))


### Bug Fixes

* _post_rip_handoff writes TRANSCODE_WAITING and FAILURE ([693087c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/693087c293bd2bba86b9d0de8cabb9d8c899b4ec))
* chown /home/arm after usermod to fix non-default UID startup ([d9baafd](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d9baafd5565f26eef7503e61d52197f6bf005df2))
* remove main.py dual-writer that clobbered SKIP_TRANSCODE success ([b9f4b3a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b9f4b3a3ce13f5bc97ed7344f7ac3f4f1c070000))
* **security:** avoid leaking exception details in skip-and-finalize response ([f682168](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f68216838ddc9909dfef8b1e21a47c9cb2e794c4))
* skip-and-finalize rejects non-waiting states ([9af9ff2](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9af9ff27a29d5c171cbffb3c740fc81ed198f544))
* transcoder_notify returns bool so FAILURE path is reachable ([6094d01](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6094d0189d5642b85513a2c96e64d13a7cf8370e))

## [15.5.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v15.4.3...v15.5.0) (2026-04-15)


### Features

* add force parameter to drives/rescan endpoint ([b2555e1](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b2555e164b97cc136a2810883555379020581143))

## [15.4.3](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v15.4.2...v15.4.3) (2026-04-13)


### Bug Fixes

* detect disc type from filesystem when udev properties unavailable ([f5c0a5d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f5c0a5d24dcb9f17a77435a9d2f9b6d421399bcc))

## [15.4.2](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v15.4.1...v15.4.2) (2026-04-13)


### Bug Fixes

* add faulthandler + heartbeat instrumentation for silent rip deaths ([c322340](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c322340230a44a29ffbe6882f25f5c4cdb4f5ba8))
* bake udev.conf into image + env var override at runtime ([1c9a7f9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1c9a7f980eb53bcf0ecc33ce26696e8f96a0ad7c))
* increase udev event_timeout to prevent SIGKILL of rip processes ([1e9d5a9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1e9d5a9705a6960a65153796940d56b03b1e1e1f))
* make udev event_timeout configurable via UDEV_EVENT_TIMEOUT env var ([019ccfb](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/019ccfbf8865608fcfacdcc535ea7176ed0e988b))

## [15.4.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v15.4.0...v15.4.1) (2026-04-13)


### Bug Fixes

* isolate makemkvcon in own process group + ignore SIGPIPE ([6f39e0d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6f39e0d66f47b8ae5eef598c93dfd7b7b5342ca7))

## [15.4.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v15.3.1...v15.4.0) (2026-04-13)


### Features

* add CD_RIP_TIMEOUT to kill stalled cdparanoia rips ([298f0d5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/298f0d5fb56bbbcec96aac9376d9d926711b842a))


### Bug Fixes

* add disc_number to MusicBrainz detail tracks for multi-disc filtering ([79f8f23](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/79f8f233c3e3db54a37f9cc3c6fa4cbb82df7eb9))
* clean up stale abcde workdirs to prevent resuming crashed rips ([fb6e3aa](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/fb6e3aac868d67829f53c7f56d6426f9a9137db6))
* handle mock stdout in CD_RIP_TIMEOUT select(), update test assertions ([a8ea9d6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a8ea9d65475bb4428bf365de511294977d385864))
* only mark CD tracks as ripped after tagging, not during encoding ([9cdcff2](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9cdcff22017bde6bb2db5d6089c8024f4fb046e1))
* place m3u playlist inside album folder instead of music root ([6b1aaab](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6b1aaaba567af34de7f4b8b0d84bd0fff871c811))
* re-read udev after mount failure to detect disc type ([7291e1b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7291e1be6c81f7922772f6608e847ef329186882))
* trigger rescan after tray close to detect inserted disc ([cf1e6b0](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/cf1e6b0934604fd7efc7830ada9fd2b898f100e0))
* truncate stale log files when job ID is reused ([888a8f4](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/888a8f4b053d66cdef66e05e8983ccdffe7037ac))

## [15.3.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v15.3.0...v15.3.1) (2026-04-11)


### Bug Fixes

* prevent silent ripper death during MakeMKV file write ([ea7d121](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ea7d121ac3628ce26abe0339b9704e0db303d344))

## [15.3.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v15.2.3...v15.3.0) (2026-04-11)


### Features

* expose read-only mount status in file browser API ([d7754f7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d7754f78fc0f8c903d8e992096d36cf8289f9967))


### Bug Fixes

* match OMDb results against expanded title, not raw disc label ([2280fe3](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2280fe368366b76c9881c0d5bc6216a3e27c9eb4))

## [15.2.3](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v15.2.2...v15.2.3) (2026-04-11)


### Bug Fixes

* enable FLAC encoding defaults and add DVD poster fallback ([6b49c52](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6b49c52af88049a0ead45e3c549320819cbd51c3))
* enable FLAC encoding defaults in abcde config ([80ba4ab](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/80ba4ab1460140f837c10c1f4f67fe68f08a43f2))
* fetch poster from OMDb/TMDb when CRC64 record has none ([542f258](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/542f2581509ced391729086d7722a62977c00a29))

## [15.2.2](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v15.2.1...v15.2.2) (2026-04-10)


### Bug Fixes

* skip writability check for read-only media/transcode mount ([8bdf193](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8bdf193db0022773970ccabbca4075919562a1a2))

## [15.2.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v15.2.0...v15.2.1) (2026-04-10)


### Bug Fixes

* reset manual_start flag after wait loop exits ([003af25](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/003af255e2c618a61bc0d6ca97095dfbdbfcb9b6))

## [15.2.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v15.1.0...v15.2.0) (2026-04-10)


### Features

* add RetrySession for automatic SQLite BUSY retry on all commits ([9996639](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9996639474c1ed7d892c32fb581b2e4b865a933b))


### Bug Fixes

* disable pysqlite transaction management for BEGIN IMMEDIATE ([a7cc73b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a7cc73b7b0ca8ba94e72b1c35f3043b99b56800f))
* mark integration tests so CI skips them ([aa77ff5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/aa77ff505400bc2a5f6cf1e7a32bea09a6c4dff7))
* preserve dirty state across RetrySession rollback+retry ([fe3f019](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/fe3f019fcd7c2a75b695549ac5035b48b95b961c))
* use BEGIN IMMEDIATE to prevent transaction upgrade deadlocks ([60cec7d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/60cec7d1b76bfeb59ad5598e653376cddc3cac2e))


### Reverts

* remove BEGIN IMMEDIATE - blocks reads during long writes ([d3edb7a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d3edb7abd71ec6b41aa90683bd20b588bf107297))

## [15.1.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v15.0.0...v15.1.0) (2026-04-09)


### Features

* add global defaults for prescan cache, retries, and disc enum timeout ([1077ccb](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1077ccbb7c448310c256d0032705642a0e072290))
* add per-drive prescan settings columns and migration ([b4c23c2](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b4c23c259d1d6b31e2eb0ae44f49ca8bc6c8cde9))
* add POST /jobs/{id}/tracks/auto-number endpoint ([b1f5cc3](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b1f5cc3419294917173ea668ab7fb9089a80eb0c))
* async API safety - prevent worker blocking and fix thread races ([e3c6f43](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e3c6f43ed3a3a6cf2d2b8b41cb9c091eb13de557))
* auto-number episodes on series discs when TVDB matching unavailable ([6bd4778](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6bd477840d4cf77fd366154bdaffbb0829d776a0))
* comprehensive abcde/cdparanoia output classifier ([1641579](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/16415794ce2e410430ebe95006d0ac5f6d8d759d))
* extend drive API with prescan settings serialization and validation ([0a20c0c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0a20c0c01e09e2e80d96af133e993c4e80e70cac))
* mark tracks ripped in real-time during MakeMKV rip ([b3f758c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b3f758c22979765f73351da2b551f8663fd6e74e))
* parameterize prescan cache size and enum timeout (no longer hardcoded) ([0f89492](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0f8949256a7d0621e572f1fd7942b2c43176c40c))
* stream abcde output through structured logging ([1592723](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/15927231d5daa7ef5b0c62b0c1adb519b7cd9f67))
* use per-drive prescan overrides with global fallback in prescan loop ([f65602b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f65602bf688010f6dcf666b795cfd5d0d05c2d68))


### Bug Fixes

* accept explicit paused value in pause endpoint ([31806a4](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/31806a4c4425f1cb2ed72d24b0b2e40a5bb8fe0c))
* add pragma no cover for entry-point lock cleanup ([ec02174](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ec021748ea45ee8ecbe4c2d264ae28d728c54bd6))
* address code review findings ([569b6be](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/569b6beaf2526cb1c9b62d6051a961d63194a77d))
* address code review findings for async-api-safety ([833fd60](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/833fd60fef5d9d15bbb18bcfc699f9e2f3481d4c))
* audio format tests race with background disk_usage_cache subprocess ([427a4df](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/427a4df912b1eac32ff1742d1f409a281f670e36))
* create subdirectories as arm user to avoid root ownership on NFS ([fb5d1cb](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/fb5d1cb6d5c2c853ec1277314ed26c70fcc4e42f))
* detect and break stale per-device lock files ([233c7f9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/233c7f98dcf6fd9ef790730deddb35052983006a))
* handle TVDB API returning null data in resolve_tvdb_id ([7af59c5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7af59c5149498168ad6b22042fc89c84e203174d))
* prevent DB lock on notification from rolling back title update ([97de83a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/97de83aa20a657a5cab96ac0210a6c72d24a98ea))
* regression fixes - session cleanup on executor threads, log format ([4db2608](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4db26087d7c96f0ba058a07123365786818f0f9f))
* remove pipe from exec in wrapper to fix flock release on job completion ([0a33ae9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0a33ae93b71c4ec4c65d3afe63fe6c60060d68c3))
* remove stale per-device lock files on container startup ([208d2dd](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/208d2dd65d8192f6469adb7944788338050dde2f))
* reset wait_start_time when resuming a paused job ([8712dab](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8712dab0f10799c9d65bd1f565fde7b1b09cefe5))
* second review - rollback on timeout, unused import, docstring ([e184148](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e1841483c1672f83f360494afc6af755eb5aed2d))
* set per-drive prescan mock attributes to None in prescan retry test ([2379d26](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2379d26ecdc4b228a8d1928d91fdc58781710e2d))
* use correct enum name MessageID instead of MakeMKVMessageCode ([acdbbf7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/acdbbf73d61db840a48da0be917ae4c58e152855))
* warn on startup when directories are not writable by arm user ([f4dd44d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f4dd44d1790b408a7f508f06a4d7cb36e00b83e0))

## [15.0.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v14.2.0...v15.0.0) (2026-04-06)


### ⚠ BREAKING CHANGES

* Raw rip directories now use job GUID instead of title-based names. The transcoder webhook 'path' field contains a GUID basename instead of a title. Transcoder must treat this field as opaque (already does).

### Features

* add disc_number/disc_total to naming pattern variables ([2c4117c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2c4117c3770d2669448d98eaafc0cb567efc8da2))
* add finalize_output for transcoder-disabled deployments ([e4846b6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e4846b6219441c88323d77a1754c218241c4e6c3))
* add guid column to Job model for GUID-based work paths ([94462a7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/94462a765130916d8e0c58f994af962d9164c3c2))
* add JOB_STATUS_SCANNING group, remove IDENTIFYING from ripping ([92037b4](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/92037b4e236b6f26fcfb7d92516e9a0d3017c3b3))
* add pagination support to metadata search endpoint ([fae85b9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/fae85b9ec8c3099e676e094164fc48f7c5139944))
* add per-drive rip speed setting ([e88f195](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e88f1952075f48420bbbfa961d42e670a942cb16))
* add preflight and preflight/fix API endpoints ([e14a3da](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e14a3dad404bb528dab9afe7bb32ca2f9ad70f91))
* add preflight service with key checks, path ownership, and host path resolution ([406b3b3](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/406b3b38445c54939710c355eaf6d329391a8d84))
* add validate_tvdb_key() for TVDB API key validation ([f07fb47](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f07fb478031f2ab670102c617fcebc1c536f52e8))
* build_raw_path uses GUID instead of title ([4a486a0](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4a486a07d03b48b49781bfff4b654c4ce0813168))
* call finalize_output when transcoder is disabled ([61e116e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/61e116eddcbd72915ee0a32c478c78952f894dfd))
* naming lifecycle cleanup - GUID paths, clean titles, deferred naming ([d7862bf](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d7862bf2fd33eac8b15fa2b64bff0cb6da22a33c))
* orphaned job cleanup service ([e7bed05](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e7bed05078d26808bf68f6df2bfad761f3886bc8))
* pass host path env vars to arm-rippers for preflight host path resolution ([5a72830](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5a72830a40c4994bd612988478c7768236e69ef7))
* run orphaned job cleanup on container startup ([96f0d4a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/96f0d4ab5e0804cff6056d1fac4fb4f115a0d198))
* send notification when orphaned jobs are cleaned up ([17580f3](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/17580f3590406e1405bc9a1344e9bfa9757e346b))
* simplify setup_rawpath - GUID paths eliminate collisions ([f2634e6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f2634e647690c93f8f82d42bc00b9113c508ee50))
* store clean titles without aggressive sanitization ([800a7d8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/800a7d82b5379a58075b43610e6af14084a2c80d))


### Bug Fixes

* address SonarCloud findings ([bccdfbf](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/bccdfbf061d3137ad55f5133bc749a4c4ad94b71))
* bind uvicorn to 0.0.0.0 in Docker, use 127.0.0.1 in healthcheck ([4000258](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4000258d6326369c75bc8de897ca03f201f96ad6))
* collapse consecutive hyphens in clean_for_filename ([7ca38b8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7ca38b812e69fb722f62f5ce25fb639b70f3435b))
* detect UHD Blu-ray by index.bdmv header, not /CERTIFICATE/id.bdmv ([646a0c0](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/646a0c03fda7e1da1b50ea74680b8075148684a4))
* gracefully handle read-only config during startup migration ([9a12848](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9a12848e4e27541a02e673e931f52247c4ee5432))
* mark TRANSCODE_PATH as read-only in preflight path checks ([d901691](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d901691a7e3b7ab415fbc24fd9bc5dae1c83549a))
* mountinfo parser uses root field for bind-mount host paths ([7c5eda9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7c5eda95a8cecd766865b37af37c36e2d6323ace))
* override base image healthcheck in main Dockerfile ([9664ba2](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9664ba23b106b8d74d2179fde7e1ba92200ee29d))
* override HEALTHCHECK directive with longer timeout and start-period ([3d5512f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3d5512f6815cef88d88e5e3f08c86f419bb05087))
* prevent setup wizard flash on transient DB errors ([ec70b7c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ec70b7cc69942e10939814be68e95dbea8f4679e))
* prevent udev startup from hanging container boot ([124beab](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/124beabeb542bae0088bae787ea12d747bc8cbb0))
* refresh job from DB after MusicBrainz update, add year verification logging ([bbf97e7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/bbf97e730596c40acf9e64bacf00a8e537f23ea3))
* remove transcoder_notify from notify() - webhook is a pipeline trigger, not a notification ([c2b2b01](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c2b2b01a1481f8c5445bf8fc0e5bec49c0486a25))
* resolve duplicate Alembic migration ID l7m8n9o0p1q2 ([1e492c0](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1e492c04f8eebcf92e624eb24afcefd4ca519243))
* resolve first-run permission failures and audio CD rip crash ([50649b1](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/50649b147bc7fcdcc578d17218f10f20974aed7f))
* rollback poisoned DB sessions in API middleware ([c378938](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c378938e51d90add233a98689dbffbe274e97bd7))
* strip trailing (YEAR) from API titles to prevent double-year in display ([e9a67c5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e9a67c5a61d840d6249c36280119585661ce55a5))
* update test assertions for search pagination page param ([6157ac8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6157ac8d1fbe229548d13418ba81bf69d0a2b576))
* use hostname -i in healthcheck to avoid 10s DNS delay ([ad273e3](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ad273e3898066a6c44c04e157df7cd95ef93d139))
* use light sanitization for Blu-ray XML titles ([bc273d1](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/bc273d147e4595d08ecaed8ae976a22640a8eba0))
* use sqlalchemy.or_ instead of db.or_ in cross-disc matching ([f68c8d6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f68c8d63c6e1f4252ec03efb69be760b23cee001))
* use TCP connect instead of HTTP for healthcheck to avoid worker starvation ([490d119](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/490d119dd95cb19370a2abd089018655c725f709))

## [14.2.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v14.1.2...v14.2.0) (2026-03-31)


### Features

* add GET /drives and /drives/with-jobs listing endpoints ([339c56c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/339c56c95d6bf8c41c10010175c95a1d706e09cb))
* add GET /jobs/active and /jobs/{id}/detail endpoints ([e1144e1](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e1144e1bb0f81580fadfd153663f9f123bfcf03c))
* add notification list, count, dismiss-all, purge endpoints ([314442c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/314442ccaf89fa69c2218f2d62f5608a2e1f9622))
* add paginated jobs listing and retranscode-info endpoints ([2753c8f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2753c8f634c78b8c2d192778b52a76733eb902c9))


### Bug Fixes

* disk-usage cache subprocess probe SyntaxError breaks path checks ([0c09d8a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0c09d8a51ec66a49c60e46b559f19a089b444946))
* harden naming pattern validation and add missing test coverage ([947f0eb](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/947f0eb765cddec07dd2dc6a6f52c41952c7be67))
* replace deprecated datetime.utcnow() with datetime.now() ([1ae9834](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1ae9834c227be358abe571fd9874c0cbac65eff7))
* use Annotated type hints for FastAPI Query parameters ([6ed7014](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6ed701470ba89b6603a26dbc941a8fad1469528d))

## [14.1.2](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v14.1.1...v14.1.2) (2026-03-30)


### Bug Fixes

* promote key MakeMKV events to INFO, demote rsync progress to DEBUG ([c0c1d59](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c0c1d592fbf3ed1a127f44fde6333db15bbb7a6b))
* protect /system/paths from NFS stalls via cached subprocess probe ([173b41f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/173b41f9b5900ddfebfdda6c33e23f7068ba7e29))

## [14.1.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v14.1.0...v14.1.1) (2026-03-30)


### Bug Fixes

* colon sanitization produces clean spacing in filenames ([6767af3](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6767af34f855ae9ffe1058734077c64bb6e4a233))
* guard against None PID in clean_old_jobs ([1dfa36a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1dfa36a5db41037da634bd7ca0fea5274485c273))
* multi-title movie tracks get per-track folders for Plex compatibility ([a8578dc](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a8578dc57f6dd3b47d50e62510cbc7a274644ca1))

## [14.1.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v14.0.1...v14.1.0) (2026-03-27)


### Features

* add rsync to Docker image for NFS-safe file transfer ([bc6aa52](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/bc6aa524ffda67d526cb0e36bcaf5f92973f6f7b))
* auto-disable tracks shorter than MINLENGTH after prescan ([#152](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/152)) ([160eba5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/160eba5906e004023f83ea14cae3012c5d4b0ac8))
* cached disk usage and rsync copy to prevent NFS stalls ([6a4b6e6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6a4b6e6fd5d86f8aec9768595dd7effa162020a2))
* deterministic track-to-file reconciliation via PRGC messages ([#149](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/149)) ([dfd84d8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/dfd84d8068a663e506f1ae8127f25271de3f11f7))


### Bug Fixes

* convert async def handlers to sync to prevent event loop blocking ([125904a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/125904abf5bd277c09de90622d2d2294a240b0af))
* convert file browser handlers from async to sync to prevent event loop blocking ([6631fb1](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6631fb121e0128382126a13577a2e9ee0bf2db43))
* cross-disc filter excludes re-runs of the same disc number ([#153](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/153)) ([696e720](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/696e7201ecb2155f9fb0a34b04ed1200df4afd56))
* deterministic track reconciliation via prescan track lengths ([#151](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/151)) ([804e3e5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/804e3e53c09084bd7842734ad449ad8e9b12e8eb))
* expect 422 for invalid body (Pydantic validation) ([87405ac](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/87405acd3343b71f2dc08def0226b9a750576c72))
* prevent file loss during scratch-to-shared NFS copy ([#147](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/147)) ([dc35f49](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/dc35f49117b8a2da0144eb983a76c11bed72cfc3))
* remove --minlength from folder imports to preserve track numbering ([#148](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/148)) ([b610625](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b6106259d19735236e92c92f3c7c659413e56e23))
* replace polynomial regex in arm_matcher.py (CodeQL) ([84b9ec4](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/84b9ec4d5b9a60b08c059133dd8b6593a1d56f23))
* replace polynomial regex with literal space to satisfy CodeQL ([70aee04](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/70aee0482f1bc17ebba3c5760157044e525103ae))
* sync track.title when episode_name updated via PATCH ([#145](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/145)) ([1e0a9fc](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1e0a9fcecf423213f7fee8b3352e4a59ec20832b))

## [14.0.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v14.0.0...v14.0.1) (2026-03-26)


### Bug Fixes

* add episode_number and episode_name to track editable fields ([dc1f72a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/dc1f72a36330c78a17ce35f0d47c99fe2a015669))
* commit logfile to DB in rip_folder and add startup log entry ([22b8911](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/22b89111cefd76cbbb49aecdd5f97728c74aac2e))
* create log file handler during prescan so logs are visible in waiting state ([0dee286](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0dee286a65e062ae9202a5bb88267be754fd7fae))
* pass job_id to rip_folder thread to prevent detached session error ([aa832a6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/aa832a6d91703a568a75bb62bb9dc93fc4044a1c))
* persist tvdb_id in match_episodes_for_api regardless of apply mode ([a9a66e9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a9a66e91a7a7e48a0687a983340c02e52eff2223))
* persist tvdb_id in preview mode so full episode dropdown loads on first match ([4644703](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/464470327ffaa8559cf9b7f84d8ae6521c4963c9))
* remove redundant OF|of alternatives with IGNORECASE (SonarCloud) ([7375361](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7375361009ddcb66aaa699f17701c2dc81fc93c6))
* set log handler and root logger to DEBUG so rip logs are captured ([b38a4b7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b38a4b767048a5e8bed0964aefe0907532abd197))
* set logfile on folder import jobs during prescan for UI log display ([6e8dea5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6e8dea526760932ec9d700693f01fb3581742a3f))
* set SQLite busy_timeout to 30s to prevent database locked during rips ([49f45b4](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/49f45b45cb1ed00e94ac4e199a5aab51b8946b1e))
* skip redundant prescan in rip_folder when tracks exist from review ([1bb8219](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1bb8219d847ad7830e6ed427d09110d1837f37dd))
* unmatched series tracks use Track N name instead of fake S01E numbering ([06045d3](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/06045d363ee7bb1e7cb2c26b724a3ac6293d417e))
* update tests for logfile handler and tvdb_id persist changes ([533b1a6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/533b1a6ae6824cc7928a9900fd02f94bf22b0bf6))
* use LOGLEVEL from config for folder rip log handlers instead of hardcoded DEBUG ([a547475](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a54747599d23cf7afa0a33370c267789df23f288))

## [14.0.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v13.7.2...v14.0.0) (2026-03-25)


### Features

* add clear-raw maintenance endpoint ([aed1d90](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/aed1d90464e449af8374e0bcb9569fdc1e2e082b))
* add naming API endpoints and update manifest ([7fe293c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7fe293c8fd5b5d3b3e408eea44ec0cab2a1ace12))
* add naming-preview endpoint returning rendered filenames for all tracks ([3527625](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3527625e38ea73891dbf6963c9aa3c0c0dbc1c2d))
* add season/disc_number/disc_total to folder create and job update APIs ([0c13b86](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0c13b86a2ab3666829feabef23968f01ef337a50))
* always send per-track naming manifest to transcoder ([0723019](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0723019d0eab8488f5630c1c5a1d9e8cb69b5a88))
* auto-enable multi_title when episode matching is applied ([c228fc8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c228fc8a5d268606514cabc13acde040e1c6dff6))
* extract disc_total from 'Disc N of M' patterns in parse_label() ([343e4e1](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/343e4e17734d0aeb237ac94f82a57bafb72e6f67))
* extract disc/season metadata from folder paths via parse_label() ([07bc707](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/07bc707e984a0c014e1d857c0d7fccb1706c8535))
* folder import creates review job, start endpoint dispatches rip_folder ([a5c9e19](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a5c9e195e86afa2c8a7c7e400e6a5e2f4946659d))
* per-job naming overrides and custom filenames ([ba0286f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ba0286f64c84a2a714b1bbe07c4b85efeb5a922a))
* prescan tracks on folder import before entering review state ([a564cab](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a564cab4f1df9ea7f3b587c0825e3db80d648506))
* windowed positional episode matching for multi-disc sets ([d1be086](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d1be086d947eb3f10c0b2e780f4487afc52a61be))


### Bug Fixes

* fallback regex for disc/season extraction from folder names with trailing junk ([7dfdfe7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7dfdfe786704542f0528c4436877138239255dba))
* guard _get_pattern override against non-string values (MagicMock) ([30aab4d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/30aab4d53754360424f6f73a7fe5959789211a59))
* guard logfile check against mock objects in tests ([2615660](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2615660160487a1f605f0dc6ffe8de64bb8adeb9))
* position bias now a weighted factor in episode matching, not just a tiebreaker ([07abea9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/07abea96f98f48ad3bba8fcb1b9ee98ff5a0ad2f))
* prevent DB pool exhaustion by cleaning up scoped session in prescan thread ([8211992](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/82119922754acb5dc5b2ec29839fc18692035638))
* prevent DB pool exhaustion in all background thread entry points ([8f02be1](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8f02be1062bebc2a47a98bb339e9c538447bd785))
* re-order episode matches so track sequence maps to episode sequence ([7c7c4f5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7c7c4f56faca7b50d3fdef437cbeb5c1c245f64f))
* set up per-job log file for folder import rips ([c8fd191](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c8fd1915f9cd091ddd262620ebde5c7826ef423b))

## [13.7.2](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v13.7.1...v13.7.2) (2026-03-23)


### Bug Fixes

* add missing ingress volume mount to remote-transcoder compose ([f6dd1d1](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f6dd1d1e685f6c0d9ff5f4acb6993fa6ee93f391))

## [13.7.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v13.7.0...v13.7.1) (2026-03-23)


### Bug Fixes

* resolve duplicate alembic revision ID j4k5l6m7n8o9 ([9fc3b93](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9fc3b9319a0cba64be31f9b9866575566a592b84))

## [13.7.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v13.6.0...v13.7.0) (2026-03-23)


### Features

* add maintenance REST router with orphan detection and cleanup endpoints ([56e412b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/56e412bd8a1a2b759f7e707309e055d0b36b68a9))
* add maintenance service for orphan detection and cleanup ([3532e67](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3532e67687da6d348c2d3917efaabbbaf67e941f))
* add MakeMKV key check endpoint and expose key status in ripping-enabled ([d1f0fb9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d1f0fb9fa67e1767c447728f9f4a924c6ebc1649))
* add makemkv_key_valid and makemkv_key_checked_at to AppState ([4172cd6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4172cd6f36f1069093c049278eddc5150c9772ac))
* add track-fields PATCH endpoint ([491f71b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/491f71b99087044a9a7e4e7139b1af465e6c0e2c))
* persist MakeMKV key validity to AppState in prep_mkv() ([8b08405](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8b0840564003ca3ef9ecc85258ca412a89d43e92))


### Bug Fixes

* don't expose exception details in setup/complete endpoint ([6f6817e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6f6817ebdd54d885778c23311b97bb121c5d484f))
* prevent path traversal in maintenance delete endpoints ([e90757e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e90757e8bbd0a77c510b9521118c042581dd842d))
* sanitize error messages in maintenance endpoints ([3fd2dca](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3fd2dca9f7e2bdd5114c6ea00b031871e7128c79))

## [13.6.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v13.5.0...v13.6.0) (2026-03-22)


### Features

* add ARM_INGRESS_PATH volume bind for folder import ([ad95d15](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ad95d15d55bf369eb0f67138620fb079227fb8b3))
* add folder import API endpoints (scan and create) ([af2c82b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/af2c82b757688207a790ad67bff3c6381d12840c))
* add folder import fields to Job model with migration and config ([d6fc214](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d6fc21484911d191429ec14c2c12bccac5b01911))
* add folder ripper module for folder import pipeline ([0f7be57](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0f7be57784526a2bd8a5ce414e75ff3dd861124f))
* add folder scan module for disc type detection and metadata extraction ([b2836f5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b2836f5e35f030271331c8b74277bc3559a92ffc))


### Bug Fixes

* create Config record for folder import jobs ([f186803](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f1868036768a12a943d7671e26e527e769ca4e7b))
* handle null logfile in job list and set logfile for folder imports ([cbaba65](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/cbaba65773c844960455200e5167178bbdca61f5))
* move tests to test/ directory for CI coverage pickup ([719f380](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/719f380817f6e25f5025e414ac1bc5c864c2d274))
* replace regex with string operations to eliminate polynomial backtracking ([5db90c0](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5db90c01069cc3e6c684d4b95301d7845a128657))
* resolve CodeQL findings — sanitize error responses and fix regex backtracking ([d3a1960](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d3a1960e55e352d421ad3a2e6ab3649a87801464))
* skip entries with invalid UTF-8 filenames in directory listing ([94cedb6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/94cedb692a2df1172adf5ae735d3fb91980eec7b))
* skip recursive dir size calculation for ingress paths ([74f1780](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/74f1780eb13e40f7628ff65e0153a9a730902362))
* update ripper tests for all-mode MakeMKV extraction ([a913f75](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a913f75474d98f2aaaab57dc19ad7f046658a0b4))
* use MakeMKV 'all' mode for folder imports instead of per-track ([3ec73f0](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3ec73f08ae10045a51c85cf76acb7654eebc00f4))

## [13.5.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v13.4.0...v13.5.0) (2026-03-19)


### Features

* add drive eject/close endpoint, drive_mode PATCH, and job stats ([3d24bb7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3d24bb7de5b018045f1acf24baf630a7269ad38b))

## [13.4.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v13.3.0...v13.4.0) (2026-03-19)


### Features

* add configurable PRESCAN_TIMEOUT setting ([8f5f991](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8f5f9914bb37ca06c1010a2c316170bceb60ec2d))
* auto-initialize database on startup and add setup wizard endpoints ([661f1cf](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/661f1cf699661f8ad7592b6761ac02ff6beb3180))


### Bug Fixes

* migration data check uses job count instead of app_state row ([7723993](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7723993c12e50799886dae4c9c5509e29feddbe9))

## [13.3.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v13.2.0...v13.3.0) (2026-03-16)


### Features

* add themes volume mount to remote-transcoder compose ([f432707](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f432707fde9f5041e991ed69567048c4456732bb))


### Bug Fixes

* add missing transcoder env vars to docker-compose ([ff5210d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ff5210d3f385011a30bc40e96eb29aa4d7707771))

## [13.2.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v13.1.0...v13.2.0) (2026-03-16)


### Features

* add copying and ejecting job statuses ([f97168b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f97168b5e910e0b7649ace0143cf1608f4b67842))
* add themes volume mount for extractable theme system ([6945e25](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6945e259c3b5b7853ab7b6dcac24ed346bd4afee))
* support testing unsaved metadata API keys ([c2a0097](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c2a0097fb27171903ee95f723e62fae7400304b7))

## [13.1.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v13.0.0...v13.1.0) (2026-03-15)


### Features

* add disc_identifier property to LabelInfo ([04545f4](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/04545f4468b02b6b96b96a153bb433ad4cbfd8f1))


### Bug Fixes

* consolidate TV disc label parser onto arm_matcher ([#1605](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1605)) ([bc96516](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/bc9651680dc655bbed6d138ed67dcea02a22513e))
* correct file ownership in setup script ([#1660](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1660)) ([380abfb](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/380abfba74851c30a20cabe2a874e046c1faa625))
* guard against None from yaml.safe_load in config reload ([#1639](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1639)) ([a923649](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a9236498484aca26314c8f5049900ddfcf88df26))
* normalize hyphens and dots as word separators in parse_label ([#60](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/60)) ([30a5611](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/30a5611d313d1be783e381076738f756cc391f6a))
* skip umount when mount fails in save_disc_poster ([#1664](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1664)) ([b85b607](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b85b607627aa51db3f617c469f7b995ee84a481a))
* use tmp_path fixture instead of /tmp in test (SonarCloud S5443) ([0e9e549](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0e9e5498e7faac90f51b09344c809e473347e857))

## [13.0.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v12.0.0...v13.0.0) (2026-03-14)


### ⚠ BREAKING CHANGES

* version alignment for v13 release across all repos
* Built-in transcoding is no longer available. Use the dedicated transcoder service (uprightbass360/arm-transcoder) instead.
* Flask, Werkzeug, WTForms, and Waitress are removed. The API server now uses FastAPI + uvicorn.

### Features

* abcde config editor API, MUSIC_PATH config, sensible transcoder defaults ([2a2e45d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2a2e45db7f8a5e7113bf33c964c15ed7c7bc3bbf))
* add 'identifying' status, rename idle from 'active' to 'ready' ([7e5f532](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7e5f532b4b424af6d01a95c890c28adf72664af4))
* add 4K UHD Blu-ray disc type detection (bluray4k) ([a972582](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a972582dfa8fbdb2192f8531a79552bf8cb238d6))
* add database migration version to system version endpoint ([54c9113](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/54c91131b19e5532213a4035ec39a7c1e5470776))
* add DELETE /api/v1/drives/{drive_id} for stale drive removal ([0e78e51](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0e78e512c4ad8c2f79aec1cb494a32c75638bd30))
* add drive diagnostic endpoint for udev troubleshooting ([e331d5f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e331d5f305cbaec13f68107c1491ec948d2431f2))
* add drive rescan script and API endpoint ([883b4ac](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/883b4ac159716e0f8ea0486bd374a9875363ca5a))
* add drive scan endpoint to trigger disc detection ([fdc4bc9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/fdc4bc9caa192aee284f3879aace6993b1335075))
* add file permissions display and fix-permissions endpoint ([983ba13](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/983ba131c0528f9637812fa22cc42adaeb468043))
* add poster_url to transcoder webhook payload ([8c1ba04](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8c1ba0438e06c05c31582b3cd456e04462093738))
* add seed log files for all dev-data jobs ([ae774ee](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ae774ee39644cab272020c376faa46f5774839b4))
* add structured fields, naming engine, and music metadata enhancements ([08c1b2e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/08c1b2e6c8ace117fd1ffaa23db744cc37aea485))
* add track enabled column, SINGLE_TRACK_VIDEO_TYPES constant, and seed data ([207ba53](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/207ba53a9a83191a0628225990dedd59e863b7f1))
* add TV series season/disc parsing to disc title matcher ([0119c2c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0119c2c8552a8bcac15aedcf7a9e278cb6ffc637))
* add user-settable uhd_capable flag to drives ([4b67675](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4b6767591bf1fe09da9045c49b23d119d9a40952))
* add wait_start_time to Job for accurate countdown timer ([2a19995](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2a19995ebdb2826165b1a0ac712511d1bb3de9ca))
* auto-download community keydb.cfg for MakeMKV Blu-ray decryption ([e35ed23](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e35ed23f3eef2f7f95a3a8cbe947b7680752e43d))
* auto-fill episode and season for per-track naming defaults ([61c0e4c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/61c0e4cc5b4c5d61c918bf17a6ac3c07a41be026))
* auto-generate track filename from naming pattern and revive MAINFEATURE ([a948e35](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a948e3564164fd8d2a6febb58ff6c1d87d3ab88b))
* configurable CD rip speed profile (safe/fast/fastest) ([03f959d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/03f959df83fe4fb6b2974d1211eb8b3b934c9042))
* disc-number-aware TVDB episode matching ([eda350a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/eda350a3390df3b76173c1231064866013b6bcd6))
* file browser API with path-validated CRUD operations ([3d3ad25](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3d3ad2500656521ac93e32cad9ea53ef7d26bd0d))
* harden disc detection chain against retriggering and timeouts ([6131596](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/613159665a71a69d1ba3411e74ed1ed48f0ef70a))
* include DB-registered drives in diagnostic and add drive info ([2dc246f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2dc246fa1602536f6f0c5620db94544a77c261be))
* include episode_runtime in match output for UI delta display ([eda1a1a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/eda1a1abb3a72ccc1c16da360018af9a1b1add09))
* integrate disc title matcher into identification pipeline ([2687b3a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2687b3aaed346f32298e7447ebf3a10927472b3f))
* local SSD scratch for ripping with transfer to shared storage ([8bbe650](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8bbe650a9a248b5dd5aa63238dde73eeb9dd2a93))
* merge upstream logging refactor and exception handling ([ac51ebb](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ac51ebbd1a38186b802a2fc2735cebb69a1d54d6))
* multi-disc config settings, webhook all-tracks, per-track transcode callbacks ([efb495c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/efb495c05fa066fc4c9a1cb0b8199f95e89b6771))
* multi-season TVDB matching with best-season selection ([e585f8a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e585f8a636b958629c60198593a89594bf857d78))
* multi-title disc support ([558e19d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/558e19de852b4cdf410bc57875f9088d4e5febd5))
* multi-title disc support — model + API + webhook ([4f254ff](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4f254ff1177d6f6a3c67750cd0cde8cbfccbda82))
* music track progress polling, disc number support, audio format config ([703545c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/703545cc6bef3366bd0f7a1fa3536f5d0950bbdc))
* native transcoder webhook notification ([3a20175](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3a2017581095270e18bb177b822872a445e56c4c))
* normalize video_type to 'music' for audio CD pipeline ([3e4e597](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3e4e5971af1e5f3c4486b2b82bb74677ff764a81))
* per-disc subfolders for multi-disc music CD rips ([0735bff](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0735bfff723df8fc09db79cdc7989176405c3390))
* per-job pause support in manual wait loop ([aaa66b4](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/aaa66b48bb0bdb76dcf7063613f97346d1968ec0))
* per-job transcode config overrides (ARM side) ([c69e7aa](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c69e7aa0945f850334e0ef540c98ab883ed29875))
* pin HandBrake version, add weekly dependency check ([7ffa4ed](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7ffa4ed75691aafd349a528ae9fde68c4ea3afed))
* port upstream PRs [#1698](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1698), [#1605](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1605), [#1660](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1660) ([a3547e8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a3547e89dd4130af9dcfc0af7fee789324878a4c))
* pre-render naming in webhook so transcoder uses ARM patterns ([923adb4](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/923adb457a0c037a9a0fbcf9c68ac5df62fb39cd))
* pre-scan disc tracks before waiting state for review ([a51a993](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a51a9931f8d7e36a781ab779c3165a43bd58a308))
* publish our own base image, clean up workflows ([5aea491](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5aea4915aec53712fcaa314f167f7df9f1e27aae))
* show recursive folder sizes in file browser listing ([0e8536a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0e8536a38e1d11d9c42785e89bebbb4cbd103000))
* structured logging with structlog ([4a62e02](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4a62e02ee3089a49f20ebd4025c2e7b964945c49))
* TVDB v4 API integration for automatic TV episode matching ([3b11bb9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3b11bb9390dbfc3fae0141d57d219657e208b4c4))


### Bug Fixes

* add drive readiness check before rip phase ([3475bde](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3475bde156557778530a0e14c821f4d7cc5ea758))
* add mount retry with backoff for slow USB optical drives ([8bc5123](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8bc51230dd86c77d5c60b43f07a0e59c5868c9f4))
* add mount retry with backoff for slow USB optical drives ([d8a2e1b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d8a2e1b4fce670c37b0776e7db3bb71e121b6ddd))
* add timeouts to MakeMKV keydb download to prevent startup hangs ([d4ac27b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d4ac27bfac21bcdd08afb951b090cca9101017be))
* address CodeQL alerts with config and generic error messages ([152177b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/152177bb791e78517b1d23040c761e21c5190e65))
* allow NFS/group-based access in startup ownership check ([aa12cb5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/aa12cb54bf43914e660a5233889ee7cbae8fd533))
* allow NFS/group-based access in startup ownership check ([ccd6073](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ccd60735ac275f09916667a7dc8ff92c116f9301))
* always chown subdirs at startup for Docker volume mounts ([0904838](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/090483837c35711d07ccfc039171c52498f3c10e))
* always launch ARM even when disc type is undetected ([9800187](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/98001873064f28ca2c2683774425f1f3389eaf74))
* auto-clean empty output folders from failed rips ([2a31e25](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2a31e25dbeaa970c926651d80f1b2611aa572851))
* auto-migrate database schema on ripper startup ([894dc1f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/894dc1f135c0793e2f3372d5933702f6a0f92b48))
* bind-mount /dev in remote-transcoder compose for MakeMKV access ([f3d93ab](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f3d93abc86b73f3362be6637e80be31bc350becf))
* bind-mount /dev so USB drives survive reconnect in container ([65fb7dd](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/65fb7ddf0449ef6accdc7bdfdbe6246514dfa916))
* bind-mount UI VERSION file in dev compose ([771eba8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/771eba8f4150b9c1f985c9d0d053977374fb2d34))
* break arm.ui import chain to fix CI test collection failure ([dc35772](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/dc357724af654d8af55095041c2fc4ee830fd4ae))
* break CodeQL taint chains for path injection and sensitive logging ([9bf05c5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9bf05c521250170db88b2b44f9661bea742df02b))
* bump Flask-WTF to 1.2.2 for Flask 3.x compatibility ([5462e38](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5462e388f34bae19f4ae6f64c188e3bd2593044b))
* bump itsdangerous and Werkzeug for Flask 3.1.2 compatibility ([adb4dda](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/adb4dda9635beaf1eae991123fa4305dc72fe4a1))
* chain multi-title migration after tv_disc_label migration ([24f7cdf](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/24f7cdf5f7e203fb71219619b936834023d8926c))
* clarify CRC database error message when service is offline ([0d7cecc](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0d7ceccbc05ad89e2fa43efedc8af411fe8f3cee))
* clear stale ripping_paused flag on container startup ([3788776](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3788776cfec576edc3c698c2c454118ed542bcfb))
* configure release-please to update VERSION file ([8f8634b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8f8634b80e2b369ac60c14790ae9da9c97b90b7c))
* convert MusicBrainz track length from ms to seconds, rename source ([66006a5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/66006a5e0fce46f5eba2deb9103b4ef508ca3304))
* create missing optical drive device nodes at container startup ([da556c0](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/da556c06135fcf43e0a211cc0422e126b6d89a52))
* data disc with same label silently discarded (upstream [#1651](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1651)) ([72cf674](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/72cf674b1d1e3d8aea529572f1b39377e96c043b))
* delete existing tracks before creating TOC placeholders ([b195ed0](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b195ed001ddbcb849a6a115da41dd9f6189d71e7))
* detect systemd-udevd in drive diagnostic check ([f00154d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f00154d825043850831a91eb11a889f96bb2b1b7))
* dev compose builds from sibling repos, not stale submodules ([c40327a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c40327aa2e3d4e9cc008a509548a4efddef5e697))
* disc identification and rip reliability improvements ([a106880](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a1068808458375ecc146ece3b45332e8297ecbd6))
* docker-compose review fixes across all repos ([768ab0a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/768ab0ac51e9ba1d9d4f0784aa71abb2018a427d))
* drop Python 3.9 from CI matrix (alembic 1.18 requires &gt;=3.10) ([6ffd19b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6ffd19b5609afe209e1c25d44100f7b6ab4e125d))
* drop root privileges before launching ARM ripper ([cdd1b1c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/cdd1b1cb1d3ac1b4e9660e017e3b56d93fe9047c))
* early exit on 0 titles, persist MakeMKV key, improve error messages ([248d1a6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/248d1a6ef0cbef35afc9eda8c968002164c2dae1))
* exclude integration tests from default pytest runs ([61d956f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/61d956f2419be74749526e58f6258ba2745a46d1))
* exit 0 when drive not in /sys/block during rescan ([2a40d46](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2a40d46c3c1ec6a496024cb40eb21d18939a3205))
* extract 4-digit year from OMDb/CRC date ranges in ARM ripper ([3b0703a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3b0703afb1e03ccb3245ff1cc388b2be4d9cdaee))
* fall back to season 1 when TVDB returns no episodes for disc number ([0791b64](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0791b64e17452abb5c49bf4171c663ab08dc9faa))
* force fresh DB read in AppState.get() so pause works across processes ([abbfac8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/abbfac842b7d0ba8569b1dbc059eeeb91f39dd54))
* guard against None mdisc in MakeMKV disc discovery ([#60](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/60)) ([30da652](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/30da652bb90092a552ccb2ddc1a7eb56396cfb4a))
* handle asyncio.run() inside running event loop for TVDB matching ([1bff301](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1bff301ad8cc56246abbf0d6a4947b1df3d0257a))
* handle empty dupe folders at both primary and stage paths ([2dade8b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2dade8b5bb09d9b647d535b3b937ff40520de734))
* handle MusicBrainz rate limiting in integration tests ([8edfa26](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8edfa264790bd7aff53e9ccab25a95814a040e5a))
* handle None track length from MusicBrainz API ([52740a4](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/52740a466aaf61d39bdc2c6b932576f221a390ae))
* handle unknown drive device nodes gracefully in setup() ([db33015](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/db33015f8a87535e0a195713b04707b5ea163ad5))
* include MakeMKV error details in RipperException message ([77d5745](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/77d57455107ae67e70115b2eb79a308835344aac))
* increase pre-scan retry delays for USB drive recovery ([d135c17](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d135c17dda6f1775b01c4add4a9e2f3e72fb280c))
* initialize track status to 'pending' to avoid Unknown display ([eec3d92](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/eec3d9213a211dc848c968913683938ec9e498bd))
* **installer:** correctly detect contrib for bookworm-updates/security across deb822 + mirror lists ([e86f8d9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e86f8d9c1edddde8f24325e236028bc568941185))
* job-level naming reads season_auto and episode_auto ([8bc4f0c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8bc4f0c2785623471d0705abc8827540c3d4a994))
* keydb download runs in background, compose improvements ([a02ec4f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a02ec4f972171612a2e3bbccc407faf76b536836))
* lightweight pre-scan with timeout, no status mutation ([71b1aa9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/71b1aa9b91e4c31852ea7f8ef62afaf8a0aa4067))
* make ARM_UI_TRANSCODER_URL configurable via .env ([5d63035](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5d63035e967da586dd51f057f90bb85ee7a3266c))
* make chown non-fatal for NFS-mounted media directories ([e1f802e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e1f802e7a0b86d944c7dd0c571c799b40eb68dda))
* match correct medium for multi-disc CDs and show TOC tracks early ([3004e0f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3004e0fe5df49a8fcf3766cd11035834c3a38cf1))
* match udev add|change action for container disc detection ([b367eb8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b367eb82d4223181c531c40411cf7e265acf22ba))
* mount single device instead of --all so arm user can mount discs ([8c0550b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8c0550bee3d1bc28e3f2b9d13b17e967321103d7))
* mount transcoder raw volume as rw for source deletion ([cd71aaf](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/cd71aaf737bbff497f34bd007f88e4096ba71cfe))
* move _run_async to separate module to avoid circular import and recursion ([a9a6750](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a9a6750439304d007acf7ed1574df43ae34ec59a))
* move setup_job_log after job persist to fix music CD crash ([0157175](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0157175864c2ec75d8f8a97462a52472c63f7d72))
* music CD progress tracking — broken regex, missing commit, no track data ([4c8b2f6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4c8b2f67a5a99e2f575a3fda174477ee58ba41be))
* only use setuser when wrapper runs as root ([96417b8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/96417b82175086164fa98efc558d15f38efb2e0d))
* pass completed path base to notify script for correct transcoder path ([678fcd3](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/678fcd3b825f5e4d92a5be993281a21021585096))
* poll drive readiness before MakeMKV pre-scan ([b71777a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b71777ade2f9bca1d6dc4c77daeb3170a9b3daa2))
* poll drive readiness before mount to avoid 5-min syscall hang ([69f354f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/69f354fd5c74b082c2feadace36f68172707e2c9))
* protect against drive re-enumeration (sr0→sr1→sr2 cycling) ([fbe6ca6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/fbe6ca653bf6d7fb06ef0da6dad96a947b70253c))
* re-initialize job log after disc identification resolves label ([2e3e8f4](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2e3e8f4cabe5974105f2f85d311a09f343a9e36d))
* release drive association when cleaning abandoned jobs ([440764f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/440764fff4718ee586e8c89ab521cb5c5b68ff78))
* remove :ro from rescan_drive.sh bind-mount ([668c37b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/668c37b912d306d19c1d6c2ee7a885106187573e))
* remove credential logging and stack trace exposure (CodeQL) ([460ca1d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/460ca1d1e9e26dcbbff174206a2ac98211cc8c18))
* remove exception details from API error responses (CodeQL) ([0300e82](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0300e823d252ec909efa1fc6d8476571a14a0540))
* remove unused dependencies from base image ([0812356](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0812356ac9c2afb0b7a74280159fc6380151ea67))
* rename migration to avoid duplicate revision ID ([cc9248f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/cc9248f0ebf91be1c4b8f1ebdc44054ed109c7da))
* replace /tmp paths in tests with /home/arm paths (S5443) ([04511fe](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/04511fe249b494870f55dbe9944696329bc5d108))
* replace PLACEHOLDER values with empty strings in rip method config ([af55799](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/af557994e4a9cd116e5bb26e91883f2956aea621))
* replace upstream URLs with fork URLs across wiki ([797bab9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/797bab942ec869a42a38ffd4e2fa715fa2389aa1))
* resolve all 25 CodeQL security warnings ([9734728](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9734728d6de0112826dd9a646bfc2d6d12272652))
* resolve SonarCloud issues across drives API and tests ([282c92b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/282c92bc1b15ec80a56db40b4801bdfed68cc165))
* resolve SonarCloud LOW maintainability issues ([4b731bb](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4b731bb4a7f089833424b696a92f4bb7e3158c5c))
* resolve SonarCloud Python HIGH issues (S1192, S3776, S5655, S8415) ([d7c74e6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d7c74e6f3551427f4d47fd20e107ee31fbf2cd17))
* resolve SonarCloud Python MEDIUM maintainability issues ([37ff350](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/37ff35095cfb7e0679fa572e3edac3c6c54f8be1))
* resolve SonarCloud quality gate failures ([a004957](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a00495730ee2ce342477d8d6d12e6296e209c0b0))
* resolve SonarCloud reliability bugs (S7493, S1244) ([26ea784](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/26ea78460d66332a21ca543a4fbfd5408352d86f))
* resolve SonarCloud security hotspots and test flakiness ([816ea5e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/816ea5ecbd676807053cdfbf2fb486960160ce09))
* resolve SonarCloud shell MEDIUM maintainability issues ([c2e9902](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c2e99022d4e43a60e5aa48444a28ebfb1169cdf9))
* resolve SonarCloud shell script issues (S7688, S131) ([3120783](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3120783a14380ec9810229e21347242d50c44c3d))
* resolve test failures, add path validation and abcde endpoint tests ([4501140](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/45011400ce4703437435912e2e4778ec31baf557))
* respect global pause even when title_manual is set ([0693e32](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0693e329f34602a055f2dba5af2c7505114c4783))
* restore HandBrake preset list (accidentally emptied) ([feb89ec](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/feb89ecb76644a3854ce759acfbbff95a9616aca))
* restore makemkv-settings named volume definition ([4e5096d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4e5096dfbea3d134103f6c9396bd78d27199bf08))
* restore submodule pointers (auto-managed by CI) ([af36ccf](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/af36ccf5ebd88648d65bd4b61dff1e66d867796b))
* retry drive detection at startup when udev hasn't settled ([2e9cadc](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2e9cadc3afc1fcb5e8015bf6af980643c404f4f1))
* retry pre-scan when MakeMKV fails to open disc after identify ([33f42e6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/33f42e619fc9fff08b3620362380fd84d5ce9222))
* retry pre-scan when MakeMKV returns 0 titles ([4528722](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/452872236228534fe619490480e43fe2cb6a5b3d))
* retry push with rebase in update-submodules workflow ([5fa8f69](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5fa8f695a27c156b27e85254874e640804007d45))
* review issues in matching system ([aa32477](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/aa324779b70e1b3355dfcae9a13144d67ff15850))
* round 2 review issues in matching system ([0d9ad4d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0d9ad4d9dc3284af111b2f70b6b132677fe3f8c3))
* run arm-hb-presets as root to write to volume ([409dbeb](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/409dbebf0b0805acc8b8a4c6396916a9e4770afe))
* run MusicBrainz lookup before manual wait so metadata is available during review ([1374daa](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1374daa36a574bfe578a8fdf84e5fcaba0c31c6d))
* save_disc_poster() leaves disc mounted before MakeMKV (upstream [#1664](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1664)) ([5b58335](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5b583352c6bed69c7ef55c9f5258e96a6d96e8e6))
* scope Docker builds to linux/amd64 only ([f047133](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f0471338d2b2c49dd62e4aa6e7ccc1e957f664e2))
* scope workflow permissions to job level (S8264/S8233) ([d6fb744](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d6fb7444c2a88749a8471cd5e9b67dbdfc66db55))
* send transcoder webhook on rip complete regardless of NOTIFY_RIP ([1e4e0e5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1e4e0e59f2a0653310532fb41f3b4542967db70d))
* set track.ripped=False during scan, True after actual rip ([2742af7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2742af7631fc3004118d847a1219b119eb84d416))
* settings not persisting after config save (upstream [#1639](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1639)) ([7f661b5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7f661b54066d9518b6c33038668b131e81a604ac))
* **settings:** trim whitespace from form values on save ([97214a8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/97214a845e96a3289018d78cf3ed0a0c07161315))
* skip Apprise when no channels configured, improve duplicate log ([bc85939](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/bc85939a7952e25a73df362c8c0dcbd1d9e7daab))
* skip mount for music CDs, set track count, clean up stage init ([284509e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/284509e6e2d9deae7ad51b99c10eba92dc3e8e47))
* skip phantom udev events for non-existent device nodes ([32fcd33](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/32fcd334cc51b18e9da8a8516d0d2d2a017dc849))
* SQLite WAL mode, idempotent migration, and NFS media path ([#76](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/76)) ([8733d9a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8733d9af3e9cddeaccecf1089a44f30f75a5cd56))
* support NFS mounts in host path detection for file browser ([2eb7a40](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2eb7a4070e0258d941656275b47ff9f2afc8608c))
* suppress spurious transcoder webhooks and accept transcoding status callback ([c563c82](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c563c82af4007be6988eb23d3e7b1ad944447b3f))
* tolerate read-only bind-mounts in /opt/arm during startup ([e9e15dc](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e9e15dc819f8530b58b4e71fab0d64786799c4d4))
* track folder uses show name and labels disc fallback correctly ([d86a9ef](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d86a9efad90fbdcef28b8e831976def290931570))
* udev rule ordering, action matching, and lock path ([acd59a7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/acd59a72ae42b295c7d744d193b164c2c194d380))
* update Docker.md default fork from automaticrippingmachine to uprightbass360 ([93fdab7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/93fdab7c8749453ab79d8bc71566304a34733bdc))
* update help URL in main.py to fork repo ([a4eb593](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a4eb5938f67f6bf5ae516dbfc6d3a1b09ad67fb1))
* update issue templates with fork references ([a9a5bf8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a9a5bf8297408f4e674f3b2a98e47f53916c3931))
* update music track ripped/status after abcde completes ([95b6d24](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/95b6d24a7f4c0e09961a3bdfcc791d99e3d44481))
* update put_track test to expect ripped=False ([db38c78](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/db38c78144dd12f9ff88589416e67003612d852c))
* update stale wiki links and fork references ([974d638](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/974d638599159a99d4ef91587469468d3a3b3159))
* update tests for drive readiness check and pre-scan gating ([53e7ff2](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/53e7ff2300e96cb3ddd945a97eb29013cf2b9a70))
* update tests for JobState, music rip, and makemkv changes ([77b4c24](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/77b4c24a56147f442efea522a42ef00374c23521))
* update wiki sidebar, contributing docs for fork ([1d3a85f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1d3a85ff8d62b5ee0d8daa125f7598f04a1651ab))
* USB drive ejection detection, drive locking, and rescan loop ([acb2cc6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/acb2cc6ce34fd635402fc957957235be61c17aac))
* use /search/remoteid/{id} endpoint for TVDB series lookup ([ee65dbf](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ee65dbfe4f32d34626d16c50f2490b5c36af5cf1))
* use direct DB connection for pause check to bypass stale session ([17f16cf](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/17f16cf4b18fbbbf9ffba57d875ac6006803cd34))
* use list() for len(job.tracks) to handle AppenderQuery ([5bd119d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5bd119d6779a1f7acc952f7cf89fadd9c053ef9e))
* use metadata season for TVDB lookup, not disc_number ([94c2e98](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/94c2e9881b5909f3e3871bc6fb7480d318b1d71b))
* use PAT for release-please so releases trigger publish workflow ([c060ec1](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c060ec1c8b9f343fd21245043512bca60a3c32d0))
* use pytest.approx for float comparison (SonarCloud S1244) ([fd8bbab](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/fd8bbab095d545c20d7fcb16a57f5f5bcc90d5cd))
* wait for ARM healthcheck before starting UI ([ad1e200](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ad1e200b53b748a7ece94afa08b34c0e80a0fe39))


### Miscellaneous Chores

* bump version to 12.0.0, update submodules ([fa77786](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/fa777862b3d2265fa684736beb455a0ff9605f57))


### Code Refactoring

* remove HandBrake/FFmpeg transcoding from ARM ([66ec6d6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/66ec6d633a2df447a41822234f2810c305e78aa0))
* replace Flask with FastAPI, delete old UI ([0981e7f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0981e7fcc52d974241efef92b810df1134f80cee))

## [11.0.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.11.0...v11.0.0) (2026-03-09)


### ⚠ BREAKING CHANGES

* Built-in transcoding is no longer available. Use the dedicated transcoder service (uprightbass360/arm-transcoder) instead.
* Flask, Werkzeug, WTForms, and Waitress are removed. The API server now uses FastAPI + uvicorn.

### Features

* add 4K UHD Blu-ray disc type detection (bluray4k) ([a972582](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a972582dfa8fbdb2192f8531a79552bf8cb238d6))
* add AppState model for global ripping pause control ([f4b600c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f4b600ca5b400538cd3a47ff4dbcb956ca1a2c38))
* add Docker Compose orchestration for multi-service deployment ([5200d42](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5200d42d2243f78bedadca864b9c25c139a9761d))
* add drive rescan script and API endpoint ([883b4ac](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/883b4ac159716e0f8ea0486bd374a9875363ca5a))
* Add drives API endpoint and harden drive matching logic ([4720cea](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4720ceab36fc5353630fdd2c7060942fe8445639))
* add file permissions display and fix-permissions endpoint ([983ba13](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/983ba131c0528f9637812fa22cc42adaeb468043))
* add poster_url to transcoder webhook payload ([8c1ba04](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8c1ba0438e06c05c31582b3cd456e04462093738))
* add release bundle workflow to publish deploy zip as release asset ([9c27280](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9c27280f0c9b3b819ceb4cf6065d133b7758fd4d))
* Add REST API layer at /api/v1/ ([3ce2d7b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3ce2d7b7d1182f31ff8ae89d64098e913ac6e849))
* add seed log files for all dev-data jobs ([ae774ee](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ae774ee39644cab272020c376faa46f5774839b4))
* add structured fields, naming engine, and music metadata enhancements ([08c1b2e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/08c1b2e6c8ace117fd1ffaa23db744cc37aea485))
* add system monitoring, ripping toggle, and job start endpoints ([c9c2b23](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c9c2b23add90af72ff2b27b4ee4250ffdd403ee2))
* Add title update, settings, and system info API endpoints ([e3477d6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e3477d64de65d60908c76bf005712b957fb17e38))
* add TV series season/disc parsing to disc title matcher ([0119c2c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0119c2c8552a8bcac15aedcf7a9e278cb6ffc637))
* add user-settable uhd_capable flag to drives ([4b67675](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4b6767591bf1fe09da9045c49b23d119d9a40952))
* auto-download community keydb.cfg for MakeMKV Blu-ray decryption ([e35ed23](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e35ed23f3eef2f7f95a3a8cbe947b7680752e43d))
* auto-update submodules on component releases ([5208420](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5208420f12bc8f590a183e05099f8e052a2789d9))
* Centralize path logic, persist raw/transcode paths, enhance notifications ([0738575](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/07385757099fbaca318a6229e2090f09eaeb7d2a))
* file browser API with path-validated CRUD operations ([3d3ad25](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3d3ad2500656521ac93e32cad9ea53ef7d26bd0d))
* GPU hardware detection via sysfs with WSL2 support ([45a6e71](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/45a6e71654a9f06e3bf8b72f88dda3512eea2040))
* harden disc detection chain against retriggering and timeouts ([6131596](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/613159665a71a69d1ba3411e74ed1ed48f0ef70a))
* implement global ripping pause and manual start in wait loop ([025622d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/025622d20c321f3bd42583f97dda1edd1f2be04e))
* integrate disc title matcher into identification pipeline ([2687b3a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2687b3aaed346f32298e7447ebf3a10927472b3f))
* merge upstream logging refactor and exception handling ([ac51ebb](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ac51ebbd1a38186b802a2fc2735cebb69a1d54d6))
* native transcoder webhook notification ([3a20175](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3a2017581095270e18bb177b822872a445e56c4c))
* normalize video_type to 'music' for audio CD pipeline ([3e4e597](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3e4e5971af1e5f3c4486b2b82bb74677ff764a81))
* per-job pause support in manual wait loop ([aaa66b4](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/aaa66b48bb0bdb76dcf7063613f97346d1968ec0))
* per-job transcode config overrides (ARM side) ([c69e7aa](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c69e7aa0945f850334e0ef540c98ab883ed29875))
* pin HandBrake version, add weekly dependency check ([7ffa4ed](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7ffa4ed75691aafd349a528ae9fde68c4ea3afed))
* port upstream PRs [#1698](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1698), [#1605](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1605), [#1660](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1660) ([a3547e8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a3547e89dd4130af9dcfc0af7fee789324878a4c))
* publish our own base image, clean up workflows ([5aea491](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5aea4915aec53712fcaa314f167f7df9f1e27aae))
* Remove login_required from API v1, add cancel endpoint and config validation ([5da273f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5da273fefe508d7bbddcbb56652ac6acc151c90b))
* show recursive folder sizes in file browser listing ([0e8536a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0e8536a38e1d11d9c42785e89bebbb4cbd103000))
* structured logging with structlog ([4a62e02](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4a62e02ee3089a49f20ebd4025c2e7b964945c49))


### Bug Fixes

* add mount retry with backoff for slow USB optical drives ([8bc5123](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8bc51230dd86c77d5c60b43f07a0e59c5868c9f4))
* add mount retry with backoff for slow USB optical drives ([d8a2e1b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d8a2e1b4fce670c37b0776e7db3bb71e121b6ddd))
* add timeouts to MakeMKV keydb download to prevent startup hangs ([d4ac27b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d4ac27bfac21bcdd08afb951b090cca9101017be))
* address CodeQL alerts with config and generic error messages ([152177b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/152177bb791e78517b1d23040c761e21c5190e65))
* allow NFS/group-based access in startup ownership check ([aa12cb5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/aa12cb54bf43914e660a5233889ee7cbae8fd533))
* allow NFS/group-based access in startup ownership check ([ccd6073](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ccd60735ac275f09916667a7dc8ff92c116f9301))
* always chown subdirs at startup for Docker volume mounts ([0904838](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/090483837c35711d07ccfc039171c52498f3c10e))
* auto-migrate database schema on ripper startup ([894dc1f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/894dc1f135c0793e2f3372d5933702f6a0f92b48))
* bind-mount UI VERSION file in dev compose ([771eba8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/771eba8f4150b9c1f985c9d0d053977374fb2d34))
* break arm.ui import chain to fix CI test collection failure ([dc35772](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/dc357724af654d8af55095041c2fc4ee830fd4ae))
* break CodeQL taint chains for path injection and sensitive logging ([9bf05c5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9bf05c521250170db88b2b44f9661bea742df02b))
* build ARM from source in remote-transcoder compose, enable devices ([1a472ad](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1a472adc734d495319a3a27e170c46ced573691f))
* bump Flask-WTF to 1.2.2 for Flask 3.x compatibility ([5462e38](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5462e388f34bae19f4ae6f64c188e3bd2593044b))
* bump itsdangerous and Werkzeug for Flask 3.1.2 compatibility ([adb4dda](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/adb4dda9635beaf1eae991123fa4305dc72fe4a1))
* clear stale ripping_paused flag on container startup ([3788776](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3788776cfec576edc3c698c2c454118ed542bcfb))
* configure release-please to update VERSION file ([8f8634b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8f8634b80e2b369ac60c14790ae9da9c97b90b7c))
* correct Docker Hub image names for UI and transcoder ([4f0ec61](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4f0ec61dcfd0e5b5c5e45486b96b014e62235c6f))
* create missing optical drive device nodes at container startup ([da556c0](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/da556c06135fcf43e0a211cc0422e126b6d89a52))
* data disc with same label silently discarded (upstream [#1651](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1651)) ([72cf674](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/72cf674b1d1e3d8aea529572f1b39377e96c043b))
* Detect abcde I/O errors despite zero exit code ([#1526](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1526)) ([abc4f68](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/abc4f684ad415810515a201e87c05b0b1cda2d6b))
* dev compose builds from sibling repos, not stale submodules ([c40327a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c40327aa2e3d4e9cc008a509548a4efddef5e697))
* docker-compose review fixes across all repos ([768ab0a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/768ab0ac51e9ba1d9d4f0784aa71abb2018a427d))
* Don't treat unparsed MakeMKV output as fatal when exit code is 0 ([#1688](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1688)) ([d6623e9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d6623e9f5c2bc1705877c5e90899eea80575cfcf))
* drop Python 3.9 from CI matrix (alembic 1.18 requires &gt;=3.10) ([6ffd19b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6ffd19b5609afe209e1c25d44100f7b6ab4e125d))
* early exit on 0 titles, persist MakeMKV key, improve error messages ([248d1a6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/248d1a6ef0cbef35afc9eda8c968002164c2dae1))
* exit 0 when drive not in /sys/block during rescan ([2a40d46](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2a40d46c3c1ec6a496024cb40eb21d18939a3205))
* extract 4-digit year from OMDb/CRC date ranges in ARM ripper ([3b0703a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3b0703afb1e03ccb3245ff1cc388b2be4d9cdaee))
* Fall back to exact title match for short OMDb queries ([#1430](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1430)) ([9a87349](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9a87349cba50165c735ac63643708f3999c1b5ff))
* force fresh DB read in AppState.get() so pause works across processes ([abbfac8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/abbfac842b7d0ba8569b1dbc059eeeb91f39dd54))
* guard against None mdisc in MakeMKV disc discovery ([#60](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/60)) ([30da652](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/30da652bb90092a552ccb2ddc1a7eb56396cfb4a))
* Guard HandBrake no_of_titles against None and string type ([#1628](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1628)) ([c10d917](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c10d917347f98c94cd7358baf12ad100bc278d32))
* Handle malformed BDMV XML and ensure umount ([#1650](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1650), [#1664](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1664)) ([ac33272](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ac33272bb2da72f60683ea0f0570e3815b04a68d))
* handle MusicBrainz rate limiting in integration tests ([8edfa26](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8edfa264790bd7aff53e9ccab25a95814a040e5a))
* Handle nameless drives in drives_update ([#1584](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1584)) ([2e63381](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2e63381ed2d56a145b9a36dadf7bb4429984011b))
* Handle None job.drive in makemkv.py ([#1665](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1665)) ([0e465ee](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0e465ee495e639df0a760ed1610e5fb15fcb1dc6))
* handle unknown drive device nodes gracefully in setup() ([db33015](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/db33015f8a87535e0a195713b04707b5ea163ad5))
* Harden calc_process_time against non-numeric input, downgrade log to DEBUG ([#1641](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1641)) ([78ab2e9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/78ab2e9c26f8021e8626094266c324fd121a29a3))
* Harden OMDb fallback with timeout and broad exception handling ([#1430](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1430)) ([ed39afc](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ed39afc02bd21226197f7355ea94eb60445fc5b9))
* **installer:** correctly detect contrib for bookworm-updates/security across deb822 + mirror lists ([e86f8d9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e86f8d9c1edddde8f24325e236028bc568941185))
* keydb download runs in background, compose improvements ([a02ec4f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a02ec4f972171612a2e3bbccc407faf76b536836))
* Log umount diagnostics and improve test isolation ([#1664](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1664), [#1584](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1584), [#1430](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1430)) ([d939362](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d939362c2998853c6911d4c107f42a93a5ac6943))
* make ARM_UI_TRANSCODER_URL configurable via .env ([5d63035](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5d63035e967da586dd51f057f90bb85ee7a3266c))
* match udev add|change action for container disc detection ([b367eb8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b367eb82d4223181c531c40411cf7e265acf22ba))
* mount single device instead of --all so arm user can mount discs ([8c0550b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8c0550bee3d1bc28e3f2b9d13b17e967321103d7))
* mount transcoder raw volume as rw for source deletion ([cd71aaf](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/cd71aaf737bbff497f34bd007f88e4096ba71cfe))
* pass completed path base to notify script for correct transcoder path ([678fcd3](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/678fcd3b825f5e4d92a5be993281a21021585096))
* Prevent duplicate file assignment in _reconcile_filenames ([#1355](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1355), [#1281](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1281)) ([c1f6caa](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c1f6caabfdb5045c323c5382e6e120b536c6eba4))
* Prevent str(None) producing literal 'None' as bluray title ([#1650](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1650)) ([efa139d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/efa139d990815d8472da991eb3ce5069b369d1bf))
* protect against drive re-enumeration (sr0→sr1→sr2 cycling) ([fbe6ca6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/fbe6ca653bf6d7fb06ef0da6dad96a947b70253c))
* re-initialize job log after disc identification resolves label ([2e3e8f4](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2e3e8f4cabe5974105f2f85d311a09f343a9e36d))
* Reconcile MakeMKV scan-time filenames with actual rip output ([#1355](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1355), [#1281](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1281)) ([2623b11](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2623b116fa1123ad231681c944fd9c2d8ac6f4a1))
* remove :ro from rescan_drive.sh bind-mount ([668c37b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/668c37b912d306d19c1d6c2ee7a885106187573e))
* remove unused dependencies from base image ([0812356](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0812356ac9c2afb0b7a74280159fc6380151ea67))
* replace hard-coded paths with configurable ones ([824e720](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/824e720e4608cd520b2ae6f38ce4943cf057354f))
* replace PLACEHOLDER values with empty strings in rip method config ([af55799](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/af557994e4a9cd116e5bb26e91883f2956aea621))
* replace upstream URLs with fork URLs across wiki ([797bab9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/797bab942ec869a42a38ffd4e2fa715fa2389aa1))
* resolve all 25 CodeQL security warnings ([9734728](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9734728d6de0112826dd9a646bfc2d6d12272652))
* resolve flake8 lint errors ([0c72660](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0c726609307c8c09a8c3fd06aef5d82c81ba82fb))
* Resolve flake8 lint errors across codebase ([1654f76](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1654f7614776d0e0fe8391d31c22b05859789b27))
* resolve SonarCloud LOW maintainability issues ([4b731bb](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4b731bb4a7f089833424b696a92f4bb7e3158c5c))
* resolve SonarCloud Python HIGH issues (S1192, S3776, S5655, S8415) ([d7c74e6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d7c74e6f3551427f4d47fd20e107ee31fbf2cd17))
* resolve SonarCloud Python MEDIUM maintainability issues ([37ff350](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/37ff35095cfb7e0679fa572e3edac3c6c54f8be1))
* resolve SonarCloud quality gate failures ([a004957](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a00495730ee2ce342477d8d6d12e6296e209c0b0))
* resolve SonarCloud reliability bugs (S7493, S1244) ([26ea784](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/26ea78460d66332a21ca543a4fbfd5408352d86f))
* resolve SonarCloud security hotspots and test flakiness ([816ea5e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/816ea5ecbd676807053cdfbf2fb486960160ce09))
* resolve SonarCloud shell MEDIUM maintainability issues ([c2e9902](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c2e99022d4e43a60e5aa48444a28ebfb1169cdf9))
* resolve SonarCloud shell script issues (S7688, S131) ([3120783](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3120783a14380ec9810229e21347242d50c44c3d))
* respect global pause even when title_manual is set ([0693e32](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0693e329f34602a055f2dba5af2c7505114c4783))
* restore HandBrake preset list (accidentally emptied) ([feb89ec](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/feb89ecb76644a3854ce759acfbbff95a9616aca))
* restore makemkv-settings named volume definition ([4e5096d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4e5096dfbea3d134103f6c9396bd78d27199bf08))
* restore submodule pointers (auto-managed by CI) ([af36ccf](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/af36ccf5ebd88648d65bd4b61dff1e66d867796b))
* retry drive detection at startup when udev hasn't settled ([2e9cadc](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2e9cadc3afc1fcb5e8015bf6af980643c404f4f1))
* retry push with rebase in update-submodules workflow ([5fa8f69](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5fa8f695a27c156b27e85254874e640804007d45))
* Rewrite Docker publish workflow for dual-registry push ([83adb0e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/83adb0e723ac2d43f8e11d524ba81ae3b0c7a677))
* run arm-hb-presets as root to write to volume ([409dbeb](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/409dbebf0b0805acc8b8a4c6396916a9e4770afe))
* save_disc_poster() leaves disc mounted before MakeMKV (upstream [#1664](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1664)) ([5b58335](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5b583352c6bed69c7ef55c9f5258e96a6d96e8e6))
* scope Docker builds to linux/amd64 only ([f047133](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f0471338d2b2c49dd62e4aa6e7ccc1e957f664e2))
* scope workflow permissions to job level (S8264/S8233) ([d6fb744](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d6fb7444c2a88749a8471cd5e9b67dbdfc66db55))
* Set fallback no_of_titles on ffprobe failure, guard None comparison ([#1628](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1628)) ([96697d1](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/96697d13202b84b6bdf7887b768aeb8eaa964808))
* set track.ripped=False during scan, True after actual rip ([2742af7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2742af7631fc3004118d847a1219b119eb84d416))
* settings not persisting after config save (upstream [#1639](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1639)) ([7f661b5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7f661b54066d9518b6c33038668b131e81a604ac))
* **settings:** trim whitespace from form values on save ([97214a8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/97214a845e96a3289018d78cf3ed0a0c07161315))
* skip Apprise when no channels configured, improve duplicate log ([bc85939](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/bc85939a7952e25a73df362c8c0dcbd1d9e7daab))
* Skip unrecognized MakeMKV output lines in parser ([#1688](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1688)) ([7297893](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7297893d2e17494f92095655eecb8cc94d519f5b))
* SQLite WAL mode, idempotent migration, and NFS media path ([#76](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/76)) ([8733d9a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8733d9af3e9cddeaccecf1089a44f30f75a5cd56))
* Strip whitespace from settings values, harden git version check ([#1684](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1684), [#1345](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1345)) ([edac6d2](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/edac6d2fd4cc5c69384b0ef03ec928911ab15e56))
* support NFS mounts in host path detection for file browser ([2eb7a40](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2eb7a4070e0258d941656275b47ff9f2afc8608c))
* suppress spurious transcoder webhooks and accept transcoding status callback ([c563c82](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c563c82af4007be6988eb23d3e7b1ad944447b3f))
* tolerate read-only bind-mounts in /opt/arm during startup ([e9e15dc](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e9e15dc819f8530b58b4e71fab0d64786799c4d4))
* track numbering mismatch causes silent data loss ([#1475](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1475)) ([35f091e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/35f091eb08791d55f6233b50b7fd6da3938fd58a))
* udev rule ordering, action matching, and lock path ([acd59a7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/acd59a72ae42b295c7d744d193b164c2c194d380))
* update Docker.md default fork from automaticrippingmachine to uprightbass360 ([93fdab7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/93fdab7c8749453ab79d8bc71566304a34733bdc))
* update help URL in main.py to fork repo ([a4eb593](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a4eb5938f67f6bf5ae516dbfc6d3a1b09ad67fb1))
* update issue templates with fork references ([a9a5bf8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a9a5bf8297408f4e674f3b2a98e47f53916c3931))
* update put_track test to expect ripped=False ([db38c78](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/db38c78144dd12f9ff88589416e67003612d852c))
* update stale wiki links and fork references ([974d638](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/974d638599159a99d4ef91587469468d3a3b3159))
* update wiki sidebar, contributing docs for fork ([1d3a85f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1d3a85ff8d62b5ee0d8daa125f7598f04a1651ab))
* Use consistent filename in rip_data and harden abcde log check ([#1651](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1651), [#1526](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1526)) ([830a743](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/830a7435156cb53b82ab45ea5e5f442cf3a83b9a))
* Use de-duplicated filename for data disc ISO output ([#1651](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1651)) ([500e89d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/500e89dc71b9f9999ac15c28f90d853b4d1481a9))
* use direct DB connection for pause check to bypass stale session ([17f16cf](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/17f16cf4b18fbbbf9ffba57d875ac6006803cd34))
* Use list args for HandBrake subprocess to prevent shell quoting issues ([#1457](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1457)) ([4f32270](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4f32270fdce65ae3e627c53aedf3a1a0634a3026))
* use PAT for release-please so releases trigger publish workflow ([c060ec1](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c060ec1c8b9f343fd21245043512bca60a3c32d0))
* use pytest.approx for float comparison (SonarCloud S1244) ([fd8bbab](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/fd8bbab095d545c20d7fcb16a57f5f5bcc90d5cd))
* Use total_seconds() for ETA calculation over 24 hours ([#1641](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1641)) ([40bf39f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/40bf39f3acc7f85f22efdc5bb774b39063491678))
* Use Union type syntax for Python 3.9 compatibility ([ffad9c7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ffad9c772da6844eec767df5c3cda570438d2625))
* wait for ARM healthcheck before starting UI ([ad1e200](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ad1e200b53b748a7ece94afa08b34c0e80a0fe39))


### Code Refactoring

* remove HandBrake/FFmpeg transcoding from ARM ([66ec6d6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/66ec6d633a2df447a41822234f2810c305e78aa0))
* replace Flask with FastAPI, delete old UI ([0981e7f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0981e7fcc52d974241efef92b810df1134f80cee))

## [10.11.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.10.2-alpha.1...v10.11.0-alpha.1) (2026-03-05)


### Features

* add drive rescan script and API endpoint ([883b4ac](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/883b4ac159716e0f8ea0486bd374a9875363ca5a))


### Bug Fixes

* exit 0 when drive not in /sys/block during rescan ([2a40d46](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2a40d46c3c1ec6a496024cb40eb21d18939a3205))
* protect against drive re-enumeration (sr0→sr1→sr2 cycling) ([fbe6ca6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/fbe6ca653bf6d7fb06ef0da6dad96a947b70253c))
* remove :ro from rescan_drive.sh bind-mount ([668c37b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/668c37b912d306d19c1d6c2ee7a885106187573e))
* tolerate read-only bind-mounts in /opt/arm during startup ([e9e15dc](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e9e15dc819f8530b58b4e71fab0d64786799c4d4))

## [10.10.2-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.10.1-alpha.1...v10.10.2-alpha.1) (2026-03-04)


### Bug Fixes

* handle unknown drive device nodes gracefully in setup() ([db33015](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/db33015f8a87535e0a195713b04707b5ea163ad5))

## [10.10.1-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.10.0-alpha.1...v10.10.1-alpha.1) (2026-03-04)


### Bug Fixes

* match udev add|change action for container disc detection ([b367eb8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/b367eb82d4223181c531c40411cf7e265acf22ba))
* udev rule ordering, action matching, and lock path ([acd59a7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/acd59a72ae42b295c7d744d193b164c2c194d380))

## [10.10.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.9.0-alpha.1...v10.10.0-alpha.1) (2026-03-04)


### Features

* harden disc detection chain against retriggering and timeouts ([6131596](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/613159665a71a69d1ba3411e74ed1ed48f0ef70a))

## [10.9.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.8.4-alpha.1...v10.9.0-alpha.1) (2026-03-04)


### Features

* port upstream PRs [#1698](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1698), [#1605](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1605), [#1660](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1660) ([a3547e8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a3547e89dd4130af9dcfc0af7fee789324878a4c))


### Bug Fixes

* data disc with same label silently discarded (upstream [#1651](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1651)) ([72cf674](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/72cf674b1d1e3d8aea529572f1b39377e96c043b))
* handle MusicBrainz rate limiting in integration tests ([8edfa26](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8edfa264790bd7aff53e9ccab25a95814a040e5a))
* resolve SonarCloud quality gate failures ([a004957](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a00495730ee2ce342477d8d6d12e6296e209c0b0))
* resolve SonarCloud security hotspots and test flakiness ([816ea5e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/816ea5ecbd676807053cdfbf2fb486960160ce09))
* save_disc_poster() leaves disc mounted before MakeMKV (upstream [#1664](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1664)) ([5b58335](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5b583352c6bed69c7ef55c9f5258e96a6d96e8e6))
* settings not persisting after config save (upstream [#1639](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1639)) ([7f661b5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7f661b54066d9518b6c33038668b131e81a604ac))
* use pytest.approx for float comparison (SonarCloud S1244) ([fd8bbab](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/fd8bbab095d545c20d7fcb16a57f5f5bcc90d5cd))

## [10.8.4-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.8.3-alpha.1...v10.8.4-alpha.1) (2026-03-03)


### Bug Fixes

* resolve SonarCloud LOW maintainability issues ([4b731bb](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4b731bb4a7f089833424b696a92f4bb7e3158c5c))
* resolve SonarCloud Python MEDIUM maintainability issues ([37ff350](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/37ff35095cfb7e0679fa572e3edac3c6c54f8be1))
* resolve SonarCloud shell MEDIUM maintainability issues ([c2e9902](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c2e99022d4e43a60e5aa48444a28ebfb1169cdf9))

## [10.8.3-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.8.2-alpha.1...v10.8.3-alpha.1) (2026-03-03)


### Bug Fixes

* resolve SonarCloud Python HIGH issues (S1192, S3776, S5655, S8415) ([d7c74e6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d7c74e6f3551427f4d47fd20e107ee31fbf2cd17))
* resolve SonarCloud shell script issues (S7688, S131) ([3120783](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3120783a14380ec9810229e21347242d50c44c3d))

## [10.8.2-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.8.1-alpha.1...v10.8.2-alpha.1) (2026-03-02)


### Bug Fixes

* resolve SonarCloud reliability bugs (S7493, S1244) ([26ea784](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/26ea78460d66332a21ca543a4fbfd5408352d86f))

## [10.8.1-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.8.0-alpha.1...v10.8.1-alpha.1) (2026-03-02)


### Bug Fixes

* address CodeQL alerts with config and generic error messages ([152177b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/152177bb791e78517b1d23040c761e21c5190e65))
* scope workflow permissions to job level (S8264/S8233) ([d6fb744](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d6fb7444c2a88749a8471cd5e9b67dbdfc66db55))

## [10.8.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.7.1-alpha.1...v10.8.0-alpha.1) (2026-03-02)


### Features

* show recursive folder sizes in file browser listing ([0e8536a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0e8536a38e1d11d9c42785e89bebbb4cbd103000))

## [10.7.1-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.7.0-alpha.1...v10.7.1-alpha.1) (2026-03-02)


### Bug Fixes

* support NFS mounts in host path detection for file browser ([2eb7a40](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2eb7a4070e0258d941656275b47ff9f2afc8608c))

## [10.7.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.6.0-alpha.1...v10.7.0-alpha.1) (2026-03-02)


### Features

* add file permissions display and fix-permissions endpoint ([983ba13](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/983ba131c0528f9637812fa22cc42adaeb468043))

## [10.6.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.5.2-alpha.1...v10.6.0-alpha.1) (2026-03-02)


### Features

* file browser API with path-validated CRUD operations ([3d3ad25](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3d3ad2500656521ac93e32cad9ea53ef7d26bd0d))

## [10.5.2-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.5.1-alpha.1...v10.5.2-alpha.1) (2026-03-02)


### Bug Fixes

* suppress spurious transcoder webhooks and accept transcoding status callback ([c563c82](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c563c82af4007be6988eb23d3e7b1ad944447b3f))

## [10.5.1-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.5.0-alpha.1...v10.5.1-alpha.1) (2026-03-02)


### Bug Fixes

* SQLite WAL mode, idempotent migration, and NFS media path ([#76](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/76)) ([8733d9a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8733d9af3e9cddeaccecf1089a44f30f75a5cd56))

## [10.5.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.4.0-alpha.1...v10.5.0-alpha.1) (2026-03-01)


### Features

* per-job transcode config overrides (ARM side) ([c69e7aa](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c69e7aa0945f850334e0ef540c98ab883ed29875))
* structured logging with structlog ([4a62e02](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4a62e02ee3089a49f20ebd4025c2e7b964945c49))


### Bug Fixes

* allow NFS/group-based access in startup ownership check ([aa12cb5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/aa12cb54bf43914e660a5233889ee7cbae8fd533))
* allow NFS/group-based access in startup ownership check ([ccd6073](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ccd60735ac275f09916667a7dc8ff92c116f9301))
* dev compose builds from sibling repos, not stale submodules ([c40327a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c40327aa2e3d4e9cc008a509548a4efddef5e697))
* keydb download runs in background, compose improvements ([a02ec4f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a02ec4f972171612a2e3bbccc407faf76b536836))
* make ARM_UI_TRANSCODER_URL configurable via .env ([5d63035](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5d63035e967da586dd51f057f90bb85ee7a3266c))
* mount transcoder raw volume as rw for source deletion ([cd71aaf](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/cd71aaf737bbff497f34bd007f88e4096ba71cfe))
* restore makemkv-settings named volume definition ([4e5096d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4e5096dfbea3d134103f6c9396bd78d27199bf08))
* set track.ripped=False during scan, True after actual rip ([2742af7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2742af7631fc3004118d847a1219b119eb84d416))
* update put_track test to expect ripped=False ([db38c78](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/db38c78144dd12f9ff88589416e67003612d852c))

## [10.4.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.3.1-alpha.1...v10.4.0-alpha.1) (2026-02-28)


### Features

* add poster_url to transcoder webhook payload ([8c1ba04](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8c1ba0438e06c05c31582b3cd456e04462093738))

## [10.3.1-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.3.0-alpha.1...v10.3.1-alpha.1) (2026-02-28)


### Bug Fixes

* retry push with rebase in update-submodules workflow ([5fa8f69](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5fa8f695a27c156b27e85254874e640804007d45))

## [10.3.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.2.2-alpha.1...v10.3.0-alpha.1) (2026-02-28)


### Features

* add seed log files for all dev-data jobs ([ae774ee](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ae774ee39644cab272020c376faa46f5774839b4))
* per-job pause support in manual wait loop ([aaa66b4](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/aaa66b48bb0bdb76dcf7063613f97346d1968ec0))


### Bug Fixes

* auto-migrate database schema on ripper startup ([894dc1f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/894dc1f135c0793e2f3372d5933702f6a0f92b48))
* extract 4-digit year from OMDb/CRC date ranges in ARM ripper ([3b0703a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3b0703afb1e03ccb3245ff1cc388b2be4d9cdaee))

## [10.2.2-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.2.1-alpha.1...v10.2.2-alpha.1) (2026-02-28)


### Bug Fixes

* replace upstream URLs with fork URLs across wiki ([797bab9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/797bab942ec869a42a38ffd4e2fa715fa2389aa1))
* restore submodule pointers (auto-managed by CI) ([af36ccf](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/af36ccf5ebd88648d65bd4b61dff1e66d867796b))
* update Docker.md default fork from automaticrippingmachine to uprightbass360 ([93fdab7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/93fdab7c8749453ab79d8bc71566304a34733bdc))
* update help URL in main.py to fork repo ([a4eb593](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a4eb5938f67f6bf5ae516dbfc6d3a1b09ad67fb1))
* update issue templates with fork references ([a9a5bf8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a9a5bf8297408f4e674f3b2a98e47f53916c3931))
* update stale wiki links and fork references ([974d638](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/974d638599159a99d4ef91587469468d3a3b3159))
* update wiki sidebar, contributing docs for fork ([1d3a85f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1d3a85ff8d62b5ee0d8daa125f7598f04a1651ab))

## [10.2.1-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.2.0-alpha.1...v10.2.1-alpha.1) (2026-02-28)


### Bug Fixes

* add timeouts to MakeMKV keydb download to prevent startup hangs ([d4ac27b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d4ac27bfac21bcdd08afb951b090cca9101017be))

## [10.2.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.1.4-alpha.1...v10.2.0-alpha.1) (2026-02-28)


### Features

* add structured fields, naming engine, and music metadata enhancements ([08c1b2e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/08c1b2e6c8ace117fd1ffaa23db744cc37aea485))
* normalize video_type to 'music' for audio CD pipeline ([3e4e597](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3e4e5971af1e5f3c4486b2b82bb74677ff764a81))


### Bug Fixes

* restore HandBrake preset list (accidentally emptied) ([feb89ec](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/feb89ecb76644a3854ce759acfbbff95a9616aca))

## [10.1.4-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.1.3-alpha.1...v10.1.4-alpha.1) (2026-02-26)


### Bug Fixes

* add mount retry with backoff for slow USB optical drives ([8bc5123](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8bc51230dd86c77d5c60b43f07a0e59c5868c9f4))
* add mount retry with backoff for slow USB optical drives ([d8a2e1b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d8a2e1b4fce670c37b0776e7db3bb71e121b6ddd))
* re-initialize job log after disc identification resolves label ([2e3e8f4](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2e3e8f4cabe5974105f2f85d311a09f343a9e36d))

## [10.1.3-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.1.2-alpha.1...v10.1.3-alpha.1) (2026-02-26)


### Bug Fixes

* bind-mount UI VERSION file in dev compose ([771eba8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/771eba8f4150b9c1f985c9d0d053977374fb2d34))
* replace PLACEHOLDER values with empty strings in rip method config ([af55799](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/af557994e4a9cd116e5bb26e91883f2956aea621))
* run arm-hb-presets as root to write to volume ([409dbeb](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/409dbebf0b0805acc8b8a4c6396916a9e4770afe))

## [10.1.2-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.1.1-alpha.1...v10.1.2-alpha.1) (2026-02-25)


### Bug Fixes

* docker-compose review fixes across all repos ([768ab0a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/768ab0ac51e9ba1d9d4f0784aa71abb2018a427d))
* skip Apprise when no channels configured, improve duplicate log ([bc85939](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/bc85939a7952e25a73df362c8c0dcbd1d9e7daab))

## [10.1.1-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.1.0-alpha.1...v10.1.1-alpha.1) (2026-02-25)


### Bug Fixes

* guard against None mdisc in MakeMKV disc discovery ([#60](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/60)) ([30da652](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/30da652bb90092a552ccb2ddc1a7eb56396cfb4a))

## [10.1.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v10.0.0-alpha.1...v10.1.0-alpha.1) (2026-02-25)


### Features

* native transcoder webhook notification ([3a20175](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3a2017581095270e18bb177b822872a445e56c4c))

## [10.0.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v1.6.4...v10.0.0-alpha.1) (2026-02-25)


### ⚠ BREAKING CHANGES

* Built-in transcoding is no longer available. Use the dedicated transcoder service (uprightbass360/arm-transcoder) instead.
* Flask, Werkzeug, WTForms, and Waitress are removed. The API server now uses FastAPI + uvicorn.

### Features

* add 4K UHD Blu-ray disc type detection (bluray4k) ([a972582](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a972582dfa8fbdb2192f8531a79552bf8cb238d6))
* add AppState model for global ripping pause control ([f4b600c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f4b600ca5b400538cd3a47ff4dbcb956ca1a2c38))
* add Docker Compose orchestration for multi-service deployment ([5200d42](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5200d42d2243f78bedadca864b9c25c139a9761d))
* Add drives API endpoint and harden drive matching logic ([4720cea](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4720ceab36fc5353630fdd2c7060942fe8445639))
* add release bundle workflow to publish deploy zip as release asset ([9c27280](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9c27280f0c9b3b819ceb4cf6065d133b7758fd4d))
* Add REST API layer at /api/v1/ ([3ce2d7b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3ce2d7b7d1182f31ff8ae89d64098e913ac6e849))
* add system monitoring, ripping toggle, and job start endpoints ([c9c2b23](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c9c2b23add90af72ff2b27b4ee4250ffdd403ee2))
* Add title update, settings, and system info API endpoints ([e3477d6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e3477d64de65d60908c76bf005712b957fb17e38))
* add TV series season/disc parsing to disc title matcher ([0119c2c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0119c2c8552a8bcac15aedcf7a9e278cb6ffc637))
* add user-settable uhd_capable flag to drives ([4b67675](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4b6767591bf1fe09da9045c49b23d119d9a40952))
* auto-download community keydb.cfg for MakeMKV Blu-ray decryption ([e35ed23](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e35ed23f3eef2f7f95a3a8cbe947b7680752e43d))
* auto-update submodules on component releases ([5208420](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5208420f12bc8f590a183e05099f8e052a2789d9))
* Centralize path logic, persist raw/transcode paths, enhance notifications ([0738575](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/07385757099fbaca318a6229e2090f09eaeb7d2a))
* GPU hardware detection via sysfs with WSL2 support ([45a6e71](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/45a6e71654a9f06e3bf8b72f88dda3512eea2040))
* implement global ripping pause and manual start in wait loop ([025622d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/025622d20c321f3bd42583f97dda1edd1f2be04e))
* integrate disc title matcher into identification pipeline ([2687b3a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2687b3aaed346f32298e7447ebf3a10927472b3f))
* merge upstream logging refactor and exception handling ([ac51ebb](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ac51ebbd1a38186b802a2fc2735cebb69a1d54d6))
* pin HandBrake version, add weekly dependency check ([7ffa4ed](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7ffa4ed75691aafd349a528ae9fde68c4ea3afed))
* publish our own base image, clean up workflows ([5aea491](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5aea4915aec53712fcaa314f167f7df9f1e27aae))
* Remove login_required from API v1, add cancel endpoint and config validation ([5da273f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5da273fefe508d7bbddcbb56652ac6acc151c90b))


### Bug Fixes

* always chown subdirs at startup for Docker volume mounts ([0904838](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/090483837c35711d07ccfc039171c52498f3c10e))
* break arm.ui import chain to fix CI test collection failure ([dc35772](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/dc357724af654d8af55095041c2fc4ee830fd4ae))
* break CodeQL taint chains for path injection and sensitive logging ([9bf05c5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9bf05c521250170db88b2b44f9661bea742df02b))
* build ARM from source in remote-transcoder compose, enable devices ([1a472ad](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1a472adc734d495319a3a27e170c46ced573691f))
* bump Flask-WTF to 1.2.2 for Flask 3.x compatibility ([5462e38](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5462e388f34bae19f4ae6f64c188e3bd2593044b))
* bump itsdangerous and Werkzeug for Flask 3.1.2 compatibility ([adb4dda](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/adb4dda9635beaf1eae991123fa4305dc72fe4a1))
* clear stale ripping_paused flag on container startup ([3788776](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3788776cfec576edc3c698c2c454118ed542bcfb))
* configure release-please to update VERSION file ([8f8634b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8f8634b80e2b369ac60c14790ae9da9c97b90b7c))
* correct Docker Hub image names for UI and transcoder ([4f0ec61](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4f0ec61dcfd0e5b5c5e45486b96b014e62235c6f))
* create missing optical drive device nodes at container startup ([da556c0](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/da556c06135fcf43e0a211cc0422e126b6d89a52))
* Detect abcde I/O errors despite zero exit code ([#1526](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1526)) ([abc4f68](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/abc4f684ad415810515a201e87c05b0b1cda2d6b))
* Don't treat unparsed MakeMKV output as fatal when exit code is 0 ([#1688](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1688)) ([d6623e9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d6623e9f5c2bc1705877c5e90899eea80575cfcf))
* drop Python 3.9 from CI matrix (alembic 1.18 requires &gt;=3.10) ([6ffd19b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6ffd19b5609afe209e1c25d44100f7b6ab4e125d))
* early exit on 0 titles, persist MakeMKV key, improve error messages ([248d1a6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/248d1a6ef0cbef35afc9eda8c968002164c2dae1))
* Fall back to exact title match for short OMDb queries ([#1430](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1430)) ([9a87349](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9a87349cba50165c735ac63643708f3999c1b5ff))
* force fresh DB read in AppState.get() so pause works across processes ([abbfac8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/abbfac842b7d0ba8569b1dbc059eeeb91f39dd54))
* Guard HandBrake no_of_titles against None and string type ([#1628](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1628)) ([c10d917](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c10d917347f98c94cd7358baf12ad100bc278d32))
* Handle malformed BDMV XML and ensure umount ([#1650](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1650), [#1664](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1664)) ([ac33272](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ac33272bb2da72f60683ea0f0570e3815b04a68d))
* Handle nameless drives in drives_update ([#1584](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1584)) ([2e63381](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2e63381ed2d56a145b9a36dadf7bb4429984011b))
* Handle None job.drive in makemkv.py ([#1665](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1665)) ([0e465ee](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0e465ee495e639df0a760ed1610e5fb15fcb1dc6))
* Harden calc_process_time against non-numeric input, downgrade log to DEBUG ([#1641](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1641)) ([78ab2e9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/78ab2e9c26f8021e8626094266c324fd121a29a3))
* Harden OMDb fallback with timeout and broad exception handling ([#1430](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1430)) ([ed39afc](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ed39afc02bd21226197f7355ea94eb60445fc5b9))
* **installer:** correctly detect contrib for bookworm-updates/security across deb822 + mirror lists ([e86f8d9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e86f8d9c1edddde8f24325e236028bc568941185))
* Log umount diagnostics and improve test isolation ([#1664](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1664), [#1584](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1584), [#1430](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1430)) ([d939362](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d939362c2998853c6911d4c107f42a93a5ac6943))
* mount single device instead of --all so arm user can mount discs ([8c0550b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8c0550bee3d1bc28e3f2b9d13b17e967321103d7))
* pass completed path base to notify script for correct transcoder path ([678fcd3](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/678fcd3b825f5e4d92a5be993281a21021585096))
* Prevent duplicate file assignment in _reconcile_filenames ([#1355](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1355), [#1281](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1281)) ([c1f6caa](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c1f6caabfdb5045c323c5382e6e120b536c6eba4))
* Prevent str(None) producing literal 'None' as bluray title ([#1650](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1650)) ([efa139d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/efa139d990815d8472da991eb3ce5069b369d1bf))
* Reconcile MakeMKV scan-time filenames with actual rip output ([#1355](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1355), [#1281](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1281)) ([2623b11](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2623b116fa1123ad231681c944fd9c2d8ac6f4a1))
* remove executable bit from files which don't need it ([39e8409](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/39e8409deadd4dbfa71b5599d7db48f8b115c205))
* remove unused dependencies from base image ([0812356](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0812356ac9c2afb0b7a74280159fc6380151ea67))
* replace hard-coded paths with configurable ones ([824e720](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/824e720e4608cd520b2ae6f38ce4943cf057354f))
* resolve all 25 CodeQL security warnings ([9734728](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9734728d6de0112826dd9a646bfc2d6d12272652))
* resolve flake8 lint errors ([0c72660](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0c726609307c8c09a8c3fd06aef5d82c81ba82fb))
* Resolve flake8 lint errors across codebase ([1654f76](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1654f7614776d0e0fe8391d31c22b05859789b27))
* respect global pause even when title_manual is set ([0693e32](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0693e329f34602a055f2dba5af2c7505114c4783))
* retry drive detection at startup when udev hasn't settled ([2e9cadc](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2e9cadc3afc1fcb5e8015bf6af980643c404f4f1))
* Rewrite Docker publish workflow for dual-registry push ([83adb0e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/83adb0e723ac2d43f8e11d524ba81ae3b0c7a677))
* scope Docker builds to linux/amd64 only ([f047133](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f0471338d2b2c49dd62e4aa6e7ccc1e957f664e2))
* Set fallback no_of_titles on ffprobe failure, guard None comparison ([#1628](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1628)) ([96697d1](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/96697d13202b84b6bdf7887b768aeb8eaa964808))
* **settings:** trim whitespace from form values on save ([97214a8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/97214a845e96a3289018d78cf3ed0a0c07161315))
* Skip unrecognized MakeMKV output lines in parser ([#1688](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1688)) ([7297893](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7297893d2e17494f92095655eecb8cc94d519f5b))
* Strip whitespace from settings values, harden git version check ([#1684](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1684), [#1345](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1345)) ([edac6d2](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/edac6d2fd4cc5c69384b0ef03ec928911ab15e56))
* track numbering mismatch causes silent data loss ([#1475](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1475)) ([35f091e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/35f091eb08791d55f6233b50b7fd6da3938fd58a))
* Use consistent filename in rip_data and harden abcde log check ([#1651](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1651), [#1526](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1526)) ([830a743](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/830a7435156cb53b82ab45ea5e5f442cf3a83b9a))
* Use de-duplicated filename for data disc ISO output ([#1651](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1651)) ([500e89d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/500e89dc71b9f9999ac15c28f90d853b4d1481a9))
* use direct DB connection for pause check to bypass stale session ([17f16cf](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/17f16cf4b18fbbbf9ffba57d875ac6006803cd34))
* Use list args for HandBrake subprocess to prevent shell quoting issues ([#1457](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1457)) ([4f32270](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4f32270fdce65ae3e627c53aedf3a1a0634a3026))
* use PAT for release-please so releases trigger publish workflow ([c060ec1](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c060ec1c8b9f343fd21245043512bca60a3c32d0))
* Use total_seconds() for ETA calculation over 24 hours ([#1641](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1641)) ([40bf39f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/40bf39f3acc7f85f22efdc5bb774b39063491678))
* Use Union type syntax for Python 3.9 compatibility ([ffad9c7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ffad9c772da6844eec767df5c3cda570438d2625))
* wait for ARM healthcheck before starting UI ([ad1e200](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ad1e200b53b748a7ece94afa08b34c0e80a0fe39))


### Code Refactoring

* remove HandBrake/FFmpeg transcoding from ARM ([66ec6d6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/66ec6d633a2df447a41822234f2810c305e78aa0))
* replace Flask with FastAPI, delete old UI ([0981e7f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0981e7fcc52d974241efef92b810df1134f80cee))

## [1.6.4](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v1.6.3...v1.6.4) (2026-02-23)


### Bug Fixes

* break arm.ui import chain to fix CI test collection failure ([dc35772](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/dc357724af654d8af55095041c2fc4ee830fd4ae))
* clear stale ripping_paused flag on container startup ([3788776](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3788776cfec576edc3c698c2c454118ed542bcfb))

## [1.6.3](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v1.6.2...v1.6.3) (2026-02-23)


### Bug Fixes

* pass completed path base to notify script for correct transcoder path ([678fcd3](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/678fcd3b825f5e4d92a5be993281a21021585096))

## [1.6.2](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v1.6.1...v1.6.2) (2026-02-23)


### Bug Fixes

* create missing optical drive device nodes at container startup ([da556c0](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/da556c06135fcf43e0a211cc0422e126b6d89a52))

## [1.6.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v1.6.0...v1.6.1) (2026-02-22)


### Bug Fixes

* retry drive detection at startup when udev hasn't settled ([2e9cadc](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2e9cadc3afc1fcb5e8015bf6af980643c404f4f1))

## [1.6.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v1.5.0...v1.6.0) (2026-02-20)


### Features

* add TV series season/disc parsing to disc title matcher ([0119c2c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0119c2c8552a8bcac15aedcf7a9e278cb6ffc637))
* integrate disc title matcher into identification pipeline ([2687b3a](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2687b3aaed346f32298e7447ebf3a10927472b3f))


### Bug Fixes

* mount single device instead of --all so arm user can mount discs ([8c0550b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8c0550bee3d1bc28e3f2b9d13b17e967321103d7))

## [1.5.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v1.4.1...v1.5.0) (2026-02-20)


### Features

* auto-download community keydb.cfg for MakeMKV Blu-ray decryption ([e35ed23](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e35ed23f3eef2f7f95a3a8cbe947b7680752e43d))


### Bug Fixes

* always chown subdirs at startup for Docker volume mounts ([0904838](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/090483837c35711d07ccfc039171c52498f3c10e))
* early exit on 0 titles, persist MakeMKV key, improve error messages ([248d1a6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/248d1a6ef0cbef35afc9eda8c968002164c2dae1))
* force fresh DB read in AppState.get() so pause works across processes ([abbfac8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/abbfac842b7d0ba8569b1dbc059eeeb91f39dd54))
* respect global pause even when title_manual is set ([0693e32](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0693e329f34602a055f2dba5af2c7505114c4783))
* use direct DB connection for pause check to bypass stale session ([17f16cf](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/17f16cf4b18fbbbf9ffba57d875ac6006803cd34))

## [1.4.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v1.4.0...v1.4.1) (2026-02-19)


### Bug Fixes

* break CodeQL taint chains for path injection and sensitive logging ([9bf05c5](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9bf05c521250170db88b2b44f9661bea742df02b))
* resolve all 25 CodeQL security warnings ([9734728](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9734728d6de0112826dd9a646bfc2d6d12272652))

## [1.4.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v1.3.1...v1.4.0) (2026-02-19)


### Features

* add 4K UHD Blu-ray disc type detection (bluray4k) ([a972582](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a972582dfa8fbdb2192f8531a79552bf8cb238d6))
* add user-settable uhd_capable flag to drives ([4b67675](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4b6767591bf1fe09da9045c49b23d119d9a40952))

## [1.3.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v1.3.0...v1.3.1) (2026-02-19)


### Bug Fixes

* wait for ARM healthcheck before starting UI ([ad1e200](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ad1e200b53b748a7ece94afa08b34c0e80a0fe39))

## [1.3.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v1.2.2...v1.3.0) (2026-02-18)


### Features

* merge upstream logging refactor and exception handling ([ac51ebb](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ac51ebbd1a38186b802a2fc2735cebb69a1d54d6))
* pin HandBrake version, add weekly dependency check ([7ffa4ed](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7ffa4ed75691aafd349a528ae9fde68c4ea3afed))
* publish our own base image, clean up workflows ([5aea491](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5aea4915aec53712fcaa314f167f7df9f1e27aae))


### Bug Fixes

* configure release-please to update VERSION file ([8f8634b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/8f8634b80e2b369ac60c14790ae9da9c97b90b7c))
* **installer:** correctly detect contrib for bookworm-updates/security across deb822 + mirror lists ([e86f8d9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e86f8d9c1edddde8f24325e236028bc568941185))
* remove unused dependencies from base image ([0812356](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0812356ac9c2afb0b7a74280159fc6380151ea67))
* scope Docker builds to linux/amd64 only ([f047133](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f0471338d2b2c49dd62e4aa6e7ccc1e957f664e2))
* **settings:** trim whitespace from form values on save ([97214a8](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/97214a845e96a3289018d78cf3ed0a0c07161315))

## [1.2.2](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v1.2.1...v1.2.2) (2026-02-16)


### Bug Fixes

* bump Flask-WTF to 1.2.2 for Flask 3.x compatibility ([5462e38](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5462e388f34bae19f4ae6f64c188e3bd2593044b))
* bump itsdangerous and Werkzeug for Flask 3.1.2 compatibility ([adb4dda](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/adb4dda9635beaf1eae991123fa4305dc72fe4a1))
* drop Python 3.9 from CI matrix (alembic 1.18 requires &gt;=3.10) ([6ffd19b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/6ffd19b5609afe209e1c25d44100f7b6ab4e125d))

## [1.2.1](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v1.2.0...v1.2.1) (2026-02-16)


### Bug Fixes

* use PAT for release-please so releases trigger publish workflow ([c060ec1](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c060ec1c8b9f343fd21245043512bca60a3c32d0))

## [1.2.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v1.1.0...v1.2.0) (2026-02-16)


### Features

* add release bundle workflow to publish deploy zip as release asset ([9c27280](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9c27280f0c9b3b819ceb4cf6065d133b7758fd4d))
* auto-update submodules on component releases ([5208420](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5208420f12bc8f590a183e05099f8e052a2789d9))


### Bug Fixes

* build ARM from source in remote-transcoder compose, enable devices ([1a472ad](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1a472adc734d495319a3a27e170c46ced573691f))
* correct Docker Hub image names for UI and transcoder ([4f0ec61](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4f0ec61dcfd0e5b5c5e45486b96b014e62235c6f))

## [1.1.0](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/v1.0.0...v1.1.0) (2026-02-15)


### Features

* add AppState model for global ripping pause control ([f4b600c](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/f4b600ca5b400538cd3a47ff4dbcb956ca1a2c38))
* add Docker Compose orchestration for multi-service deployment ([5200d42](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5200d42d2243f78bedadca864b9c25c139a9761d))
* Add drives API endpoint and harden drive matching logic ([4720cea](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4720ceab36fc5353630fdd2c7060942fe8445639))
* Add REST API layer at /api/v1/ ([3ce2d7b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/3ce2d7b7d1182f31ff8ae89d64098e913ac6e849))
* add system monitoring, ripping toggle, and job start endpoints ([c9c2b23](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c9c2b23add90af72ff2b27b4ee4250ffdd403ee2))
* Add title update, settings, and system info API endpoints ([e3477d6](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/e3477d64de65d60908c76bf005712b957fb17e38))
* Centralize path logic, persist raw/transcode paths, enhance notifications ([0738575](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/07385757099fbaca318a6229e2090f09eaeb7d2a))
* GPU hardware detection via sysfs with WSL2 support ([45a6e71](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/45a6e71654a9f06e3bf8b72f88dda3512eea2040))
* implement global ripping pause and manual start in wait loop ([025622d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/025622d20c321f3bd42583f97dda1edd1f2be04e))
* Remove login_required from API v1, add cancel endpoint and config validation ([5da273f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/5da273fefe508d7bbddcbb56652ac6acc151c90b))


### Bug Fixes

* Detect abcde I/O errors despite zero exit code ([#1526](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1526)) ([abc4f68](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/abc4f684ad415810515a201e87c05b0b1cda2d6b))
* Don't treat unparsed MakeMKV output as fatal when exit code is 0 ([#1688](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1688)) ([d6623e9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d6623e9f5c2bc1705877c5e90899eea80575cfcf))
* Fall back to exact title match for short OMDb queries ([#1430](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1430)) ([9a87349](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/9a87349cba50165c735ac63643708f3999c1b5ff))
* Guard HandBrake no_of_titles against None and string type ([#1628](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1628)) ([c10d917](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c10d917347f98c94cd7358baf12ad100bc278d32))
* Handle malformed BDMV XML and ensure umount ([#1650](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1650), [#1664](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1664)) ([ac33272](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ac33272bb2da72f60683ea0f0570e3815b04a68d))
* Handle nameless drives in drives_update ([#1584](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1584)) ([2e63381](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2e63381ed2d56a145b9a36dadf7bb4429984011b))
* Handle None job.drive in makemkv.py ([#1665](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1665)) ([0e465ee](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0e465ee495e639df0a760ed1610e5fb15fcb1dc6))
* Harden calc_process_time against non-numeric input, downgrade log to DEBUG ([#1641](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1641)) ([78ab2e9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/78ab2e9c26f8021e8626094266c324fd121a29a3))
* Harden OMDb fallback with timeout and broad exception handling ([#1430](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1430)) ([ed39afc](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ed39afc02bd21226197f7355ea94eb60445fc5b9))
* lint issues ([a1ecbb9](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/a1ecbb912bd4114c3a514d9cb4bfa5b79e37cfd2))
* Log umount diagnostics and improve test isolation ([#1664](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1664), [#1584](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1584), [#1430](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1430)) ([d939362](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/d939362c2998853c6911d4c107f42a93a5ac6943))
* Prevent duplicate file assignment in _reconcile_filenames ([#1355](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1355), [#1281](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1281)) ([c1f6caa](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/c1f6caabfdb5045c323c5382e6e120b536c6eba4))
* Prevent str(None) producing literal 'None' as bluray title ([#1650](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1650)) ([efa139d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/efa139d990815d8472da991eb3ce5069b369d1bf))
* Reconcile MakeMKV scan-time filenames with actual rip output ([#1355](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1355), [#1281](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1281)) ([2623b11](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/2623b116fa1123ad231681c944fd9c2d8ac6f4a1))
* remove executable bit from files which don't need it ([39e8409](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/39e8409deadd4dbfa71b5599d7db48f8b115c205))
* replace hard-coded paths with configurable ones ([824e720](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/824e720e4608cd520b2ae6f38ce4943cf057354f))
* resolve flake8 lint errors ([0c72660](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/0c726609307c8c09a8c3fd06aef5d82c81ba82fb))
* Resolve flake8 lint errors across codebase ([1654f76](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1654f7614776d0e0fe8391d31c22b05859789b27))
* Rewrite Docker publish workflow for dual-registry push ([83adb0e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/83adb0e723ac2d43f8e11d524ba81ae3b0c7a677))
* Set fallback no_of_titles on ffprobe failure, guard None comparison ([#1628](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1628)) ([96697d1](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/96697d13202b84b6bdf7887b768aeb8eaa964808))
* Skip unrecognized MakeMKV output lines in parser ([#1688](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1688)) ([7297893](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/7297893d2e17494f92095655eecb8cc94d519f5b))
* Strip whitespace from settings values, harden git version check ([#1684](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1684), [#1345](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1345)) ([edac6d2](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/edac6d2fd4cc5c69384b0ef03ec928911ab15e56))
* track numbering mismatch causes silent data loss ([#1475](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1475)) ([35f091e](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/35f091eb08791d55f6233b50b7fd6da3938fd58a))
* Use consistent filename in rip_data and harden abcde log check ([#1651](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1651), [#1526](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1526)) ([830a743](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/830a7435156cb53b82ab45ea5e5f442cf3a83b9a))
* Use de-duplicated filename for data disc ISO output ([#1651](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1651)) ([500e89d](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/500e89dc71b9f9999ac15c28f90d853b4d1481a9))
* use job.title to show meaningful music notifications ([1d2d22b](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1d2d22b5f785588a3dfcd244aab46f7ca89ed5a5))
* use job.title to show meaningful music notifications ([754b972](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/754b9727f69f952178d1b41fdfb1fc74b5239091))
* Use list args for HandBrake subprocess to prevent shell quoting issues ([#1457](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1457)) ([4f32270](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/4f32270fdce65ae3e627c53aedf3a1a0634a3026))
* Use total_seconds() for ETA calculation over 24 hours ([#1641](https://github.com/uprightbass360/automatic-ripping-machine-neu/issues/1641)) ([40bf39f](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/40bf39f3acc7f85f22efdc5bb774b39063491678))
* Use Union type syntax for Python 3.9 compatibility ([ffad9c7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ffad9c772da6844eec767df5c3cda570438d2625))

## [2.21.6](https://github.com/uprightbass360/automatic-ripping-machine-neu/compare/2.21.5...v2.21.6) (2026-02-11)


### Bug Fixes

* Resolve flake8 lint errors across codebase ([1654f76](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/1654f7614776d0e0fe8391d31c22b05859789b27))
* Use Union type syntax for Python 3.9 compatibility ([ffad9c7](https://github.com/uprightbass360/automatic-ripping-machine-neu/commit/ffad9c772da6844eec767df5c3cda570438d2625))

## v2.4.6
 - Updated jquery tablesorter, old version was vulnerable to XSS 
 - Removed all unused versions of CSS 
 - Smalls validation checks when searching the database page. (searching now requires min 3 chars)
 - Small changes to index.html (home for arm ui) to warn before abandoning jobs
 - Jquery ui now fully removed. Now uses only bootstrap for theming
 - ARM ui database no longer needs logfiles in url (potentially dangerous), it checks the database instead for the logfile matching the job.
 - Some progress on converting all string types to fstrings where possible
 - ARM will now break out of wait if the user inputs/searches for movie/series.

## v2.3.4 - v2.4.5
 - Adding bypass for db.session.commit() error for movies (WIP only MakeMKV and part of handbrake is coded)
 - Abandon job option added to main ARM ui page (for now this only sets job to failed no processes are cancelled)
 - Typo fixes (ARM ui images has/had some typos these have been updated and corrected)
 - ARM ui now shows CPU temps
 - ARM ui now uses percentage bars to more clearly display storage and RAM usage 
 - ARM ui database page is now fully functional with updated ui that looks clearer and with more details
 - ARM ui database is now searchable
 - ARM ui settings page now fully works and saves your settings to the arm.yaml
 - ARM ui now prevents logfiles that contain "../"
 - ARM ui login page updated to look smoother look
 - Bugfix (ARM will no longer log failures when opening sdx or hdx devices)
 - Bugfix (ARM will no longer crash when dealing with non utf-8 chars)
 - Bugfix (ARM database_updater() was setting incorrect values into the database)
 - Bugfix (ARM ui will no longer crash when trying to read logs with non utf-8 chars)
 - Bugfix (ARM ui will now get the latest % of encode, this was buggy as it was getting the very first % it could find)
 - Bugfix (ARM ui will now correctly display ram usage)
 - Bugfix (ARM ui now correctly deals with setup (it should now create all necessary folders and do so without errors) )
 - Bugfix (ARM ui update title no longer shows html on update)

## v2.3.4
 - Travisci/flake8 code fixes
 - github actions added
 - Bugfix(small bugfix for datadiscs)
 - Bugfix (old versions of yaml would cause Exceptions)
 - Bugfix (db connections are now closed properly for CD's)
 - added bypass for music CD's erroring when trying to commit to the db at the same time

## v2.3.3

 - A smaller more manageable update this time 
 - Early changes for cleaner looking log output
  - Security (HandBrake.py outputs the new prettytable format)
  - Bugfix (Transcode limit is now respected) 
  - Bugfix (Bluray disc with no titles will now be handled correctly and will not throw an exception )
  - Bugfix (abcde.config now correctly uses musicbrainz)

## v2.3.2
 - Added prettytables for logging
 - Remove api/keys from the Config class string printout 
  - Security (HandBrake.py was still outputting all api key and secrets to log file. This has now been fixed)
  - Bugfix (Transcode limit is now respected) 
  - Bugfix (Bluray disc with no titles will now be handled correctly and will not throw an exception ) 

## v2.2.0
 - Added Apprise notifications
  - Added more to the Basic web framework (flask_login)
    - Added login/admin account
    - Added dynamic websever ip to notifications
    - Allow Deleting entries from the db (also warning for both the page and every delete)
    - Added music CD covers (provied by musicbrainz & coverartarchive.org)
    - Added CPU/RAM info on index page
    - Added some clearer display for the listlogs page 
    - Bugfix (Mainfeature now works when updating in the ui) 
    - Bugfix (Job is no longer added twice when updated in ui) 
    - ALPHA: Added ARM settings page (This only shows settings for the moment, no editing)
  - Added Intel QuickSync Video support
  - Added AMD VCE support
  - Added desktop notifications
  - Added user table to the sqlite db
  - Added Debian Installer Script
  - Added Ubuntu Installer Script
  - Added Auto Identfy of music CD's
  - Made changes to the setup logging to allow music CD's to use the their artist name and album name as the log file 
  - Added abcde config file overide (This lets you give a custom config file to abcde from anywhere)
  - Added log cleaner function to strip out secret keys (This isnt complete yet)
  - Bugfix (datadiscs with no label no longer fail) 
  - Bugfix (NONE_(timestamp).log will no longer be generated ) 

## v2.1.0
 - Added new package (armui) for web user interface
  - Basic web framework (Flask, Bootstrap)
    - Retitle functionality
    - View or download logs of active and past rips
  - sqlite db

## v2.0.1
 - Fixed crash inserting bluray when bdmt_eng.xml file is not present
 - Fixed error when deleting non-existent raw files
 - Fixed file extension config parameter not being honored when RIPMETHOD='mkv'
 - Fixed media not being moved when skip_transcode=True
 - Added logic for when skip_trancode=True to make it consistant with standard processing
 - Removed systemd and reimplemented arm_wrapper.sh (see Readme for upgrade instructions)

## v2.0.0
 - Rewritten completely in Python
 - Run as non-root
 - Seperate HandBrake arguments and profiles for DVD's and Bluray's
 - Set video type or automatically identify
 - Better logging
-  Auto download latest keys_hashed.txt and KEYDB.cfg

## v1.3.0
 - Get Title for DVD and Blu-Rays so that media servesr can identify them easily.
 - Determine if video is Movie or TV-Show from OMDB API query so that different actions can be taken (TV shows usually require manual episode identification)
 - Option for MakeMKV to rip using backup method.
 - Option to rip only main feature if so desired.

## v1.2.0
- Distinguish UDF data from UDF video discs

## v1.1.1

- Added devname to abcde command
- Added logging stats (timers). "grep STAT" to see parse them out.

## v1.1.0

- Added ability to rip from multiple drives at the same time
- Added a config file for parameters
- Changed logging
  - Log name is based on ID_FS_LABEL (dvd name) variable set by udev in order to isolate logging from multiple process running simultaneously
  - Log file name and path set in config file
  - Log file cleanup based on parameter set in config file
- Added phone notification options for Pushbullet and IFTTT
- Remove MakeMKV destination directory after HandBrake finishes transcoding
- Misc stuff

## v1.0.1

- Fix ripping "Audio CDs" in ISO9660 format like LOTR.

## v1.0.0

- Initial Release
