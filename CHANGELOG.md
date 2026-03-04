# Changelog

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
