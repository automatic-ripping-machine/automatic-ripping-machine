# Changelog

## [19.1.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v19.1.0...v19.1.1) (2026-06-07)


### Bug Fixes

* **ui:** stop transcoder/dashboard elements popping in on load ([dea14e2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/dea14e26e84af0135475cb3d11e23101a981ddf1))

## [19.1.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v19.0.0...v19.1.0) (2026-06-07)


### Features

* **demo:** add ARM_UI_DEMO_MODE for isolated UI with seed data ([b5c998c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b5c998cf33afca32414aaa02428ddc0337019c18))

## [19.0.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v18.2.0...v19.0.0) (2026-05-27)


### ⚠ BREAKING CHANGES

* **notifications:** remove legacy flat-config notification fields from settings
* contracts has breaking commits in this bump. Review the commit list above and verify consumer code still compiles before merging. release-please will cut a major consumer release when this PR lands.

### Features

* bump components/contracts to 5e9a6c2 ([742af1e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/742af1e4ffcb6dbe38443b0b491cbd1b56368b4a))
* **notifications:** add channel status/time/label helpers ([277a561](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/277a5612f4034ef59b665c67419aa847069dc8f5))
* **notifications:** add ChannelList container ([823b2dc](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/823b2dcd7d891d86592a2c354e2361fe8cfcfa9f))
* **notifications:** add compact ChannelRow ([932f6c3](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/932f6c3996083963fd57fea2ae2722fb8f7ea7a4))
* **notifications:** add FilterPills ([bdb542a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/bdb542a273e0f900d635db2cdd6ebb43bf6722fd))
* **notifications:** add form readiness helpers ([942ae6e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/942ae6e392f0d8e7b3fb5ef3ec3d1a4382b35ee1))
* **notifications:** add global toast store ([e0b314a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e0b314af1f024f1435c6e1046a7e7cd458212db6))
* **notifications:** add inline ChannelEditor ([f962470](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f962470348ab7f138243c7b78db38e5210cf9ef8))
* **notifications:** add NotificationsTab orchestrator ([4004f42](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4004f42af29e03167c5fe522e81575f2db49ff6f))
* **notifications:** add preserveExisting flag to ConfigureSection ([dfced7a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/dfced7aa6a88d3f5c7e3dd5c056dfe250859bf64))
* **notifications:** add ServiceDropdown with featured + search ([302f0e1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/302f0e14f161cdf2eb57cd7c793280234bc9a49e))
* **notifications:** add ServiceGlyph monogram ([025f45d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/025f45d0f136e0223a799be0c1c4e40eb218a2f9))
* **notifications:** add shared Configure/Events/Templates sections ([94f4d3f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/94f4d3f053e00a48081377b9061d4e1ed7bdd674))
* **notifications:** add StatStrip ([e6dbb30](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e6dbb3088d780f1313fcb8d9fdc67de775a8a974))
* **notifications:** add StatusDot primitive ([c2df0cd](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c2df0cda8ca964a5b15437df447af36bf60bc21e))
* **notifications:** add ToastHost renderer ([6512cee](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6512ceeca33a6e22f02454b5d137c2d7ddb5f80c))
* **notifications:** add Toggle primitive ([a499fe8](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a499fe846c8fa9cc907ff6414e1485b7d2efcbc5))
* **notifications:** add unified AddChannelForm ([425eb9a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/425eb9a17edb3857da931e8dfc623bb93a330f15))
* **notifications:** Add-channel as a button below the list, form hidden until clicked ([de9889b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/de9889b106c9ce6ec7268cd600960c80f8612afb))
* **notifications:** arm_client proxies for channel/catalog/dispatch endpoints ([ceac74f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ceac74f63418d457464d1d4d60420415e088ca25))
* **notifications:** BFF passthrough routes for channels/catalog/dispatch ([d48c50c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d48c50c0c16b85a954c3b1b2f868f61e9a27855d))
* **notifications:** channel edit view with test-send polling ([6092270](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/60922708e8506293015fe018ca5ebfd83fdfce14))
* **notifications:** ChannelCard list row ([2c30adc](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2c30adc7db730f19ad527bccaa412ac8aff8bbf1))
* **notifications:** channels list view ([2c617a9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2c617a9feefdb1d8361690942b7e259ca1188fa5))
* **notifications:** click a variable chip to insert it at the caret ([a1cd0b2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a1cd0b2dcbbaa6a6ee077a0f4e2aa55a0ef6890d))
* **notifications:** create-channel flow (apprise/webhook/bash) ([88cbaaa](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/88cbaaa52368b510442e21070823f9b27790856b))
* **notifications:** DispatchHistory pane ([1837a7d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/1837a7d366b615b8fc2accd8490d271d2e05304a))
* **notifications:** editor renders apprise fields via service_id ([9faaf77](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9faaf77d82c1d02343423a41e5bd310fd83edb39))
* **notifications:** editor save sends {service_id, fields} for apprise ([1f5641a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/1f5641a3385a54b7356ff23bf3252b198ac2b664))
* **notifications:** editor seeds appriseFields + raw-URL guard ([e8677f4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e8677f4158d208ea044dd1f48c07afa8894661e4))
* **notifications:** editor test-send via channel_id+fields when dirty ([8ec51ff](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/8ec51ff3917fc8921a3fe1f00a6b8b4576ca0cd4))
* **notifications:** editor unknown-service guard + apprise test-send branch ([bcea653](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/bcea65355785d62e7763be79b17c2d2860339b3d))
* **notifications:** EventSubscriptions checkbox group ([a3c27e8](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a3c27e8caaf4f24737563112cc60b1d19666b986))
* **notifications:** frontend channels API client ([a0f5df9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a0f5df9eb1daef6413f8346968ed996a83c658c7))
* **notifications:** hand-written frontend types for channels + catalog ([064caee](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/064caee39564344dd3d88ebd7f6bcb67d7e0ea40))
* **notifications:** inline channel panels in settings Notifications tab ([50949d1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/50949d1191d07284cdcd5c0972fbf316b3c4c719))
* **notifications:** make service selection a searchable dropdown ([37a6300](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/37a6300b4e952bb63b756f3b1b74b6ab26d87d97))
* **notifications:** move Channel Label/Enabled above the service picker ([12d134f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/12d134faa20e6bc11f82db9f5db5ec3ae6f6ff32))
* **notifications:** per-event TemplateEditor ([9caeb89](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9caeb899c084f057eda87083e3abec90cd243650))
* **notifications:** persist service_id in created apprise config ([28afd88](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/28afd88e4f8e607e823b2d57832334cb2a925674))
* **notifications:** recompose apprise url from editor fields on save ([6265d09](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6265d09cab08a1f39076fb85f4c564624f0b408c))
* **notifications:** remove legacy flat-config notification fields from settings ([351fb14](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/351fb14be1a28a0d7d5ec41ff1e7e11e944d6394))
* **notifications:** reorg apprise card — required + collapsible advanced ([487e6e7](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/487e6e759060d1b4cab7420a9dcde2d13b6abac5))
* **notifications:** schema-driven SchemaField component ([4c4833a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4c4833a94acb9b3150d9a2cf001cb7a5901b96c0))
* **notifications:** SchemaField treats &lt;hidden&gt; as keep-current placeholder ([d6f75df](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d6f75df8a7aed48a0f54c5f0a46b1b6a31b325c3))
* **notifications:** searchable service dropdown + form polish ([00f788d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/00f788d968da46bcaab2964a2ef534e9e5c94976))
* **notifications:** ServicePicker with featured + search ([08ba10e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/08ba10e60b3e19c4fae9d8f76e5c4505797074ac))
* **notifications:** surface default templates as placeholders ([bfb2d85](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/bfb2d85b5e0ecf1b5ad8db0837612c73ee823284))
* **notifications:** Test button on the Add-channel form ([e1ac316](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e1ac3169b08ba8924f2873d24bc5ac8977399b03))
* **notifications:** toConfig sends {service_id, fields} for apprise ([2586e75](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2586e7527084ea6138bec8720e4dfe836b715a57))
* **notifications:** wire redesigned NotificationsTab into settings page ([e3c99e1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e3c99e122b6a827d078bca551b60bcbfaf94c107))


### Bug Fixes

* **bff:** handle empty 204 response body in _request (channel delete returned 500) ([c9afd83](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c9afd83c94dbbe7100e2d1a0ba4c14b650572a81))
* **notifications:** align channel-list column headers + style Close button ([65868f4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/65868f4c4e5febee0311f9115af711062a3982d6))
* **notifications:** editor Send test uses the edited config ([d09ad74](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d09ad74dcbf80a9443589ea682778023b24183d5))
* **notifications:** hide redundant Events legend in shared section ([12d4541](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/12d454173b06315364e101bee04ee9b8cb459a7b))
* **notifications:** percent-encode service_id in compose-url path (SonarCloud SSRF) ([4d802cd](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4d802cdb87dca2d33c3191af494f63f386f06a51))
* **notifications:** poll dispatch status on test-send ([a13cebe](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a13cebe5c4f7582fa11e877c8c7492441deb4bab))
* **notifications:** stop double scrollbar when channel editor is expanded ([f4c2f53](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f4c2f539b2a7aa33a53f7ff9ff41e08b402676a9))
* **notifications:** theme inline UI, add occurred_at var, validate required inputs ([464bdc4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/464bdc4a03b5ac87ac75febffc8291b99fb2313c))
* **sidebar+settings:** debounce arm/transcoder offline flag; stop double-scroll on tab click ([901e42c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/901e42c4950b38ad6f46c0ba0cad9dff67c4322d))
* **sidebar:** raise httpx keepalive_expiry past poll cadence to stop flicker ([88191e5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/88191e52b7c27e134a83b87a4999bcd841c6070e))

## [18.2.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v18.1.0...v18.2.0) (2026-05-18)


### Features

* **bff:** /api/jobs/{id}/metadata + /api/patterns/tokens endpoints ([82039c4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/82039c445ce68c1076f269636d0116fc93050e57))
* **ui:** pattern editor shows all PATTERN_TOKENS, sorted alphabetically ([18cd3fd](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/18cd3fd9d55491ae8193b558cd6b091fcea1ad14))


### Bug Fixes

* **dashboard:** render 0% progress bar instead of indeterminate spinner ([be1af65](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/be1af65e3345c1bb3114a540e03e8ec7fd4217e0))

## [18.1.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v18.0.0...v18.1.0) (2026-05-10)


### Features

* **presets:** HandBrake preset picker fed from transcoder endpoint ([260264e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/260264e0544d72f1e432dc83ccb9f75badcf12cc))
* **progress:** BFF surfaces copy_progress and copy_stage ([3a21d32](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/3a21d3250b3a945bdb752b51b456cbc89a65bdf8))
* **progress:** render copy progress on dashboard for copying jobs ([e19178f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e19178f3ff67c04e20d697b1a3ca136d6a891536))
* **settings:** show arm-ui webhook secret status alongside transcoder ([96a6833](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/96a68332b71828de60598cc1c27c51a943858086))


### Bug Fixes

* **arm-client:** raise test-metadata-key timeout to 30s for makemkv provider ([56137eb](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/56137eb3134ccd25ee66e3c1f0efc0484557ee15))
* **jobs:** drop void operator in deriveLifecycle, prefix unused param ([df91801](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/df91801208d647ed5af306d9e9cc8a2302380fdf))
* **jobs:** folder imports use the disc 5-stage lifecycle ([83a94a0](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/83a94a0c4056dcf346c436df585b0d8235a1622e))
* **jobs:** hide Episodes tab on movie jobs (gate is series AND imdb_id) ([b2d22e6](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b2d22e69982c2d44140dc9038175931c096dd109))

## [18.0.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v17.5.0...v18.0.0) (2026-05-08)


### ⚠ BREAKING CHANGES

* contracts has breaking commits in this bump. Review the commit list above and verify consumer code still compiles before merging. release-please will cut a major consumer release when this PR lands.

### Features

* bump components/contracts to 37d3fd4 ([23dd718](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/23dd718952e061a3b987bc7f0296e9fb82f0a73e))
* **iso:** BFF proxy router for /api/jobs/iso endpoints ([a4f6b3e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a4f6b3e4170e41cdc52bce8e8c2654a7e44ec174))
* **iso:** unified Import wizard with ISO file support ([cef9351](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/cef93515c568e7118516cdaeb361043a2c1e9e35))
* **ui:** split fallback into Video and Disc pills ([2dffdcf](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2dffdcf2c5eb66bbdcca8f2758e7243b1706d86a))


### Bug Fixes

* **dashboard:** show transcode % on All Jobs card ([2c7cba1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2c7cba1281f8a33565428c42aeb1bd53994611f9))
* **quality:** clear SonarCloud gate failures on main ([25ed68e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/25ed68e2e3f333e8b6027fbc73fd01a93efa1b0a))

## [17.5.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v17.4.0...v17.5.0) (2026-05-04)


### Features

* **ui:** job-detail lifecycle as title-above-bar blocks below header ([5de7fbc](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5de7fbce81f41bbdc47b3eb7ae95cdae48ec8285))
* **ui:** visual job lifecycle widget on dashboard cards + detail page ([7b2c7f2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7b2c7f2bf0e81d0c27acd66b17b797f520822415))


### Bug Fixes

* **settings:** drop non-string comments entries before model validation ([006dbdf](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/006dbdfe224af1c1d576f915ae7e118584a1d555))

## [17.4.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v17.3.0...v17.4.0) (2026-05-04)


### Features

* adopt arm_contracts v0.7.0 (JobState/SourceType/TrackStatus/WebhookEventType/SkipReason) ([dc5db5a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/dc5db5aff48c32829a52fb910479f6b28629232c))
* adopt arm_contracts v2.0.0 JobState disambiguation ([77fdd11](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/77fdd116810cc60767e62abdceb266f572e574f4))
* **codegen:** add FastAPI -&gt; TypeScript codegen pipeline ([c77401a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c77401a458579455390f3d1cb815e71c1d7f5926))
* **disc-review:** apply backend skip_reason truth to DiscReviewWidget too ([fb08d0a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fb08d0a60aee52ec9bb2bb15ef8f78b85383b76c))
* **home:** redesign active rip + transcode cards ([80c9e6a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/80c9e6a0bcd5a41ac6b082b91df75a4369d46bc1))
* **home:** replace Elapsed cell with computed ETA on active cards ([9b5c3f4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9b5c3f4f3d2f407b502f031633f1d2c4460e8927))
* **jobs:** render disc-review filter state from backend skip_reason ([1aa78bd](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/1aa78bdcf31f9ce970b2a6e874150ef7a6d4c787))
* **models:** add typed BFF response models, response_model coverage ([2d74332](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2d74332d31cdb811c566ff41dc043f63e5995729))
* **theme:** add status-color tokens + statusAccentVar helper ([c319b12](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c319b12df33a1924154c50915a6242578741258b))
* **types:** tighten BFF response models for accurate frontend types ([38be943](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/38be943acbfc0e5d3c5d828c65613da7da84d4b0))


### Bug Fixes

* **ci:** unstick codegen workflow + sweep leftover legacy type imports ([909646b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/909646b8513d52eac14660ebae1f27cb04f2ddcb))
* **dashboard:** bucket disambiguated wire strings in waiting/ripping filters ([6b395be](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6b395be79f062e823de58ba61dd8a17fc432e0e2))

## [17.3.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v17.2.0...v17.3.0) (2026-05-01)


### Features

* **phase:** surface transcoder sub-status on job detail page ([d8514b7](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d8514b7e6b8c9a0f944724b738fe53abc8d0e0e1))


### Bug Fixes

* bump components/contracts to 67eba7b for rip_progress float fix ([120d90e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/120d90e2f9f87638b06454f8b276c008409ea889))
* **jobs:** purge redirects on detail page; bulk-purge pages under per_page cap ([e254d03](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e254d03ccff15490042be819399a274d7a1053ac))
* **security:** strip CRLF from user-controlled values before logging ([18d51e9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/18d51e9a4141d0e59042e42b7155ae405064bf91))

## [17.2.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v17.1.0...v17.2.0) (2026-04-29)


### Features

* bump components/contracts to 1f17568 ([be0a1b2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/be0a1b26598a9773e0e32242304bb9defd60d2c7))
* **folder-import:** split OMDB match into its own step ([dadf30f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/dadf30f3f939e320e194149827b05b065569bc67))
* retire last ripper bind mount via arm-neu logs API ([171888d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/171888de287cd6b6dec2321491ccbd364b99bf8b))
* **schemas:** adopt shared Job/Track/JobSummary contracts (Phase C) ([2368947](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2368947cd0a6521d3231440cf846dcedbafe29ae))
* **settings:** scale Versions card columns to entry count ([46de78d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/46de78dafcf00ec15689bc8a4d608af7c30aa7c5))
* **settings:** show transcoder GPU vendor under version ([741db61](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/741db613e2ad4659b36950aedc50cd4f84e24987))
* **version:** stamp build identity into VERSION at image-build time ([5669fc2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5669fc248bd19460eff1c0f9feba868ff6e96614))


### Bug Fixes

* **dashboard:** degrade ARM endpoints per-field, sticky-merge in store ([7c1714c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7c1714cb6c36c06355c50f97c3a7f9d196913b82))
* **preflight:** bump BFF timeout 30s -&gt; 60s ([933ebed](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/933ebedc234fd310b7fd0286cac3630e7b6424b8))
* **settings:** null-guard transcoder_config in Logging block ([40eb1f2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/40eb1f2a77fdca1808b47d451b71628883c4de06))
* **settings:** UI polish on transcoder Configuration tab ([4822935](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/482293507c051a7a2c55b3b7b1090c178ffd0846))

## [17.1.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v17.0.0...v17.1.0) (2026-04-28)


### Features

* decouple from ripper-side bind mounts ([89ebb13](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/89ebb13971709f64a678a7c452443e1afbd135bc))

## [17.0.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v16.5.1...v17.0.0) (2026-04-26)


### ⚠ BREAKING CHANGES

* The BFF response schema and runtime contract change in several places. Any external consumer of the arm-ui HTTP API or anyone overriding the published compose/.env must update.

### Features

* drop direct DB reads, talk to ripper over HTTP only ([7e05dfd](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7e05dfda5432b35dda4870c55430837cd7a9e089))


### Bug Fixes

* **security:** contain progress-file paths under arm_log_path ([a6abbc2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a6abbc2dc0e2991d8d2046e1ee0f233c550063f7))

## [16.5.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v16.5.0...v16.5.1) (2026-04-25)


### Bug Fixes

* **settings:** add breathing room below tabs + normalise heading spacing ([bd9b6cd](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/bd9b6cdaf4f3de5218465cd5e3d11ad641b3d73d))
* **settings:** even spacing between Transcoding tab heading + description + first section ([ad0386e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ad0386e38374ad53033e1272dc1af107e1b19967))
* **settings:** polish settings page layout ([2747dfc](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2747dfc69c0da8910cdb20c0f5de4de87834e88c))
* **settings:** wrap Transcoding tab body in space-y-6 ([0b57e4d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/0b57e4d6e977573480ae59ad5330abbcef588bfd))

## [16.5.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v16.4.0...v16.5.0) (2026-04-25)


### Features

* **transcoder:** surface current encoder FPS during transcode ([9864b3f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9864b3fc63641fbbe4f0405f21ac332fe8398aa8))


### Bug Fixes

* **jobs:** skip loading flicker on poll-driven refresh of /jobs/[id] ([f2d2e3b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f2d2e3b3fb7a0e6ff4dfdb8bb2e9865316f2a0c3))

## [16.4.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v16.3.0...v16.4.0) (2026-04-24)


### Features

* **mobile:** responsive enhancements across tables, layouts, drawer ([25a8756](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/25a87566bd1cc3ec0cb575b14ac489c504f03267))

## [16.3.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v16.2.0...v16.3.0) (2026-04-24)


### Features

* **config:** add /api/config feature-flag discovery endpoint ([b554ed6](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b554ed66177d87a3cc65cc17aa86fabe1115b342))
* **config:** add transcoder_enabled flag (default true) ([d1d1c51](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d1d1c511337d980ab1bf73afd708cf2ada4a526a))
* **dashboard:** short-circuit transcoder fetch when flag disabled ([f8faeb4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f8faeb47e2f2ca27a2a71ba6d9a0b5a298d662cd))
* **deps:** add require_transcoder_enabled guard ([6c7bd9d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6c7bd9dcc81d850223008e97b3cc58d5685f23e0))
* **jobs:** gate transcode-config and retranscode behind feature flag ([ac624d0](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ac624d06c9ca4ad260c2016485b4f7901bfe7cfa))
* **settings:** gate transcoder-scoped endpoints behind feature flag ([f0db30a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f0db30a923a0e25fcc06cd5519d882844ca2f9f3))
* **settings:** skip transcoder config load when disabled ([736417f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/736417ff95001176ec1bc49235c8b5cd9da573ff))
* **setup:** hide transcoder surfaces in new-user walkthrough ([1207334](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/1207334644a755d8ba0ede8a9ebdd7af5ce8dd36))
* **transcoder:** gate all /api/transcoder/* behind feature flag ([81a47b0](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/81a47b010fee57fc69bcea7670df48e03c6c3ef9))
* **ui:** add transcoderEnabled store hydrated from /api/config ([fc29554](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fc2955488560c2da96e8aa9e08451d55e50b31f6))
* **ui:** filter transcoder from nav + quick actions when disabled ([fe9c94b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fe9c94bbdec5643613cad52aaa801bca96935db5))
* **ui:** hide dashboard transcoding section when disabled ([bc3f2f8](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/bc3f2f83e480876f012d3f7e51d944661603393f))
* **ui:** hide transcoder settings tab + subpanels + SKIP_TRANSCODE when disabled ([78fa040](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/78fa040d582f65110f4a6fca112120603affb42a))
* **ui:** hide transcoder status in empty dashboard panel when disabled ([a3e198b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a3e198bed5b50bf66b05077ec9c13ec23893baed))
* **ui:** hide transcoder surfaces on job detail when disabled ([abdbb8a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/abdbb8af2f6ff05eebd2e4a949fd6094e3cf21cc))
* **ui:** hide transcoder tab on logs page when disabled ([c8c38c2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c8c38c251b1ec514b39e43aabc735b24111d0784))
* **ui:** hide transcoder+gpu panels in stats bars when disabled ([5894ba4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5894ba40458f8c1675291cef6b0b5ea9d74b66f3))
* **ui:** hydrate transcoder-enabled flag from root layout load ([43c8ba6](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/43c8ba627d84529b8aa8426093f37d75c3c5348d))
* **ui:** redirect /transcoder and /logs/transcoder when disabled ([3c89188](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/3c89188b77c3284632a6258c91102969e2deae7d))


### Bug Fixes

* **arm_client:** bump preflight timeout to 30s ([6504e2f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6504e2ff70a1e209c3d75e7b11eddd0a49851a64))

## [16.2.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v16.1.0...v16.2.0) (2026-04-24)


### Features

* **frontend:** add EmptyDashboardPanel extracted from dashboard inline markup ([3d6b051](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/3d6b051fdb681d819f043e723badffe9ede36940))
* **frontend:** add LoadState wrapper with minDelay and error handling ([a625b99](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a625b99fb249a4fdcf26f922729828adc0737985))
* **frontend:** add Playwright visual regression harness ([e2d4f2b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e2d4f2ba956f3bda41a7c93ff59f30a2528a655f))
* **frontend:** add Skeleton primitive with theme-aware colors and reduced-motion ([856d282](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/856d2822535b27059d7d0e5d3a6cc15c6381b548))
* **frontend:** add SkeletonCard composing Skeleton primitives ([7bc7ea7](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7bc7ea75f93364cb59e4d4ee744fb0f8938a6720))
* **frontend:** add transitions module with reduced-motion support ([6d4a6da](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6d4a6dac24571cb3902b739c3b0e96df2ac72e79))
* **frontend:** cache theme CSS in localStorage for instant second-visit paint ([dcf6dea](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/dcf6deafef3e5410732c49aef868bb4d190333fd))
* **frontend:** make ActiveJobRow self-skeletal ([b369f53](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b369f5350c6275bce9aafa17ee3fd75aa88f4db7))
* **frontend:** make DiscReviewWidget self-skeletal, replace ad-hoc skeleton ([4b8dcbd](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4b8dcbd5b4bce76515c9c7113a12f8661b92b991))
* **frontend:** make DriveCard self-skeletal ([ccb73c9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ccb73c9c39b880156f2e55faca6258b9bfcda292))
* **frontend:** make FileRow self-skeletal ([0d6c145](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/0d6c145be600c6f12581cf627d865d797a0dde33))
* **frontend:** make JobCard self-skeletal ([c92851c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c92851c3f21d057a993bd1bd2bd00791a65c7bd6))
* **frontend:** make JobRow self-skeletal ([69fd91f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/69fd91fbeca5c3064b586d05dc97c7ca082c1c08))
* **frontend:** make TranscodeCard self-skeletal ([f634623](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f634623af278f14bd86def149d00bfba6cc778e7))
* **frontend:** migrate dashboard to LoadState + fade transitions + EmptyDashboardPanel ([80f4547](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/80f4547ed7389d36015ec1b8dc88f2c5f90d78d4))
* **frontend:** migrate files route to LoadState ([814c558](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/814c55872e6b957621677212ab13c6f3915a85ab))
* **frontend:** migrate job detail route to LoadState ([da27282](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/da272820c4688945d25f195245face715564adb8))
* **frontend:** migrate logs list route to LoadState ([3a781c8](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/3a781c85b908eda47f9ff5ab348b69f4331edb0a))
* **frontend:** migrate notifications route to LoadState ([163a3a2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/163a3a260189ff476cf08891fb30b74586d66d05))
* **frontend:** migrate settings route to LoadState ([512b858](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/512b858b0c0b7e4d48e90841ba5d64a528840027))
* **frontend:** migrate transcoder route to LoadState ([d09ce2d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d09ce2d1baab4412a33ea6a2f29e834111e98358))
* **frontend:** show em-dash placeholder when stats are missing ([1e2d2ce](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/1e2d2ce5bfdcbce708613039da0d071d764d2fb7))


### Bug Fixes

* **frontend:** dedup theme CSS fetch with in-flight promise guard ([2c95bf8](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2c95bf8b24090f5c6e0e3ebbc5add76fea5286eb))
* **frontend:** restore visual status indicator on DiscReviewWidget header ([4dcef8b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4dcef8be0513911eaf414ab7a867c532d666c5f3))

## [16.1.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v16.0.0...v16.1.0) (2026-04-23)


### Features

* add arm-contracts as components/contracts submodule ([09c2fd0](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/09c2fd035605f3c9241421702b3ab6e65000b07b))
* validate transcode_overrides via TranscodeJobConfig ([9adc530](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9adc5306a00a184857533f50c2de754c59e60901))

## [16.0.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v15.4.1...v16.0.0) (2026-04-21)


### ⚠ BREAKING CHANGES

* Encoding settings section replaced by scheme-aware preset picker. TranscodeOverrides uses preset_slug + overrides shape. Old flat field controls removed.

### Features

* add force-complete UI for marking stuck jobs as success ([88bafd4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/88bafd457196cd8cc3aa07b9a493ae73be567b6e))
* add Skip & Finalize button for stuck transcode jobs ([fb57f24](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fb57f24a5b5c8681b9c9f1b0f8a1f2c50e7b73d2))
* add SKIP_TRANSCODE global toggle to settings page ([01ae948](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/01ae948acfe27f1820f23b91ef0aa51ad95d7c06))
* add SKIP_TRANSCODE toggle to review panel ([0f84337](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/0f843379ba58922a4fde3a31086abb86dfe82416))
* **backend:** add preset CRUD client methods ([739f74a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/739f74a3f03947d02580dafd9d32c8d24613d92d))
* **backend:** add preset CRUD proxy routes ([fe1484f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fe1484f3a11fb925af9052e287322d83d0b5454d))
* confirm dialog before skip-and-finalize ([fef8cd1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fef8cd167c0117558a2fe1ca3f0bdb50f0b3dca7))
* **frontend:** add preset API client functions ([d204f75](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d204f75cc6a5afb962a3c217df49be6504a2dee7))
* **frontend:** add preset/scheme TypeScript types ([3df5820](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/3df5820c339fa0325d3d2c6cf1ba534aebb2dd8e))
* **frontend:** add save bar with Save/Save-as-new/Revert ([9b160c2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9b160c263811e8bdb116ea3642c96338d2e5ea3a))
* **frontend:** customize panel with shared + tier rows + dirty highlighting ([ea5f9b1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ea5f9b1148f839e9a1f24f0b9f32dd0a64dfc936))
* **frontend:** edge cases - saving lock, unavailable warning, undo toast ([229adc3](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/229adc3898088bf17175c031264052675709f377))
* **frontend:** preset dropdown with built-in/custom/unavailable groups ([a20607b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a20607b12fec0a1c70a72034ecda029e80550228))
* **frontend:** replace encoding section with PresetEditor in settings page ([515198a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/515198ab5e3c736935e103728f86a4d720fdd401))
* **frontend:** rewrite TranscodeOverrides as PresetEditor wrapper ([2c3cefb](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2c3cefbf5b3c3bb7e530326a57eb22aa07f661e6))
* **frontend:** scaffold PresetEditor component with scheme header ([5b48e4d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5b48e4de8e097d291278b86c6a7bbe8ae6b8cffb))
* job progress widgets for rip/copy/transcode phases ([30335ff](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/30335fff224fa4fb18e5d51921f8167f9f116be7))
* log filter UI in InlineLogFeed ([0742be8](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/0742be8f214a1e898010c8c445bf07a5fe67d24e))
* preset picker and SKIP_TRANSCODE UI (breaking: replaces hardcoded encoding settings) ([6699162](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/669916215d3104e9ead84a8bfcce293d921579a1))
* support {show} and {episode_name} naming variables in UI ([73aaa93](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/73aaa93c5161f2c005bc22b960ec1b87b191cba5))
* surface SKIP_TRANSCODE in UI settings schema ([f8ca59e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f8ca59e8665fe426385e9d524b6f421fa146dd06))
* update UI backend for new preset system ([9801377](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/98013771e2cbbb82372b93676d7c006e0a3c134b))


### Bug Fixes

* **backend:** broaden offline catch + improve preset CRUD tests ([ed6dfb5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ed6dfb50d4d348acd74d18bfa0747084a70680b2))
* **backend:** NoReturn annotation + complete preset proxy 4xx test coverage ([47e39e2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/47e39e25c4b9ee1f3d142f2fd80e9108404cc832))
* extract transcoder-unreachable constant and document 502 responses ([fb5ec54](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fb5ec54b12e7125f49f494ad62b8e7725979d58b))
* filter legacy transcode_overrides keys on read ([ede6973](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ede6973c0c97980725c2720f091a458e23b41aca))
* **frontend:** default to first preset; hide preset-managed fields from operational section ([2063b10](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2063b1055967bfd511ee4678a54a4c5c61c0a427))
* **frontend:** PresetEditor cleanup - timer leak, save-as-new error contract, Number('') bug, missing tests ([c01f233](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c01f2335910f52fec8ad1f0bb62b145915b82152))
* **frontend:** tier field falls back to preset.shared when not set per-tier ([b0ba40a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b0ba40abd34fe3e5550b0a7a4a5dfa502217abc0))
* **frontend:** use 'Save changes' visible text on save button ([ec677bd](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ec677bd74fb65e76e18f8af002c06a66d080f089))
* hide title override search for tracks below MINLENGTH ([2a1172f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2a1172f191a1ca9f24b7974fa845f4f1f873880d))
* **security:** validate preset slug before building outbound URL ([54a1ce9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/54a1ce92ec56f4c9b64f77d5c40358a585c17f87))
* skip-and-finalize UX polish from code review ([afa513f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/afa513f513f242e3223eff9bc7451faa688655e6))
* snapshot $state proxy before passing to fetch to avoid DOMException ([a817ae6](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a817ae6af6c6012bf6b774d10c9a1fd36cf1ccd2))
* snapshot settings.transcoder_config before derived preset state ([fa846e3](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fa846e30db786177fde035ba754f6cd210a50250))
* strip legacy transcode_overrides in JobSchema serialization ([5e2b6a9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5e2b6a9517edca80d7d3d1a8e4dcd4234e12b44a))
* surface 4xx/5xx from transcoder update_config (previously swallowed as 502 'unreachable'); style Save-as-new-preset as button ([6559f03](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6559f0383db7b75fb856af37c4f45a195a700497))
* tracks_total excludes disabled tracks ([92bf9e8](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/92bf9e8c0f163482851071cf7a4c67574a61cb02))
* transcoder log panel correlates to correct job ([23796bd](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/23796bdb717cda435b0bcaae60b7574787532d49))
* use pytest.approx for progress field float equality ([ca03d12](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ca03d12cb74e1c6664502e027f75a5c55d95f19a))

## [15.4.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v15.4.0...v15.4.1) (2026-04-14)


### Bug Fixes

* stop poster image flicker on dashboard polling ([ce88d4e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ce88d4e3585aa4b0cc5794255a5598f7c437994e))

## [15.4.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v15.3.0...v15.4.0) (2026-04-14)


### Features

* add Force Rescan button to drives settings ([e970e7d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e970e7d48ae7c4de8503cd88b1bece276212b598))

## [15.3.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v15.2.0...v15.3.0) (2026-04-13)


### Features

* add CD_RIP_TIMEOUT to Music &gt; CD Ripping settings panel ([ad592de](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ad592de169cc334bfc02aeef3284a4e3654fecf9))


### Bug Fixes

* add disc_count to MusicDetail fallback objects ([b30b917](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b30b917c50b155e4584f1e818fd8b432ae76321f))
* align music progress tracks_ripped with log-parsed tagged count ([853fc59](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/853fc599d8f2d05757e8683f4bd08a98f28f34b8))
* centralize track counts from progress poll, not stale DB query ([4a11ed3](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4a11ed380ccfd6f73e6f231347ba1882d80c1ceb))
* filter MusicSearch tracks by disc_number for multi-disc releases ([2da94e9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2da94e9c7820f3eee0a4c9efbf8a25aa9b919f80))
* filter track comparison view by disc_number for multi-disc releases ([52b9d8a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/52b9d8abbbbd08d1a45f2ef349d70e8ea6295b27))
* null guard .trim() on drive settings to prevent TypeError on empty values ([773ab65](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/773ab65a8c2db146fb7b48c42922b68a819d3bc3))
* redirect to home after job delete instead of removed /jobs page ([374a9bf](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/374a9bf5941b8c09aee096658f91bfc3b95e5aa8))
* reduce test code duplication below 3% for SonarCloud ([735b93b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/735b93baa5aeb9dabe3199f4127df9ae0a7f5282))
* skip minlength filter for music disc track counts ([8d111da](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/8d111dab7055ee2cd7f235913d5e81e74d187926))
* use encoding count for music progress — tagging overcounts by 1 ([5d42376](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5d423768366c433f7e64b404e91e1964e991a1ae))

## [15.2.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v15.1.3...v15.2.0) (2026-04-11)


### Features

* disable file actions on read-only mounts ([c108534](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c108534e7908a42b137b1264572915a7dc6fc33d))
* show read-only mount banner on files page ([a2d1d86](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a2d1d86b8a618707596191b940ecd5e5adb98b19))


### Bug Fixes

* file browser root tab highlights most specific matching root ([4af2721](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4af272104868abe149408109b44dcee415f5a6fc))
* move pageReady declaration after jobsData to fix svelte-check ([953b162](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/953b1625ec294fe4fa74ff64a4456bc2e1abf35b))
* reduce dashboard loading blink and layout shift ([2072c37](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2072c3749286347869ba9aa3a6839e7c378547c2))
* replace filter pills with dropdown selects on dashboard ([8b05efd](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/8b05efd10f618d7142d401d6dd11007b14c53298))
* topnav ripping count excludes jobs in transcoding status ([1933017](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/193301777a65e7c58d70e8cb19308b51e600d114))
* unify poster placeholder across all components ([cf8cb3a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/cf8cb3ae480f70616055f1aec3b98a0c15ea4c3c))
* use disc icon for missing poster art across all views ([fe0d0a1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fe0d0a141dd1ddbf790f8f86c108ebaeacf78e04))
* use PosterImage on job detail page, add style prop ([ed90012](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ed9001227793652487233a6845c00b63dde25ec6))

## [15.1.3](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v15.1.2...v15.1.3) (2026-04-11)


### Bug Fixes

* add missing poster placeholder SVG ([dbad9a3](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/dbad9a3118ba4f59d5c67067be06ebb697eae002))

## [15.1.2](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v15.1.1...v15.1.2) (2026-04-10)


### Bug Fixes

* hide InlineLogFeed when log file returns 404 ([56b78d6](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/56b78d62399e523652c36dba1d086b0f8e105eaf))

## [15.1.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v15.1.0...v15.1.1) (2026-04-10)


### Bug Fixes

* stop InlineLogFeed polling after 3 consecutive 404s ([04e0fb2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/04e0fb28d73571b7fbad68d72c96130d2821d3cb))

## [15.1.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v15.0.0...v15.1.0) (2026-04-09)


### Features

* add buildMetadataFields utility for job detail header grid ([2cfea60](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2cfea601b35be9fa27a5be204f77f58d784ef03f))
* add per-drive prescan settings to DriveCard advanced section ([35bde2c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/35bde2ccd663a2b7e37449f1f2e6645ee7d57478))
* add prescan override fields to Drive type and API ([c0e56eb](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c0e56eb7bfcfabf2cb341e30f631fab8426a4579))
* add prescan settings to global MakeMKV settings panel ([af2ff86](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/af2ff8649112f9e19eb8da5d83c4f3fb9fc13ba0))
* consolidate job actions into single action bar below title ([2ab38ae](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2ab38ae529f8f747577a1dc6d1524f1867774edc))
* editable episode number per-track in review widget track table ([9237720](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9237720f694c0b8e6405ae8cac8581da938fb6f4))
* editable episode number per-track on job detail page ([1bb16ea](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/1bb16eac6abfff8d38ae8b6b3af963c4a16d8161))
* editable filenames on job detail page matching DiscReviewWidget ([8c14d33](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/8c14d3336ac92d18caf78cc681d5e7c9cac746a0))
* rescan drives on settings page load to populate hardware info ([97f30ce](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/97f30ce05c01dd9b9bba96d682499be66f6f0b7b))
* rewrite job detail header with breadcrumb, metadata grid, and integrated panels ([09a7f8c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/09a7f8ccf5597f45b08285a94973d09c15e82323))
* show global default values as placeholders in drive settings, clear override when matching global ([dfabb70](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/dfabb7070ba50b08c6ac1d73b749c843607b6582))
* show rendered filenames from naming engine on job detail page ([0b68a5c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/0b68a5c3d041c2f0511e7936671f621d8a99d76c))


### Bug Fixes

* add ARM_LABELS for prescan settings, fix null-clearing in drive proxy, update test fixture ([e5cf24b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e5cf24b81b1c4f182c75c54235202e704680fdaa))
* add missing fetchNamingPreview mock, update DriveCard tests for flattened settings panel ([d3372b8](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d3372b860fb00e527518b2853511ca17d6cfaafb))
* add missing rip_speed and prescan override fields to DriveUpdateRequest ([619e62c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/619e62c402a35fc5b7fe76b76e4095e592d020fd))
* add non-null assertions for job in track update handlers ([1ec5b65](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/1ec5b657219dabbbc5c58e5b00e558e2c1591aa3))
* add prescan and rip_speed fields to DriveSchema response model ([736e4c5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/736e4c5e53746ba35dbc7b24895b04f9f745ca25))
* add rip_speed and prescan columns to UI's SystemDrives model ([3b95c1f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/3b95c1f8ab9e13c70e3743b6a72e2f97fa50c41a))
* append Z to transcoder UTC timestamps for correct browser parsing ([301dfb7](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/301dfb76b0ebefb0eeaf6e9c5a31653253a1404b))
* deduplicate panel toggle button classes to pass SonarCloud ([56b0c0c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/56b0c0c217c44634abc71ec125a7018575ff4ef2))
* filter track counts by minlength so short tracks aren't counted ([99656e3](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/99656e3bedcf37b920116014b516a0d678261046))
* flatten drive settings - remove Advanced toggle, show all settings in one panel ([158c11d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/158c11d196d63973e7e1673104e91bc35f919e23))
* hide 'unknown' video type badge on transcoder cards ([861482c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/861482ce3667f4de52f6e9ac6aa93bf0497ab56c))
* hide filename for skipped tracks on job detail page ([a951b47](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a951b471ebbf41a26741d23e846a9644359a43a1))
* hide ripped badge for skipped tracks, add transcoded status color (green) ([5c2426c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5c2426cce5468a239c92f864cd97ed2e61dec4d7))
* hide transcoder log section for pre-rip job states ([2bf65a4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2bf65a4ede4bf2fa747d30c6de6557e5a10abadf))
* link TranscodeCard details to ARM job page, hide when no arm_job_id ([1caf599](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/1caf59904bac112a92403e7e1bb6cbabb42d38e9))
* move IMDb back to title line, style action bar as bordered container ([ac18c9b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ac18c9ba3bbb75a0633842127e6e59cd79d4d494))
* prevent scroll jump on transcoder page during polling ([6ae67d6](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6ae67d6614b095fea6605bec645ea2177176b665))
* remove invalid [@const](https://github.com/const), inline button class ([9627ebf](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9627ebf2067e8c0a61b6eff01d10a4340e7ff379))
* rename 'Title Override' column to 'Title' ([2da3ced](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2da3ced0a0ac87857bee5c1588f1e1b36d000197))
* replace regex with string match to resolve SonarCloud hotspot ([a75097f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a75097f0d9ce8d79a364cdb35cb46d3255150984))
* send explicit paused value instead of toggle on pause/resume ([82762e9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/82762e9b362355ec143d0a000691f04a4dec1cef))
* show 'Skipped' status for disabled tracks instead of 'Pending' ([4d703aa](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4d703aa4e9675cb46025cef870ed66793487767e))
* show real-time ripped track count from PRGC progress messages ([646d6b9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/646d6b9864c19457d1dca90e840263ddc8de6eef))
* show Skipped status and hide Ripped badge for below-minlength tracks ([61c676e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/61c676e82bdacaf6b2e8c59f20743afd32cc25c5))
* show warnings (yellow) instead of errors (red) for successful jobs with issues ([58ce092](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/58ce0924d28f822c79938330988c05c45c1731b1))
* simplify CountdownTimer to use paused prop as sole truth ([2a79130](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2a79130a9c06aa584c2b426fab545c27cf26401a))
* unify action bar button sizing and styling on job detail page ([23f3802](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/23f3802bd43aec8c3dfdd6d16ee51c7de27b3483))
* update JobActions buttons to pill style with outlined destructive actions ([e9a58e9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e9a58e954f8a3960d514d7557b41191e6f5e00c8))
* use fixed blue color for Fix Permissions button instead of theme-dependent primary ([9f2ece8](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9f2ece852406dd6552a69bd74d576ec8b31132c7))
* use full-width row layout for transcoder cards on home page ([142313e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/142313e16e6e073be7cdf21a6d1d6de5d5c82f2c))
* wire manual_pause into DiscReviewWidget pause state ([5450aca](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5450aca4a09144956edb461cbba242023fbde897))

## [15.0.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v14.4.0...v15.0.0) (2026-04-06)


### ⚠ BREAKING CHANGES

* Jobs in 'ready' status now appear in the Scanning section instead of Active Rips. The idle message is hidden during scanning.

### Features

* add gear menu with rip speed setting to drive card ([5ceff0b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5ceff0bdce232e3571ac059fee05232bca4ee0f2))
* add preflight proxy routes to UI backend ([e23ce0d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e23ce0dd7502856a58e1e7c104fff2424a1f13b1))
* add preflight TypeScript API types and functions ([556278d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/556278d143321c66130ccb2016aeb57a8b551e3c))
* add ReadinessCheckStep component for setup wizard ([cd053be](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/cd053be8d18e8c4d8fbd6190f8a30fcdfcf10006))
* add rip_speed to Drive type ([2d01225](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2d01225c2b8b4cfe3c39c30281e0ebdb1155d2ee))
* add rip_speed to updateDrive API wrapper ([8a91327](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/8a913270687d6d31062955919763d8888244bd80))
* add Scanning panel to dashboard for identifying jobs ([5049140](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/504914019be3166438c232df89621f727a79f775))
* add System Health panel to Settings page ([006281c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/006281c62bad9dc0f5dbcae33895c8aacc004979))
* add SystemHealth panel component for Settings page ([7df165f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7df165ffff963527b829dbbbb0ce86dc5132ac38))
* add transcoder nav link and fix status bar link ([7d33dcd](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7d33dcd35cce2854112e3499c74df6853a81c381))
* add worker pool API proxy and types ([57da96f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/57da96f3e4c0ed572996a6e3c642fea26b660c17))
* collapsible ActiveJobRow for dashboard rips, scanning, and transcodes ([981e31e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/981e31e3202d20fbd272a0c7a7c3f3bfaacee67e))
* dashboard scanning state, job detail visibility controls ([e680c81](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e680c81ec6f3ef80d5e56f8d5661463b723d16b1))
* disable Re-transcode button when source files are deleted ([6535cfc](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6535cfcf273ccae770d79cc39bdd9d922a537f50))
* insert ReadinessCheckStep as step 3 in setup wizard ([7309567](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/730956777501b2380668697f36f61c14441c270a))
* merge Jobs page into Dashboard and remove standalone /jobs route ([c13a418](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c13a418893c5d8a192ea1d66296c1abaddf43274))
* metadata search pagination and poster fallback handling ([5dfcbc0](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5dfcbc0f2cdbd37303531f668fde429a8e06f140))
* unified collapsible row style for rips and transcodes ([5340c82](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5340c82e20c0ee2d23ac359caffef77545cd4ee5))
* worker pool display on transcoder page ([1b32e59](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/1b32e590c4805e8c4a63632e36c21172f85695cf))


### Bug Fixes

* add error handling and feedback for retranscode action ([4a23ee6](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4a23ee6cbe115966197988f13e7cfb8c146482cd))
* add missing rip_speed field to DriveCard test fixture ([0dfcd97](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/0dfcd97b89fff62e636afef55e067bf98135eba6))
* auto-refresh job list when transcoding is active ([9136009](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9136009dd61bec7e837eb12d624f86f456846c81))
* cache setup completion to prevent wizard flash on navigation ([e0371df](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e0371dfff4d11599d9394c1ce48af71bf89f36b0))
* episode matching UX — stable table, loading state, search + match flow ([c8baa81](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c8baa814f62edf20269be7109ce9aeae57cd8b65))
* get_job uses query param instead of non-existent path route ([9c6161b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9c6161b5fe80d177ba770c87de61e429e708e121))
* handle read-only paths in preflight UI - show as green with 'Read-only' label ([a850008](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a850008cefd5e4e49b328953c226c776e38b790c))
* hide idle message when scanning jobs are active ([c0550d0](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c0550d0e854557669421b42f73c59fdecea2d964))
* hide transcoder log and CRC database for music and data jobs ([15f3c9c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/15f3c9c9df62a00a1cdd8c1c0c146d90178dc1b9))
* keep controls visible during episode match loading to prevent vertical jump ([f863f23](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f863f230d4e43fb072ca26e011790edda26ba3a1))
* move job counts to dashboard top, remove Jobs nav link ([d79d6fd](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d79d6fd306572f8b7868475a8292bfd095ded465))
* only show Episodes button for series with IMDB ID, not all movies ([f9a592d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f9a592d02b5a6475cf5887642ca6889e5f9153d1))
* parse ISO timestamp bracket log format (rescan_drive) ([afbabc4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/afbabc4a4a7997069b97f92bed5642c2031ac3a8))
* parse wrapper script log lines into structured fields ([a309c7c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a309c7c298b619968b9060aa8d763e309087a893))
* prevent input clobber during polling, improve accessibility and null guard ([9d1f0dc](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9d1f0dc2c9fe6258416998dadf87e8eed2e646d1))
* remove dev preview fake transcode data from dashboard ([99cebaf](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/99cebaf9fd9a480c99ef4d2c37241643c0aabc89))
* resolve SonarCloud warnings — unused import, raw string, non-null assertions ([e186c8b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e186c8b122a6bf629c6ddad4012a0a6fcd3613d3))
* retranscode fallback to transcoder job ID when arm_job_id is null ([a078d23](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a078d230df3710a2aa5fd8c032ed1d07d9912679))
* show 'ready' jobs in scanning section, not active rips ([7ac0b11](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7ac0b11ca4212590b8197aff5b88bf3c6175dbad))
* transcoder page scroll jump, home page transcode links, negative timeAgo ([44ffa4e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/44ffa4eec7ca68d1b57c6c30c343134cda625bf6))
* TS type error on search button and test assertion for page param ([b8d43b9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b8d43b98921aafec3c2cce9b9cf359c8df13eea1))
* TypeScript type error in it.each filter pill test ([5a18b53](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5a18b5347545f2a2d4561415f55966b2364c4555))
* update Episodes button tests for series+imdb_id requirement ([a015500](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a015500e2e1e15bb7b0c6e263aa3918cd3746357))
* update StatusBadge test to match current 'Copying' label ([cae6ded](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/cae6ded6a20235b72ea2ca4df50a6b4c9e59113f))
* update test — Search button now visible for multi-title series ([2416c9d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2416c9d410a03f52babc991267c62ee9d472062d))
* update tests for poster placeholder, multi-title search, and onclear ([c1448a8](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c1448a83f447e16bfbe34710326e3c5596b34773))
* use Annotated type hints for FastAPI query params (SonarCloud) ([8f9b04a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/8f9b04aa65a57c8f68ca2b8a494b9c7a56e54223))

## [14.4.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v14.3.0...v14.4.0) (2026-03-31)


### Features

* add 15 new built-in themes, reorder by hue ([a48bc2b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a48bc2b6f4ed28c7708922ac13d0f54c3d7caac7))


### Bug Fixes

* resolve svelte-check errors — a11y label and TypeScript mock types ([813f8b7](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/813f8b77d35bae4dfbdabf00674475cd4218ffc7))
* theme polish — section frame gaps, LCARS fixes, review panel border, cache feedback ([f518639](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f5186392c452db1dc14e0c95624598131b007e7b))

## [14.3.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v14.2.0...v14.3.0) (2026-03-30)


### Features

* multi-title movie review — toggle, auto-default, conditional fields ([3b09134](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/3b09134863ebcf4b5a5ddfd7e265db75ddf59ede))

## [14.2.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v14.1.0...v14.2.0) (2026-03-29)


### Features

* add dedicated GPU tab to sidebar and bottom stats bar ([6316a34](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6316a34a937cb556f125fb20ccb7a42e947803cd))
* add power draw, clocks to GPU metrics; rename Utilization to Load ([b6d8c0f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b6d8c0f446ea377fe18f6c76a0244738a8b0eb87))
* color-coded vendor pills — nvidia green, amd red, intel blue ([554ef76](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/554ef76f11e1e88aef7b7f68fba0948954f89660))
* display GPU utilization metrics in transcoder tab, sidebar, and bottom bar ([d83f507](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d83f50708b0f1d222892cc03014ebcb9181d5568))
* folder import wizard polish and review widget improvements ([7e57577](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7e575773e14eefae9d8f5396585d9987db918b19))


### Bug Fixes

* add missing cleared property to notification test mock data ([37da7bd](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/37da7bd77c0671215fae27720d7c7d07576315e6))
* merge API theme tokens with built-in defaults to preserve --radius ([9681406](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/96814069dd0c4732374a2b43fba86c85477678ff))
* replace require() with await import() in FolderBrowser test ([5556fcc](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5556fccd3b0ff943d52a435f2994dc5678184c09))
* theme flash, panel accent colors, maintenance text sizes, radius tokens, and collapsible file paths ([cd99c43](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/cd99c4393035f5c5a33db064f6fa691a85f2f3c8))
* use full words for GPU labels in bottom stats bar ([9afce2a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9afce2a5ecf79c18fa5bb8b3e942520004ebef56))
* use non-public path in test mock data for SonarCloud ([a0e8d7e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a0e8d7ebba58ef8671528d331a5fac4fceeb5897))

## [14.1.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v14.0.1...v14.1.0) (2026-03-27)


### Features

* apply minlength skip indicator to job detail page ([1c3ed3e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/1c3ed3e5f831dceb11d56e193789bdb61ee4f11c))
* hide rip checkbox for tracks below MINLENGTH threshold ([28ada8a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/28ada8a07701edb81752afc8090ebea3bd4394a9))

## [14.0.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v14.0.0...v14.0.1) (2026-03-26)


### Bug Fixes

* episode column, progress bar, em dashes, and episode restore ([07d3c4c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/07d3c4cd6a150e8a80b8ecd4862ab276e177dd1a))

## [14.0.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v13.8.0...v14.0.0) (2026-03-25)


### Features

* add clear raw directory maintenance action ([0564c5a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/0564c5ab4fffbf2033eb00caff25b2072a654548))
* add EpisodeMatch component with match table and dropdown reassignment ([baec9ab](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/baec9ab93e643351e0e1e712b6a251ced5f5d4a2))
* add naming proxy endpoints for per-job overrides ([d56d13a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d56d13a36f4451747efdc8011093de863b1d08ab))
* add TVDB Episodes button to dashboard review widget ([c059dc9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c059dc9e091abaec828e8fa65923bd6bfcfd604b))
* display Processing status for folder jobs, fix job detail page override ([264b692](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/264b692fa6bf9a67084392150bbe01838afb1cc0))
* make sidebar storage stats clickable links to files browser ([9ed704b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9ed704ba0224b9f353942c0d3bbcebbed1b3558d))
* per-job naming overrides UI with editable patterns and custom filenames ([1628cb5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/1628cb5f21abfb30a7634f253da031b5139b82ea))
* prefill season/disc fields in folder import wizard from scan ([c291c13](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c291c13ac3e295aca0b1923d288c2cf766010160))
* replace TVDB button with Episodes panel using EpisodeMatch component ([fe7af04](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fe7af045a729206c44fa427e3d870b45240ca697))
* show rendered filename preview in episode match table ([b235476](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b2354764bc59811ea82602bade865cbab4a21e3e))
* show rendered output filename in review track table ([4eeb94c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4eeb94cb6f511c91010cdb1ee46313d23651ca40))
* wire naming-preview API into EpisodeMatch, show rendered filenames after apply ([26f15c9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/26f15c98d3ed2f2d6d74e02de2e456390aca24e6))


### Bug Fixes

* add season/disc fields to UI proxy FolderCreateRequest, fix test factory defaults ([cfae06a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/cfae06ad2cc206c4dfa2857bac8d33556a4cfd8a))
* add source_type and source_path columns to Job ORM model ([714b671](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/714b67127d2c42a4f200a5d6f43f9f0c255d1102))
* add source_type, source_path, disc_number, disc_total to test factory defaults ([ad6dc61](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ad6dc61c8fff6fc65afe5aef62ad44943a9d338b))
* convert TVDB episode runtime from seconds to minutes for display ([f72e526](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f72e5263a66c25e3df23a2e05a99e86f251c8bbe))
* disable auto-proceed timer for folder import jobs ([cdad4e2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/cdad4e2093f11415c0d214076aad3470da6c080e))
* EpisodeMatch auto-resolves TVDB from IMDB, fallback dropdown from match results ([d82fa82](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d82fa8263c292ac3d48f384b43293ec96e08e912))
* Episodes button uses same primary style as other review widget buttons ([1e5cc13](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/1e5cc13659b8f2243e0985fcb89fdcda72da99d4))
* increase default episode match tolerance to 600s for TVDB runtime inaccuracies ([a735765](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a73576501c45b3bc24fe350775cc8c9972f2cb7b))
* increase review widget button size for better readability ([cd8286d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/cd8286d922b06c505a8c060fc83bc13e8bcf5a46))
* LCARS navbar button visibility and episode match input sizing ([fcfb038](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fcfb038be77957d2855e051d8b1d454a7383fad2))
* move Episodes button next to Search in review widget button bar ([0dbca4b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/0dbca4b33dc0c523f335fc4a9f66e24aeb499fdb))
* setup page redirects before render via load function ([b92311e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b92311e0e11ef720559bf8668bc35c72fdb30c65))
* setup page redirects to dashboard when complete, type fixes for episode match fallback ([dd3f917](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/dd3f917f87fc60a96508d9255b225192071567e4))
* setup test import path and null check for type safety ([12c2518](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/12c251844a4a9bc320a025ab9ae65ba3137bd4b3))
* show episode number badge instead of CUSTOM for episode-matched tracks ([bac5482](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/bac5482063c4ce193ea55af472e77be4dad01a5d))
* show episode number badge instead of CUSTOM in review widget track table ([3c3483b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/3c3483b1a7f9099384b2d91d44c2a6f00c213fd8))
* sort episode dropdown options by episode number ([bfc0c8e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/bfc0c8ea018d7d0a29ccfec35cdbc447e15c8279))
* sync season/disc controls from job props via effect instead of init-time state ([6dd5be2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6dd5be288a0afaa38684f856aba66e8551475108))
* use importing status key for folder jobs, keep processing for transcoder ([846e5be](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/846e5be6e0055068e3404b43484c793a4d522231))

## [13.8.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v13.7.1...v13.8.0) (2026-03-23)


### Features

* disk-backed image proxy cache with maintenance controls ([b8957ab](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b8957abd1aa3cc0739828d9d6a23301345ac90fe)), closes [#38](https://github.com/uprightbass360/automatic-ripping-machine-ui/issues/38)


### Bug Fixes

* address SonarCloud SSRF and path traversal findings (S5131, S2083) ([710cb5f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/710cb5f9325ac0bd76186dbb5c8f7e3cf743bf0c))
* remove dead code in system_cache test (SonarCloud S5727) ([50d9daa](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/50d9daa37d6e9d801b38f5271b7d71bfe0c4bf38))

## [13.7.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v13.7.0...v13.7.1) (2026-03-23)


### Bug Fixes

* make system_cache tests deterministic by testing _refresh_ripping directly ([3a8eed3](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/3a8eed316a366cb6f6e648717549f4ba91648c64))
* properly await background tasks in system_cache tests for CI reliability ([5b2f0fa](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5b2f0fa8bb7cdba8c16c5ab0f0c8034f478c8818))
* system_cache test isolation — avoid task.cancel on closed event loop ([1f6c8ef](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/1f6c8ef8b40c74ff39928a01df4be0ee7304729e))

## [13.7.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v13.6.0...v13.7.0) (2026-03-23)


### Features

* add BottomStatsBar component for lg breakpoint ([29f1b69](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/29f1b69916a941167ac5ce3dff760db6b04d4c73))
* add bulk delete and purge endpoints for jobs ([8727fd7](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/8727fd7a99e60d040f5839607228782d3ce8a361))
* add Check Key button to settings, update FindVUK label ([29dde50](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/29dde501102d07b4e3f9450ef10520eb0ce95376))
* add checkbox to JobRow, purge action to JobActions ([70d5575](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/70d557576a23e5dc303bf8f3e8613145c0c603a4))
* add GET /api/jobs/stats endpoint with filter support ([2921b60](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2921b601016280e2ee873ea4800a8ac42b9ddad7))
* add Jobs to sidebar nav, remove card view from jobs page ([fde92fa](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fde92fa8ab5409b5b5ed4b69b0e63a4ee2300730))
* add log file download and delete functionality ([a4196a8](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a4196a83a157fd35d829ecf92861a7ed997e6e45))
* add maintenance and arch-debt proxy functions to arm_client ([5cb0994](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5cb099423bcc709c8f8a2266fd6773a7ebb3590c))
* add maintenance API client and tests ([8ad9ac5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/8ad9ac57701d4e3027d96efb3728aaaec58f28e6))
* add Maintenance nav item to sidebar ([613c549](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/613c5495f797c1826b535cac909448a9379f6e8e))
* add maintenance page with orphan cleanup, notification, and transcoder sections ([29e7d9e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/29e7d9e50acdd48c3b83bf51bc98cf21e6f76cfb))
* add maintenance router with ARM proxy, notification, and transcoder cleanup ([91ee8f4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/91ee8f43946a591b7907e3bc6d7e4661a53483da))
* add MakeMKV key check and ripping-enabled proxy to arm_client ([8c71496](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/8c71496eb3183f5a8ae0810402412531b41c3fce))
* add MakeMKV key status dot to header bar ([c398eff](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c398eff48f3bac3cf8729b317d36976c031c5c57))
* add MakeMKV key status to dashboard and key check proxy endpoint ([9fe545d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9fe545d7796788dfc2e94a70999f450042a454c7))
* add MakeMKV key status to dashboard types, store, and API client ([29a420b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/29a420bec2db34eb867e34fe462f3e9db9525d86))
* add notification dismiss-all and purge functions to arm_db ([4fbe5f1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4fbe5f19264307d38b209f408bf1771a1bb96a2b))
* add sort, filter, stats, and bulk operations to jobs API client ([f4f56a7](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f4f56a75d61e85ec2e8bb973e3040bf9b5e9a49c))
* add sorting, disc type filter, and time range to jobs endpoint ([6307549](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/630754953fd2f840fa07a196012aee9dbdfcac5a))
* extend bottom bar to 2xl, full width, storage deep links ([7d8cd60](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7d8cd60d2c13cb72080f2782a985d14f3657173e))
* redesign jobs page with stats bar, pill filters, sortable headers, gear menu ([958ea5d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/958ea5d451e8e6bc67868a2e540b4c70dc49494b))
* wire BottomStatsBar at lg, hide sidebar stats below xl ([672359a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/672359aba108193a8aa26c6f5a406c8021d89078))


### Bug Fixes

* add MAKEMKV_PERMA_KEY to HIDDEN_KEYS, make key dot red when unchecked ([5aecc52](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5aecc52a15a7c56dd2cba3b206706d5bb178944d))
* add missing DashboardData fields, fix test mocks for ARM proxy ([c345436](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c34543669306bbe8df55841a92be57d8f996bcfa))
* handle ARM error responses in maintenance _check_arm ([ead732b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ead732bcff2d07ea29f3e75644c33d71229cd74c))
* move responsive visibility into BottomStatsBar root element ([b5a0c75](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b5a0c758a76f83520a43f908cdad6fce7f15fe1f))
* only scroll to settings panel on in-page nav, not initial load ([a261461](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a261461568ea41d6a1bbd093b626638f90e5e757))
* prevent background task garbage collection in system cache ([6d1e190](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6d1e190da2c73f8f1101c733aa74a50875fe87e0))
* prevent scroll lock when navigating to settings panel via hash link ([a4bb637](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a4bb6377a66394e6315ec4e9301ab76b4784cce8))
* proxy transcode-overrides and track-fields through ARM instead of direct DB ([9cbb211](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9cbb21185f727b80a5be7dc91d1ead227590137c))
* purge now cleans raw_path, transcode_path, and completed path ([68efe79](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/68efe790d59b87ac64de738b073038f8498ed3a1))
* remove programmatic scroll — just expand panel on deep link ([9917aae](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9917aae39765c0c13dfb76a18d4192bd3c643dda))
* reset scroll position before navigating to settings panel ([eeafb79](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/eeafb7969fde05e57a6fddf0bd9ef0cc5b6db96f))
* scroll to panel after 600ms delay with instant behavior ([8b8d31c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/8b8d31ce141b227b7714a4e64d1e0e6e52be411e))
* settings deep link scroll, hashchange data loading, drive card duplicate badge ([c875a9f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c875a9fab14679d82824d832f1d48df126ea90bd))
* setup/status uses 2s timeout fallback on cold cache ([039c99e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/039c99e7e695bd269a45c8e5cde2ded4a4356da7))
* storage links use ripper paths, reactive query param on files page ([1efafc9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/1efafc9a4e278f60eac9c19ff3ec8d820aab38a9))
* update jobs page test mock to include fetchJobStats ([149ab43](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/149ab436935c723554e28dbce90f485493bc6dc1))
* use instant scroll and longer delay for settings panel navigation ([6c47c35](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6c47c357b3b5b5b5eee971a59d289cb76050832d))
* use MutationObserver + requestIdleCallback for reliable panel scroll ([c01aad4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c01aad432d12de09df74004f0f6ba3cc6059335f))


### Performance Improvements

* cache setup/status endpoint with 5min TTL ([4d12135](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4d1213537d76fe419e80de260a626c0baab74036))
* cache slow ripping-enabled call with 60s TTL ([d86e96d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d86e96dbc8a7b71f09bbcffceb548c49681d1b28))


### Reverts

* remove setup/status cache — was masking ARM connection pool issue ([7dab179](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7dab179c8322a59801990e90f750dbf93700737e))

## [13.6.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v13.5.0...v13.6.0) (2026-03-22)


### Features

* add filter input to folder browser for large directories ([1dd310d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/1dd310dcba0735bdca43939ebc17ea388188c38a))
* add folder import API client and types ([8cf2bf5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/8cf2bf553b2f288033657461501fe10795da68d5))
* add Folder Import badge and source path to job cards ([256f8ed](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/256f8ed3b646dd4f7f8433e810457e96482be4e5))
* add folder import proxy routes in UI backend ([e47a19c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e47a19c9e0aea34f356d538d019cbac136f97c8f))
* add FolderBrowser component for ingress directory picking ([8fd1a8c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/8fd1a8cd42f0f91302502a446fc03b2936cf27fc))
* add FolderImportWizard three-step modal component ([5a385a4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5a385a4db3622be4beb1612e59cd0d6f9607d3cb))
* add Import Folder button to dashboard with wizard integration ([af1f5d5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/af1f5d58ffe9a685baf93c3a909ce03d0aa8928f))
* add PRESCAN_TIMEOUT and INGRESS_PATH to settings UI groups ([10760a5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/10760a510835c73c093c02bdae4db962bc560785))
* add quick actions gear menu to header, remove dashboard stats card ([115f521](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/115f521a8c5f77f241220e76f00c7e4cb43bf9c3))
* add server-side LRU cache for proxied poster images ([bfbd6d0](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/bfbd6d057a2b2d20a16d6d1c22c4dc98ec41f824))
* add source_type and source_path to job schema for folder import display ([e92ca53](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e92ca5305c16dd4d2262d212ee8c5e99a99c06b3))
* add transcoder restart button to settings service control ([9a92904](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9a929045f94a961681df74523b1d82d81691bea4))
* auto-detect disc folders, prevent drilling into BDMV/VIDEO_TS ([a6a447b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a6a447b0bceff374f7947f16e8066af4ea58f6a4))
* make diagnostics section collapsible with issues-only view ([0bb7f37](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/0bb7f37f9c96ce3d96d38c4b1d2975412be6f757))
* redesign DriveCard with consolidated action bar and enriched info ([92d4c64](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/92d4c64b9b3849d0fcc1bbdf57da1125268842eb))
* show 'Importing' status and hide track counts for folder imports ([b367337](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b367337c5a07e4e2f6c5f5880cc5f798291096f6))


### Bug Fixes

* add friendly labels for INGRESS_PATH and PRESCAN_TIMEOUT in settings ([ffb7d4d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ffb7d4ddd3ea805424c22c3098b69eeadea33e0b))
* catch httpx.ReadError in ARM client to prevent dashboard 500 errors ([eca79e6](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/eca79e6474a57714de8ae3df3e06cbac57d1c6e4))
* dismiss import wizard when clicking settings link ([7234387](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/72343870fb69b53269c935c09d5b1282f358507e))
* move import wizard to layout so it works from any page without navigation ([e9e45fd](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e9e45fdb80b060790747711a958613cd8f84ce73))
* proxy all poster images site-wide to prevent ORB blocking ([ea11c2a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ea11c2a6fdd2362de5ca485b9b6aa35e78429484))
* proxy poster images through backend to avoid browser ORB blocking ([8d872aa](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/8d872aac3e33a6f2543e136c0bf7f37c8bfb4546))
* show friendly message and retry button when ARM is starting up ([8b553b0](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/8b553b0b60af453205c9c7d0c983113f596b7343))
* show helpful link to settings when ingress path is not configured ([4f77dbf](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4f77dbf128d87f85351fa87930f3ef5a2d4a723f))
* strengthen poster proxy SSRF validation for SonarCloud ([0739f94](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/0739f94bc249dd818a2607fb64ef8bcc07dfd5ec))
* use absolute ingress path for directory listing in FolderBrowser ([98692fb](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/98692fbe37629cf98a00ea2f57239bdf5fe2cf94))
* use https in poster test to satisfy SonarCloud security scan ([844f1e9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/844f1e9094fd7494da0f0eec3da65d4ad19e222e))
* use svelte store for import wizard instead of page reload ([85c6709](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/85c670906c570c03a8360cab2af1cd61b34d641d))

## [13.5.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v13.4.0...v13.5.0) (2026-03-20)


### Features

* improve restart UX and add transcoder restart button ([9a68f2f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9a68f2f623c424279c80f9290fed46e78ce59af0))

## [13.4.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v13.3.0...v13.4.0) (2026-03-19)


### Features

* add drive controls and system controls ([51cc98b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/51cc98bd2575ad0eb726f125b555fea1678c30aa))

## [13.3.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v13.2.0...v13.3.0) (2026-03-19)


### Features

* add setup wizard with first-run redirect ([9dacd9c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9dacd9cedcb4d9a23ecbee06bf524455fdbde733))
* hide sidebar on setup wizard page ([440dcd0](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/440dcd01d3b542bce74338f14221e8ed8a995eb7))
* show transcoder and transcoder DB status in setup wizard ([534d8a8](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/534d8a814ffb4fc8ffe24cf153b34a89802c4a62))


### Bug Fixes

* catch RemoteProtocolError in arm_client to prevent 500 on stale connections ([3ef921a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/3ef921afb405f93da28876483d863e2f2c35736b))
* re-throw SvelteKit redirect in layout guard catch block ([99af364](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/99af36456cdc6c34eea2e274354a78af8ca8b1c7))

## [13.2.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v13.1.0...v13.2.0) (2026-03-18)


### Features

* add semantic CSS classes for status badges and confirm dialog ([9fee794](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9fee794fd17a0c3c09477cfcf42f9c4e96cb4e66))


### Bug Fixes

* address SonarCloud warnings and reduce code duplication ([c96a6be](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c96a6be9fd55164a45de8aa66bcdcf3412b4ef6c))
* remove accidentally committed node_modules and lock file ([ff42c4c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ff42c4c8e0f1cbff779f48c4cdf5039b48028447))
* resolve TypeScript errors in test files for CI ([497039e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/497039e07becacaf5b78540f5e05a503a74b585b))

## [13.1.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v13.0.1...v13.1.0) (2026-03-16)


### Features

* add copying/ejecting statuses, fix transcoder status label ([e25b6fe](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e25b6fe0230f65666a74e1cafe909190a184c9f7))
* add theme name field to upload form ([9b4f00a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9b4f00a2aa186f812d8224e0a4bd17863bb787c8))
* extractable theme system with runtime CSS injection ([4ec7906](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4ec7906d41dcc80814876e62d42cde8b01696407))
* improve metadata error messaging and test-with-unsaved-key ([14e9325](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/14e9325dfbef22780d05de2b08fe46c092aedd14))
* load theme CSS from sidecar files, save as split files ([02db072](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/02db0720904fc7b7a3ce5b877fa4558485d7adcc))
* multipart theme upload and CSS download in API client ([3ec182a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/3ec182a0d41570e2ff7b167e684e2c8d79d0eedb))
* multipart theme upload, separate CSS download endpoint ([912c95f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/912c95f48d9d36a96195e9c5dacacb04f873e06b))
* two-field theme upload UI (JSON + CSS) ([aed7025](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/aed702507686904cd961c7f760393b8e615633bd))


### Bug Fixes

* address SonarCloud issues in theme code ([bf36830](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/bf36830cd3eb52f32283378a2e092e60dcc397b1))
* export downloads both JSON and CSS as separate files ([015db27](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/015db27bbb832273984c5bb9a7717e1ee4f289fe))
* inline resolve() path containment checks for SonarCloud taint analysis ([4d95033](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4d95033cb0ef6e39936090df81dbe79e462819b6))
* update tests for metadata error passthrough and params changes ([2a4feb9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2a4feb9bac61e38b40e9f9aa07588284f4f3c057))
* use resolve()-based path containment check for theme file writes ([6b4a575](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6b4a575e1c4f838f2f17d5d4694ee95f3cea7995))
* use yellow status color for copying/ejecting statuses ([a801aa5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a801aa50004eeed9f1c12d09b55e027448e14744))

## [13.0.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v13.0.0...v13.0.1) (2026-03-15)


### Bug Fixes

* add info tooltip to UHD Capable checkbox ([172491f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/172491fffc468dfa32e96f6ead579cdeb3da5347))

## [13.0.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v12.0.0...v13.0.0) (2026-03-14)


### ⚠ BREAKING CHANGES

* version alignment for v12 release

### Features

* abcde.conf editor, music file browser, webhook test fallback ([383d03e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/383d03ebbf08b47fd3bb9f228005634bfc2efe27))
* add AUDIO_FORMAT to rip settings UI ([abcfcfd](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/abcfcfd4caaeb0b5b8dca4a914586f66113a95da))
* add Force Scan button and udev diagnostic panel on Drives tab ([0130fa3](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/0130fa34db67acf5ba1ef81334f39f6897bb0db5))
* add Force Scan button on drive cards ([d1ecc13](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d1ecc136acba6e9adeebcce4c91918fa37e3a9fa))
* add per-job transcoder log view on job detail page ([f9eb981](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f9eb98104d587ea46686328fcac49d98b54740bf))
* add track update API, multi-title backend proxy, and supporting changes ([cea5a74](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/cea5a74081f0612b9fa8feb45bb6fa2791894a1e))
* layout nav, dashboard idle state, LCARS section headers ([d2089e9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d2089e9a10f3b48f00bb83f1265c3a438ac2e80b))
* multi-title disc support — UI + backend proxy ([8ee4bae](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/8ee4baec8f02e43c80c3dcdf64ff4d5d84ab3190))
* music track display, disc info, collapsible debug, transcoder config ([d02fb70](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d02fb703ab588f72f33c108f1af4ea717bde943c))
* notifications page with dismiss support ([0ed3e77](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/0ed3e778f2466e1df7ad4f32549fd30c3dec7aea))
* polish TVDB match panel and job detail UX ([d67a6fa](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d67a6fad6513ce560ac8f1904f17177d99a1eec2))
* replace track enabled buttons with checkboxes and remove Edit column ([77cd4c6](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/77cd4c67856853f6f6b5cb99f4d597c86bef56c7))
* settings deep linking, TVDB config, endpoint popovers, UX polish ([5332a84](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5332a84a7e4ad421e1ef99a21d8a0321b2bf85c6))
* show DB migration status and fix Hollywood theme borders ([07a47a4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/07a47a423040ffcb0b7de02cc5c9a0036e9d6255))
* show disc number on dashboard cards and table view ([fb2800e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fb2800e72a504f910d6fd13d1916deda72277c6a))
* stale drive removal and diagnostic panel improvements ([b7e9623](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b7e96237665b76ef2618a7d60477f60b8c8ed0f1))
* structured diagnostic panel with table layout ([216398f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/216398f9d1524b50226ba05ab825b0cf407ff7b8))
* TVDB multi-season matching panel and episode columns ([de0ddaa](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/de0ddaae62047b1d05f25e3cd9327169185898d3))
* UI polish — status labels, waiting_transcode, component fixes ([c257cd5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c257cd55531843f15ae29628b8d6d14e809acfd5))


### Bug Fixes

* add abcde music progress parsing to UI progress endpoint ([828f6fc](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/828f6fc4b792b9dc9824cc4db4e1d39fc018fdce))
* add border and padding to lcars-body for non-LCARS themes ([4426b4f](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4426b4f72a9365f68c8d4436ca58fab896513269))
* add season/episode/artist/album columns to Job model ([119862a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/119862a60d2fa81c6efcf35a0479c786ee7c41b1))
* exclude stale drives from drives_online count and fix track mock ([0fbcf0e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/0fbcf0eccaa91a8f3d45b0aa9fecd9fd776b7728))
* Hollywood theme panel borders, hr styling, and tab headings ([9eabe3b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9eabe3b2c456ca6716fa27f3f53f9d273075f056))
* make confirm dialog opaque in themes with semi-transparent surfaces ([64e0cad](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/64e0cad05af282e498f2ca8320b071895c83fd3a))
* resolve SonarCloud issues and frontend type errors ([3f69246](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/3f6924683d254c73fd77ad2da6f7874c388ee670))
* resolve test failures and add coverage for abcde config endpoints ([27b75c3](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/27b75c3e8f92589a9cab629a1bcd90d3db51a85f))
* restore VERSION to 12.0.0 (already released) ([478520e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/478520e96b5d492edec380397a0efb59aab37728))
* support ARM_LOGS_PATH override for production log mount ([3f4aa52](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/3f4aa52e3534a7bdb6a16e90b192e62841c953e0))
* track enabled column + countdown timer start time ([a3ef25d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a3ef25df473da42712588f021109ab7ae6dbf077))
* TVDB panel delta display and season=0 handling ([6e00596](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6e00596174046f5370d2bb4d1c5396c6e17df0e5))
* use primary color tokens for files page warning banner ([2ae53ce](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2ae53ce88a59c2b194da0c0e8f0b5430897e24fb))
* use primary colors for toggle, fix LCARS tab styling, filter stale drives ([b99f8db](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b99f8db83417c2120a236d919ef848331e04824c))
* zero-track rip guard, error display, progress fallback to no_of_titles ([fea1bdf](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fea1bdf66b112d273252d2970b5144cbb3be9fc2))


### Miscellaneous Chores

* set pre-release version for 12.0.0 ([abbcd9b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/abbcd9b34f7db27116295d8c40ca3d91aeaa1c61))

## [12.0.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.13.3...v12.0.0) (2026-03-09)


### ⚠ BREAKING CHANGES

* /api/settings/bash-script endpoints removed.

### Features

* add 14 color scheme themes with LCARS styling and sidebar layout refinements ([bf05167](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/bf051673ba6866e61c1948b85ebfba17367f5b9f))
* add connection status visibility for ARM and transcoder services ([044660c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/044660c015ad728d1e2f6ea7ccaad89fb3a91898))
* add CRC database lookup and submit to job detail and review widget ([28ca62d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/28ca62d7d611f67925a1ce4b50c4504b8afeea4b))
* add disc type icon to review widget and minor cleanup ([48ac784](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/48ac784b7952072e7893927570a7613799157594))
* add MusicBrainz search for audio CDs ([938fb6e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/938fb6e8a0cf1a87232442e0d27a8019e1ce5b20))
* Add settings page, transcoder management, and log viewer ([7f82eb4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7f82eb4cffe76cadb3c30a955016759b37cf9e6c))
* add structured fields, track comparison, and card flip animation ([b90fb3e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b90fb3e8266c9246e71620b518014aeaf5ecdddd))
* add test coverage reporting with Codecov ([58891f4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/58891f4a6465700427bb3bb9b33189b932901dbe))
* Add title search and metadata matching to job detail page ([85e4487](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/85e4487193634655dff3ed204abbe0e3f8f64437))
* add UHD capable toggle for Blu-ray drives ([5d1363d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5d1363d64630214b969acaa8aafcee7b414e4dfd))
* add warning banner to file browser page ([e16451e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e16451e59c4186a10b2d156f6eff55e08d9cb6e9))
* **api:** add frontend API layer and types for new backend features ([ec201a5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ec201a5d7f82ddbd94a6cc6e57d4b643384102e5))
* **backend:** add system monitoring, job control, and metadata testing ([ed51a3b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ed51a3b922486d44288db7e77c0b36cbc8622982))
* bulk delete with confirmation, match tab styling to settings ([776bacb](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/776bacbf37e9997db4df9bff89e70fe20ef55084))
* **components:** add system stats, disc review, and rip settings components ([d83efca](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d83efca113991207ed45b3773a469663baf31ff0))
* condense dashboard into unified status bar ([52d8e08](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/52d8e08c160559ff4878fa6f840044f43aa205d6))
* dashboard improvements — drive names, disc icons, editable metadata, 4K UHD support, favicon, page titles ([ed497d3](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ed497d3a295330e7417ccd589bf1e5cdf453ea79))
* display folder sizes in file browser ([6c650ea](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6c650eaf11772959d85ba1da3b5b7f00009f7d24))
* display transcoder live stats (CPU, temp, memory) in sidebar ([2b6ff34](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2b6ff3491c216fe8b48cfa486611ac2bf1a070b8))
* enrich transcoder job card with poster, type badge, and metadata ([c27c48e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c27c48ec5fe2332adfec5419232bfcc86d5c9782))
* expose imdb_id and poster_url auto/manual variants in API schema ([26a51fe](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/26a51fe73dfa172755dc7086ad920abf6612ee6c))
* file browser with browsable move dialog ([af13ab2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/af13ab2719b7983d4ebe4904769ff7b1d83c9aba))
* file permissions display, fix-permissions, host paths, bulk delete fix ([a2be5d4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a2be5d4a9f2e0ede9337d29979a9e0d24e68f168))
* LCARS theme panel redesign with structural frames and pill inputs ([c048b08](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c048b080d683750d96468cd30bdef7f42013993b))
* move drives page into settings as a tab ([f494bd7](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f494bd7a7897993979e493aab1c76004e60226bb))
* move stats bar and auto-start toggle to global header, add themes ([480cebc](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/480cebcf041fc03699a278bd5342c1653becd8d2))
* notify ARM-neu to update submodule on release ([b1bdd35](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b1bdd3572d555adf23b506457491fc7db0327885))
* per-job transcode config overrides UI ([f0638b3](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f0638b32ce42d3e14aaa5725de2d7b7fad2b19f9))
* per-job transcoder log previews and plain-text log parsing ([0b843bd](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/0b843bdba165886f6f29abcb920999ac1326c6a6))
* progress bar tracks overall disc, per-job pause, year parsing fix, review pane improvements ([e958f6d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e958f6dd019822b02fbc7e3a5203d4ba5b87e1c4))
* proxy metadata requests through ARM API ([6d343f7](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6d343f7c90522efd79fd392fb579703b06a6fcf5))
* replace bash script notification with ARM config fields ([be3e548](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/be3e54898ff3b451b5720d24381385607af16664))
* **settings:** overhaul settings with search, metadata testing, and appearance ([076f2d0](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/076f2d02229d5a45094370df25203c26ba333511))
* show log_level_libraries on transcoder config page ([be060e7](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/be060e7d3b76dcfcdfc59368fd39eb2f7526ebf7))
* sortable column headers on log pages ([a447f7e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a447f7e66338bd1751ea65a1566ae975ee055fd6))
* structured logging with StructuredLogViewer for ARM and transcoder ([cf222f1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/cf222f191d1e47f00012e44545f1a1debfd34442))
* switch favicon to white ARM logo ([36d950e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/36d950e56ea216948c1f4309ab9917109ace080d))
* theme-locked light/dark mode, default card view, error log links ([913e618](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/913e618d8483b2afc9b519778bd6ae5860478cda))
* **theme:** add customizable color scheme system ([81371b2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/81371b2253bafbfded7af846a779a6ba62b9e81d))
* track progress on dashboard cards + auto-refresh job detail ([acca233](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/acca233fa896b3c373b89ec41563a601e90d66d3))
* **ui:** integrate theme system and enhance dashboard, drives, and jobs ([d10e45c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d10e45c1446e07d5c756b9387e3a80d21aa5107f))


### Bug Fixes

* add missing drive_names to emptyDashboard in store ([9d7ef4d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9d7ef4de970fee9e5db65d011bd175294e8d7e0d))
* add missing transcoder_system_stats to +page.svelte default ([d431bdf](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d431bdffea151c288bd6309c3bca0a783681ebb2))
* add null guard for settings in armSettingsSection snippet ([fc334f9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fc334f9d545043ba836dadee6b31556dc850e252))
* add spacing between CPU percent and temperature display ([549e173](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/549e173e31dc54b387a22481a28c65b53a083621))
* address SonarCloud reliability bugs ([d8d5ed7](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d8d5ed7ba54a269fe22a6d4c8c551de2cefc56ad))
* address SonarCloud security findings ([127573e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/127573ed5b084369b019bcb24a75f1b428c2e755))
* breadcrumb hover too dark on dark mode ([3449f94](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/3449f94310d39254b3bf40146a888b29665217e4))
* catch RuntimeError and OSError in httpx client exception handlers ([c0d56a5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c0d56a50347cd1a04c6a466df5992df40f195135))
* clamp rip progress to 100% when all tracks are ripped ([92f32d1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/92f32d1c3f4dfc553abac13efa1769698ad5fbcb))
* configure release-please to update VERSION file ([d453a07](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d453a07a50950e3057953b1ab83cb293f6c92209))
* deduplicate job defaults in test factories ([28b80c8](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/28b80c8758ccd28c2cc31c3799cfca5a6c878a92))
* display friendly disc type labels instead of raw values ([ea7bf8b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ea7bf8b79e399013c988684e2095a15de46c3f0b))
* exclude colorScheme.ts from SonarCloud duplication detection ([2936e5d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2936e5d7e83fd2954c7347afeb08e9196d2e0843))
* harden MusicBrainz search and cover art handling ([c6127f1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c6127f1ae539bd47b439a666adb65284a1a23170))
* improve font rendering and Blockbuster theme legibility ([2b82738](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2b82738897675d52c3025a1639c8806172695610))
* increase transcoder client timeout to 15s read / 5s connect ([f91a9a0](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f91a9a00a8babaf0f8b022d0cb1ce76b969844a9))
* metadata not syncing on review and pause toggle not flipping ([40f4ca0](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/40f4ca0550497d3b1e703e3f6807f78d42df6ea6))
* pin frontend build stage to native platform for multi-arch builds ([407e856](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/407e8562990772c085c62ca4567d57fe0e32082f))
* prevent false 100% progress during MakeMKV scan phase ([11a52d5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/11a52d5e6fcdb7473cf2514505e8440a9b564fee))
* prevent FOUC by hiding body until CSS loads ([99313a1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/99313a165054b3ebf69e825d7808a58e613262f6))
* prevent layout jump in review widget InlineLogFeed ([9fb6196](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9fb61966f973a37a4874557b1f1617b4eea1dc44))
* read full progress file so PRGT phase messages are not missed ([c8c6e62](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c8c6e62279dbdee357db15602f5fede439026782))
* remove dead RIPMETHOD_DVD and RIPMETHOD_BR config fields ([1077a62](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/1077a62aa55e5ec6515de057717a58d20ab7e866))
* remove redundant type comparison in MusicSearch flip card ([c1b88fb](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c1b88fb365335d9ab9cae5b5d7520a7491eb5fc7))
* remove UNIDENTIFIED_EJECT from settings page ([4ad9835](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4ad98352117d68356422e8a18a47db32c5625fd0))
* rename "Accepting Discs" toggle label to "Auto-Start" ([001054d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/001054dad74162940bdb777fb76760aaee106ca9))
* replace hardcoded paths with env vars in standalone compose ([5d365bb](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5d365bbe45ac067dd04ff8dec0345ebd8a1ba68d))
* resolve 44 SonarCloud high-impact code smells ([b0ff5ad](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b0ff5addbb70a420b4613d1e165279eab4011c1a))
* resolve 6 TypeScript errors in frontend type checking ([e4d9ceb](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e4d9ceb9226e6b1a50fbe903c2c66b3ec475b5b5))
* resolve all svelte-check warnings ([4526227](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4526227d3d0180032e6c59ddcdbd778795454e08))
* Resolve dashboard transcoder section flickering ([7d3add6](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7d3add64c9617e9f05adab3a4584b2c832d2ddd3))
* resolve flake8 lint errors ([a141cee](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a141cee18e0ee44d452a90f6707a939bdae71ca7))
* resolve remaining 8 SonarCloud high-impact issues ([4c945ea](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4c945ea8ff8c45a732136235e0dd8b356aea50aa))
* resolve type error in colorScheme test forceDark assertion ([83e52da](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/83e52da08a8fe741b576863a630256933cd9667d))
* resolve TypeScript error and update arm_client tests ([92af79a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/92af79a0e0a9db19cf37c4b7df36a8fbc5da1c5d))
* restore pointer cursor on buttons for Tailwind v4 ([6fb102e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6fb102e8664d900b4ff3193326965322dda15f38))
* send plain media title in webhook payload ([17a5310](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/17a531010245b77563772f4b30ebb87b92f098dd))
* serve root-level static files and prevent path traversal in SPA catch-all ([c190797](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c190797b4ffcc4280579eb9dc2649652f572a98a))
* show storage section on transcoder tab ([17cb5b5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/17cb5b54f5e422a5841daa8a6bec12dabff27a55))
* show waiting_transcode status with yellow color instead of gray ([22dd128](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/22dd1284c03b7928c41f7c975860477d4beed796))
* surface real ARM API errors instead of generic "unreachable" message ([42c8988](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/42c8988c238e347a69fcd24dacca9316ec67d6e2))
* sync Config model with actual ARM database schema ([5306dab](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5306dabbb5f10f006e8e471ff1330afe25bcbc4e))
* sync Config model with ARM DB schema and add missing active statuses ([fe950c1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fe950c191df8086deac9ca4fd7af6d6a4f6f6668))
* TMDb metadata provider fallback, error handling, and logging ([b075b1b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b075b1b44db7b5bfb1423523fbeb4635192ba482))
* update plain text log parser test to match regex parsing ([ab6be9b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ab6be9b8833fbf15a289144ee711bc985388c09c))
* use DOCKERHUB_USERNAME secret for image name ([7d14038](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7d140384de6b65a7dae86b270df04bddd8e5e502))
* use non-breaking space for CPU temp separator ([48c8cc4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/48c8cc45f9c91e5518f3843bdc357393c502ec51))
* use PAT for release-please so releases trigger publish workflow ([53e4128](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/53e41281d6a917493255b1814c5fcaebcadbba07))
* use RELEASE_PAT for parent repo dispatch ([713c21a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/713c21af09d0e84c8dd79a950bcbed7aca4fbb06))
* use vivid primary bg for review status bar on dark themes ([f1dab61](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f1dab61e25f99ea91259048d91fe036c13046741))

## [11.13.3-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.13.2-alpha.1...v11.13.3-alpha.1) (2026-03-03)


### Bug Fixes

* metadata not syncing on review and pause toggle not flipping ([40f4ca0](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/40f4ca0550497d3b1e703e3f6807f78d42df6ea6))

## [11.13.2-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.13.1-alpha.1...v11.13.2-alpha.1) (2026-03-03)


### Bug Fixes

* improve font rendering and Blockbuster theme legibility ([2b82738](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2b82738897675d52c3025a1639c8806172695610))

## [11.13.1-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.13.0-alpha.1...v11.13.1-alpha.1) (2026-03-03)


### Bug Fixes

* deduplicate job defaults in test factories ([28b80c8](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/28b80c8758ccd28c2cc31c3799cfca5a6c878a92))
* exclude colorScheme.ts from SonarCloud duplication detection ([2936e5d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2936e5d7e83fd2954c7347afeb08e9196d2e0843))
* resolve 44 SonarCloud high-impact code smells ([b0ff5ad](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b0ff5addbb70a420b4613d1e165279eab4011c1a))
* resolve remaining 8 SonarCloud high-impact issues ([4c945ea](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4c945ea8ff8c45a732136235e0dd8b356aea50aa))

## [11.13.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.12.2-alpha.1...v11.13.0-alpha.1) (2026-03-03)


### Features

* move stats bar and auto-start toggle to global header, add themes ([480cebc](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/480cebcf041fc03699a278bd5342c1653becd8d2))

## [11.12.2-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.12.1-alpha.1...v11.12.2-alpha.1) (2026-03-02)


### Bug Fixes

* address SonarCloud reliability bugs ([d8d5ed7](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d8d5ed7ba54a269fe22a6d4c8c551de2cefc56ad))

## [11.12.1-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.12.0-alpha.1...v11.12.1-alpha.1) (2026-03-02)


### Bug Fixes

* address SonarCloud security findings ([127573e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/127573ed5b084369b019bcb24a75f1b428c2e755))

## [11.12.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.11.1-alpha.1...v11.12.0-alpha.1) (2026-03-02)


### Features

* display folder sizes in file browser ([6c650ea](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6c650eaf11772959d85ba1da3b5b7f00009f7d24))

## [11.11.1-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.11.0-alpha.1...v11.11.1-alpha.1) (2026-03-02)


### Bug Fixes

* breadcrumb hover too dark on dark mode ([3449f94](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/3449f94310d39254b3bf40146a888b29665217e4))

## [11.11.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.10.0-alpha.1...v11.11.0-alpha.1) (2026-03-02)


### Features

* file permissions display, fix-permissions, host paths, bulk delete fix ([a2be5d4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a2be5d4a9f2e0ede9337d29979a9e0d24e68f168))

## [11.10.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.9.0-alpha.1...v11.10.0-alpha.1) (2026-03-02)


### Features

* add warning banner to file browser page ([e16451e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e16451e59c4186a10b2d156f6eff55e08d9cb6e9))

## [11.9.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.8.0-alpha.1...v11.9.0-alpha.1) (2026-03-02)


### Features

* bulk delete with confirmation, match tab styling to settings ([776bacb](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/776bacbf37e9997db4df9bff89e70fe20ef55084))

## [11.8.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.7.1-alpha.1...v11.8.0-alpha.1) (2026-03-02)


### Features

* file browser with browsable move dialog ([af13ab2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/af13ab2719b7983d4ebe4904769ff7b1d83c9aba))

## [11.7.1-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.7.0-alpha.1...v11.7.1-alpha.1) (2026-03-02)


### Bug Fixes

* show waiting_transcode status with yellow color instead of gray ([22dd128](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/22dd1284c03b7928c41f7c975860477d4beed796))

## [11.7.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.6.0-alpha.1...v11.7.0-alpha.1) (2026-03-02)


### Features

* condense dashboard into unified status bar ([52d8e08](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/52d8e08c160559ff4878fa6f840044f43aa205d6))
* move drives page into settings as a tab ([f494bd7](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f494bd7a7897993979e493aab1c76004e60226bb))
* proxy metadata requests through ARM API ([6d343f7](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6d343f7c90522efd79fd392fb579703b06a6fcf5))


### Bug Fixes

* resolve TypeScript error and update arm_client tests ([92af79a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/92af79a0e0a9db19cf37c4b7df36a8fbc5da1c5d))
* surface real ARM API errors instead of generic "unreachable" message ([42c8988](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/42c8988c238e347a69fcd24dacca9316ec67d6e2))

## [11.6.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.5.1-alpha.1...v11.6.0-alpha.1) (2026-03-01)


### Features

* per-job transcode config overrides UI ([f0638b3](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f0638b32ce42d3e14aaa5725de2d7b7fad2b19f9))


### Bug Fixes

* prevent false 100% progress during MakeMKV scan phase ([11a52d5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/11a52d5e6fcdb7473cf2514505e8440a9b564fee))
* read full progress file so PRGT phase messages are not missed ([c8c6e62](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c8c6e62279dbdee357db15602f5fede439026782))

## [11.5.1-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.5.0-alpha.1...v11.5.1-alpha.1) (2026-02-28)


### Bug Fixes

* clamp rip progress to 100% when all tracks are ripped ([92f32d1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/92f32d1c3f4dfc553abac13efa1769698ad5fbcb))

## [11.5.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.4.1-alpha.1...v11.5.0-alpha.1) (2026-02-28)


### Features

* enrich transcoder job card with poster, type badge, and metadata ([c27c48e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c27c48ec5fe2332adfec5419232bfcc86d5c9782))

## [11.4.1-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.4.0-alpha.1...v11.4.1-alpha.1) (2026-02-28)


### Bug Fixes

* increase transcoder client timeout to 15s read / 5s connect ([f91a9a0](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f91a9a00a8babaf0f8b022d0cb1ce76b969844a9))

## [11.4.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.3.0-alpha.1...v11.4.0-alpha.1) (2026-02-28)


### Features

* per-job transcoder log previews and plain-text log parsing ([0b843bd](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/0b843bdba165886f6f29abcb920999ac1326c6a6))


### Bug Fixes

* update plain text log parser test to match regex parsing ([ab6be9b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ab6be9b8833fbf15a289144ee711bc985388c09c))

## [11.3.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.2.0-alpha.1...v11.3.0-alpha.1) (2026-02-28)


### Features

* progress bar tracks overall disc, per-job pause, year parsing fix, review pane improvements ([e958f6d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e958f6dd019822b02fbc7e3a5203d4ba5b87e1c4))
* show log_level_libraries on transcoder config page ([be060e7](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/be060e7d3b76dcfcdfc59368fd39eb2f7526ebf7))
* sortable column headers on log pages ([a447f7e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a447f7e66338bd1751ea65a1566ae975ee055fd6))
* structured logging with StructuredLogViewer for ARM and transcoder ([cf222f1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/cf222f191d1e47f00012e44545f1a1debfd34442))
* switch favicon to white ARM logo ([36d950e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/36d950e56ea216948c1f4309ab9917109ace080d))


### Bug Fixes

* catch RuntimeError and OSError in httpx client exception handlers ([c0d56a5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c0d56a50347cd1a04c6a466df5992df40f195135))
* prevent FOUC by hiding body until CSS loads ([99313a1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/99313a165054b3ebf69e825d7808a58e613262f6))
* prevent layout jump in review widget InlineLogFeed ([9fb6196](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9fb61966f973a37a4874557b1f1617b4eea1dc44))
* rename "Accepting Discs" toggle label to "Auto-Start" ([001054d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/001054dad74162940bdb777fb76760aaee106ca9))
* serve root-level static files and prevent path traversal in SPA catch-all ([c190797](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c190797b4ffcc4280579eb9dc2649652f572a98a))
* TMDb metadata provider fallback, error handling, and logging ([b075b1b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b075b1b44db7b5bfb1423523fbeb4635192ba482))

## [11.2.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.1.1-alpha.1...v11.2.0-alpha.1) (2026-02-28)


### Features

* add connection status visibility for ARM and transcoder services ([044660c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/044660c015ad728d1e2f6ea7ccaad89fb3a91898))
* add MusicBrainz search for audio CDs ([938fb6e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/938fb6e8a0cf1a87232442e0d27a8019e1ce5b20))
* add structured fields, track comparison, and card flip animation ([b90fb3e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b90fb3e8266c9246e71620b518014aeaf5ecdddd))


### Bug Fixes

* harden MusicBrainz search and cover art handling ([c6127f1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c6127f1ae539bd47b439a666adb65284a1a23170))
* remove redundant type comparison in MusicSearch flip card ([c1b88fb](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c1b88fb365335d9ab9cae5b5d7520a7491eb5fc7))

## [11.1.1-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.1.0-alpha.1...v11.1.1-alpha.1) (2026-02-26)


### Bug Fixes

* send plain media title in webhook payload ([17a5310](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/17a531010245b77563772f4b30ebb87b92f098dd))
* use vivid primary bg for review status bar on dark themes ([f1dab61](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/f1dab61e25f99ea91259048d91fe036c13046741))

## [11.1.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.0.1-alpha.1...v11.1.0-alpha.1) (2026-02-26)


### Features

* add CRC database lookup and submit to job detail and review widget ([28ca62d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/28ca62d7d611f67925a1ce4b50c4504b8afeea4b))


### Bug Fixes

* restore pointer cursor on buttons for Tailwind v4 ([6fb102e](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/6fb102e8664d900b4ff3193326965322dda15f38))

## [11.0.1-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v11.0.0-alpha.1...v11.0.1-alpha.1) (2026-02-26)


### Bug Fixes

* remove dead RIPMETHOD_DVD and RIPMETHOD_BR config fields ([1077a62](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/1077a62aa55e5ec6515de057717a58d20ab7e866))
* replace hardcoded paths with env vars in standalone compose ([5d365bb](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5d365bbe45ac067dd04ff8dec0345ebd8a1ba68d))

## [11.0.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v10.1.0-alpha.1...v11.0.0-alpha.1) (2026-02-25)


### ⚠ BREAKING CHANGES

* /api/settings/bash-script endpoints removed.

### Features

* replace bash script notification with ARM config fields ([be3e548](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/be3e54898ff3b451b5720d24381385607af16664))

## [10.1.0-alpha.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v10.0.0-alpha.1...v10.1.0-alpha.1) (2026-02-25)


### Features

* add 14 color scheme themes with LCARS styling and sidebar layout refinements ([bf05167](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/bf051673ba6866e61c1948b85ebfba17367f5b9f))
* add disc type icon to review widget and minor cleanup ([48ac784](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/48ac784b7952072e7893927570a7613799157594))
* Add settings page, transcoder management, and log viewer ([7f82eb4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7f82eb4cffe76cadb3c30a955016759b37cf9e6c))
* add test coverage reporting with Codecov ([58891f4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/58891f4a6465700427bb3bb9b33189b932901dbe))
* Add title search and metadata matching to job detail page ([85e4487](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/85e4487193634655dff3ed204abbe0e3f8f64437))
* add UHD capable toggle for Blu-ray drives ([5d1363d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5d1363d64630214b969acaa8aafcee7b414e4dfd))
* **api:** add frontend API layer and types for new backend features ([ec201a5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ec201a5d7f82ddbd94a6cc6e57d4b643384102e5))
* **backend:** add system monitoring, job control, and metadata testing ([ed51a3b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ed51a3b922486d44288db7e77c0b36cbc8622982))
* **components:** add system stats, disc review, and rip settings components ([d83efca](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d83efca113991207ed45b3773a469663baf31ff0))
* dashboard improvements — drive names, disc icons, editable metadata, 4K UHD support, favicon, page titles ([ed497d3](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ed497d3a295330e7417ccd589bf1e5cdf453ea79))
* display transcoder live stats (CPU, temp, memory) in sidebar ([2b6ff34](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2b6ff3491c216fe8b48cfa486611ac2bf1a070b8))
* expose imdb_id and poster_url auto/manual variants in API schema ([26a51fe](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/26a51fe73dfa172755dc7086ad920abf6612ee6c))
* LCARS theme panel redesign with structural frames and pill inputs ([c048b08](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c048b080d683750d96468cd30bdef7f42013993b))
* notify ARM-neu to update submodule on release ([b1bdd35](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b1bdd3572d555adf23b506457491fc7db0327885))
* **settings:** overhaul settings with search, metadata testing, and appearance ([076f2d0](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/076f2d02229d5a45094370df25203c26ba333511))
* **theme:** add customizable color scheme system ([81371b2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/81371b2253bafbfded7af846a779a6ba62b9e81d))
* track progress on dashboard cards + auto-refresh job detail ([acca233](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/acca233fa896b3c373b89ec41563a601e90d66d3))
* **ui:** integrate theme system and enhance dashboard, drives, and jobs ([d10e45c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d10e45c1446e07d5c756b9387e3a80d21aa5107f))


### Bug Fixes

* add missing drive_names to emptyDashboard in store ([9d7ef4d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9d7ef4de970fee9e5db65d011bd175294e8d7e0d))
* add missing transcoder_system_stats to +page.svelte default ([d431bdf](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d431bdffea151c288bd6309c3bca0a783681ebb2))
* add null guard for settings in armSettingsSection snippet ([fc334f9](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fc334f9d545043ba836dadee6b31556dc850e252))
* add spacing between CPU percent and temperature display ([549e173](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/549e173e31dc54b387a22481a28c65b53a083621))
* configure release-please to update VERSION file ([d453a07](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d453a07a50950e3057953b1ab83cb293f6c92209))
* display friendly disc type labels instead of raw values ([ea7bf8b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ea7bf8b79e399013c988684e2095a15de46c3f0b))
* pin frontend build stage to native platform for multi-arch builds ([407e856](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/407e8562990772c085c62ca4567d57fe0e32082f))
* remove UNIDENTIFIED_EJECT from settings page ([4ad9835](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4ad98352117d68356422e8a18a47db32c5625fd0))
* resolve 6 TypeScript errors in frontend type checking ([e4d9ceb](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e4d9ceb9226e6b1a50fbe903c2c66b3ec475b5b5))
* resolve all svelte-check warnings ([4526227](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4526227d3d0180032e6c59ddcdbd778795454e08))
* Resolve dashboard transcoder section flickering ([7d3add6](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7d3add64c9617e9f05adab3a4584b2c832d2ddd3))
* resolve flake8 lint errors ([a141cee](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a141cee18e0ee44d452a90f6707a939bdae71ca7))
* show storage section on transcoder tab ([17cb5b5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/17cb5b54f5e422a5841daa8a6bec12dabff27a55))
* sync Config model with actual ARM database schema ([5306dab](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5306dabbb5f10f006e8e471ff1330afe25bcbc4e))
* sync Config model with ARM DB schema and add missing active statuses ([fe950c1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fe950c191df8086deac9ca4fd7af6d6a4f6f6668))
* use DOCKERHUB_USERNAME secret for image name ([7d14038](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7d140384de6b65a7dae86b270df04bddd8e5e502))
* use non-breaking space for CPU temp separator ([48c8cc4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/48c8cc45f9c91e5518f3843bdc357393c502ec51))
* use PAT for release-please so releases trigger publish workflow ([53e4128](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/53e41281d6a917493255b1814c5fcaebcadbba07))
* use RELEASE_PAT for parent repo dispatch ([713c21a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/713c21af09d0e84c8dd79a950bcbed7aca4fbb06))

## [0.9.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v0.8.0...v0.9.0) (2026-02-22)


### Features

* add 14 color scheme themes with LCARS styling and sidebar layout refinements ([bf05167](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/bf051673ba6866e61c1948b85ebfba17367f5b9f))
* LCARS theme panel redesign with structural frames and pill inputs ([c048b08](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/c048b080d683750d96468cd30bdef7f42013993b))

## [0.8.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v0.7.0...v0.8.0) (2026-02-20)


### Features

* expose imdb_id and poster_url auto/manual variants in API schema ([26a51fe](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/26a51fe73dfa172755dc7086ad920abf6612ee6c))

## [0.7.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v0.6.0...v0.7.0) (2026-02-20)


### Features

* track progress on dashboard cards + auto-refresh job detail ([acca233](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/acca233fa896b3c373b89ec41563a601e90d66d3))


### Bug Fixes

* sync Config model with actual ARM database schema ([5306dab](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5306dabbb5f10f006e8e471ff1330afe25bcbc4e))
* sync Config model with ARM DB schema and add missing active statuses ([fe950c1](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/fe950c191df8086deac9ca4fd7af6d6a4f6f6668))

## [0.6.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v0.5.0...v0.6.0) (2026-02-19)


### Features

* add disc type icon to review widget and minor cleanup ([48ac784](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/48ac784b7952072e7893927570a7613799157594))
* add test coverage reporting with Codecov ([58891f4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/58891f4a6465700427bb3bb9b33189b932901dbe))
* add UHD capable toggle for Blu-ray drives ([5d1363d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/5d1363d64630214b969acaa8aafcee7b414e4dfd))


### Bug Fixes

* display friendly disc type labels instead of raw values ([ea7bf8b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ea7bf8b79e399013c988684e2095a15de46c3f0b))

## [0.5.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v0.4.2...v0.5.0) (2026-02-19)


### Features

* dashboard improvements — drive names, disc icons, editable metadata, 4K UHD support, favicon, page titles ([ed497d3](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ed497d3a295330e7417ccd589bf1e5cdf453ea79))


### Bug Fixes

* add missing drive_names to emptyDashboard in store ([9d7ef4d](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/9d7ef4de970fee9e5db65d011bd175294e8d7e0d))
* resolve all svelte-check warnings ([4526227](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4526227d3d0180032e6c59ddcdbd778795454e08))

## [0.4.2](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v0.4.1...v0.4.2) (2026-02-18)


### Bug Fixes

* remove UNIDENTIFIED_EJECT from settings page ([4ad9835](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/4ad98352117d68356422e8a18a47db32c5625fd0))

## [0.4.1](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v0.4.0...v0.4.1) (2026-02-16)


### Bug Fixes

* configure release-please to update VERSION file ([d453a07](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d453a07a50950e3057953b1ab83cb293f6c92209))

## [0.4.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v0.3.0...v0.4.0) (2026-02-16)


### Features

* notify ARM-neu to update submodule on release ([b1bdd35](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/b1bdd3572d555adf23b506457491fc7db0327885))


### Bug Fixes

* use PAT for release-please so releases trigger publish workflow ([53e4128](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/53e41281d6a917493255b1814c5fcaebcadbba07))
* use RELEASE_PAT for parent repo dispatch ([713c21a](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/713c21af09d0e84c8dd79a950bcbed7aca4fbb06))

## [0.3.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v0.2.0...v0.3.0) (2026-02-16)


### Features

* display transcoder live stats (CPU, temp, memory) in sidebar ([2b6ff34](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/2b6ff3491c216fe8b48cfa486611ac2bf1a070b8))


### Bug Fixes

* add missing transcoder_system_stats to +page.svelte default ([d431bdf](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d431bdffea151c288bd6309c3bca0a783681ebb2))
* add spacing between CPU percent and temperature display ([549e173](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/549e173e31dc54b387a22481a28c65b53a083621))
* pin frontend build stage to native platform for multi-arch builds ([407e856](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/407e8562990772c085c62ca4567d57fe0e32082f))
* resolve 6 TypeScript errors in frontend type checking ([e4d9ceb](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/e4d9ceb9226e6b1a50fbe903c2c66b3ec475b5b5))
* resolve flake8 lint errors ([a141cee](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/a141cee18e0ee44d452a90f6707a939bdae71ca7))
* show storage section on transcoder tab ([17cb5b5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/17cb5b54f5e422a5841daa8a6bec12dabff27a55))
* use DOCKERHUB_USERNAME secret for image name ([7d14038](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7d140384de6b65a7dae86b270df04bddd8e5e502))
* use non-breaking space for CPU temp separator ([48c8cc4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/48c8cc45f9c91e5518f3843bdc357393c502ec51))

## [0.2.0](https://github.com/uprightbass360/automatic-ripping-machine-ui/compare/v0.1.0...v0.2.0) (2026-02-15)


### Features

* Add settings page, transcoder management, and log viewer ([7f82eb4](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7f82eb4cffe76cadb3c30a955016759b37cf9e6c))
* Add title search and metadata matching to job detail page ([85e4487](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/85e4487193634655dff3ed204abbe0e3f8f64437))
* **api:** add frontend API layer and types for new backend features ([ec201a5](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ec201a5d7f82ddbd94a6cc6e57d4b643384102e5))
* **backend:** add system monitoring, job control, and metadata testing ([ed51a3b](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/ed51a3b922486d44288db7e77c0b36cbc8622982))
* **components:** add system stats, disc review, and rip settings components ([d83efca](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d83efca113991207ed45b3773a469663baf31ff0))
* **settings:** overhaul settings with search, metadata testing, and appearance ([076f2d0](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/076f2d02229d5a45094370df25203c26ba333511))
* **theme:** add customizable color scheme system ([81371b2](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/81371b2253bafbfded7af846a779a6ba62b9e81d))
* **ui:** integrate theme system and enhance dashboard, drives, and jobs ([d10e45c](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/d10e45c1446e07d5c756b9387e3a80d21aa5107f))


### Bug Fixes

* Resolve dashboard transcoder section flickering ([7d3add6](https://github.com/uprightbass360/automatic-ripping-machine-ui/commit/7d3add64c9617e9f05adab3a4584b2c832d2ddd3))

## Changelog
# Breaking change marker
