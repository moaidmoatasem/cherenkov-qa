# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0](https://github.com/moaidmoatasem/cherenkov-qa/compare/v1.3.0...v1.4.0) (2026-08-16)


### Features

* Add credential loading and --json support across CLI commands ([4bc6fd9](https://github.com/moaidmoatasem/cherenkov-qa/commit/4bc6fd9db7e2867c2de8c54bf1b466844f10f94b))
* Add Plugin SDK architecture and hipaa compliance reference plugin ([83b833f](https://github.com/moaidmoatasem/cherenkov-qa/commit/83b833fcefdef97665414727a39b55325daacfec))
* Add Test Template Marketplace registry and CLI commands ([1097a9f](https://github.com/moaidmoatasem/cherenkov-qa/commit/1097a9fdf11cb6ed9aa58922389386781794b4cf))
* **asyncapi:** wire AsyncAPI into `validate --source`; document protocol choices ([#968](https://github.com/moaidmoatasem/cherenkov-qa/issues/968)) ([7b3b11c](https://github.com/moaidmoatasem/cherenkov-qa/commit/7b3b11cc2491c5bf55391bf45f8839df5d6c3795))
* **brainmap:** Obsidian brain map — extract, reconcile, publish ([#976](https://github.com/moaidmoatasem/cherenkov-qa/issues/976)) ([b583de1](https://github.com/moaidmoatasem/cherenkov-qa/commit/b583de1e38f182b596c1cae53cbb58fd88bd101c))
* **brainmap:** resolve helper-composed API paths; keep the panel current ([#981](https://github.com/moaidmoatasem/cherenkov-qa/issues/981)) ([8bef571](https://github.com/moaidmoatasem/cherenkov-qa/commit/8bef571e2cdb810e71d56e73f3f314b08043756d))
* **certificate:** wire real certificate verification into Dashboard, delete 4 orphaned mock screens ([#868](https://github.com/moaidmoatasem/cherenkov-qa/issues/868)) ([2270152](https://github.com/moaidmoatasem/cherenkov-qa/commit/2270152852bae85af717011e0585808cf8913366))
* **cli:** add logical command groups with backwards-compatible aliases ([#842](https://github.com/moaidmoatasem/cherenkov-qa/issues/842)) ([8f709bf](https://github.com/moaidmoatasem/cherenkov-qa/commit/8f709bfc4805614af36c3ef2a90f9b622a3391f9))
* **cli:** agent-discoverability surface — `agent init`, `docs`, `check-suite --json` ([#931](https://github.com/moaidmoatasem/cherenkov-qa/issues/931)) ([19a7c36](https://github.com/moaidmoatasem/cherenkov-qa/commit/19a7c36162c4f90e3ca87aa82a85b0694dd7be48))
* **conformance:** add conformance trend API + tests ([#767](https://github.com/moaidmoatasem/cherenkov-qa/issues/767)) ([2ebd253](https://github.com/moaidmoatasem/cherenkov-qa/commit/2ebd25344140869e6dc413705b3c7c3341aca3a8))
* **conformance:** alert policies + auto-regenerate mode ([#768](https://github.com/moaidmoatasem/cherenkov-qa/issues/768), [#769](https://github.com/moaidmoatasem/cherenkov-qa/issues/769)) ([c4f6b2b](https://github.com/moaidmoatasem/cherenkov-qa/commit/c4f6b2bfe51efece26a8d4a1cf49c2a014b24bd0))
* **conformance:** continuous conformance trend + regression detection ([#767](https://github.com/moaidmoatasem/cherenkov-qa/issues/767) [#771](https://github.com/moaidmoatasem/cherenkov-qa/issues/771)) ([4c5b4f2](https://github.com/moaidmoatasem/cherenkov-qa/commit/4c5b4f2eed561d3b62be40bbf2f4c995deab6138))
* **core:** add unified StoragePort + SQLite adapter and UnifiedEventBus ([#840](https://github.com/moaidmoatasem/cherenkov-qa/issues/840)) ([81ef8f4](https://github.com/moaidmoatasem/cherenkov-qa/commit/81ef8f42e15432b53a6e48ac6433d08835dced3d))
* **core:** implement stacked PR engine + layer guard + merge queue (conductor) ([#835](https://github.com/moaidmoatasem/cherenkov-qa/issues/835)) ([63de6bc](https://github.com/moaidmoatasem/cherenkov-qa/commit/63de6bcde9b30b75bd9c8d8d16a39affbefa1972))
* **coverage:** add coverage map API + tests ([#770](https://github.com/moaidmoatasem/cherenkov-qa/issues/770) #tech-debt fix #supplier-273 ([5b75fd9](https://github.com/moaidmoatasem/cherenkov-qa/commit/5b75fd9eb7f9f36fb10b05f970269445a53493d4))
* **coverage:** add coverage map API + tests ([#770](https://github.com/moaidmoatasem/cherenkov-qa/issues/770) #tech-debt fix #supplier-273) ([3ebc339](https://github.com/moaidmoatasem/cherenkov-qa/commit/3ebc339eb1ab7315da5f5e15f35fdf7bcd6d4267))
* **coverage:** add PR coverage-map comment integration ([#770](https://github.com/moaidmoatasem/cherenkov-qa/issues/770), [#766](https://github.com/moaidmoatasem/cherenkov-qa/issues/766)) ([4987cd9](https://github.com/moaidmoatasem/cherenkov-qa/commit/4987cd99bedc1a279a2309944195428f48af3d90))
* **design-system:** add comprehensive color tokens to Tailwind theme ([47ab854](https://github.com/moaidmoatasem/cherenkov-qa/commit/47ab85469472e70fb1c050a266806492bf39e8db))
* **docs:** 1.4 Diátaxis documentation consolidation, diagrams, and verification scripts ([48f555e](https://github.com/moaidmoatasem/cherenkov-qa/commit/48f555e26a1370c1a314667bf823332a9d9d221c))
* **enterprise:** Phase 13 Multi-tenant data isolation and SAML integration ([#755](https://github.com/moaidmoatasem/cherenkov-qa/issues/755), [#756](https://github.com/moaidmoatasem/cherenkov-qa/issues/756), [#757](https://github.com/moaidmoatasem/cherenkov-qa/issues/757)) ([fcf2217](https://github.com/moaidmoatasem/cherenkov-qa/commit/fcf22173893a52a0321f9a96d0c09c31f4151be0))
* **events:** wire UnifiedEventBus into orchestrator + MCP bridge ([#844](https://github.com/moaidmoatasem/cherenkov-qa/issues/844)) ([252a7f6](https://github.com/moaidmoatasem/cherenkov-qa/commit/252a7f6277295f58186be0dcff258f0951e0d695))
* **integrity:** measure the integrity detector, then make it real ([#989](https://github.com/moaidmoatasem/cherenkov-qa/issues/989)) ([3f4b499](https://github.com/moaidmoatasem/cherenkov-qa/commit/3f4b4997c21a361210719b7d8b869ed9ec7614a1))
* **journeys:** make the workflow a first-class, configurable resource ([#925](https://github.com/moaidmoatasem/cherenkov-qa/issues/925)) ([9279de2](https://github.com/moaidmoatasem/cherenkov-qa/commit/9279de287a2d8517fa396e69de9743d536d44d51))
* **mobile:** wire flow execution, source-derived planning, assertion gate ([#960](https://github.com/moaidmoatasem/cherenkov-qa/issues/960)) ([b462f6b](https://github.com/moaidmoatasem/cherenkov-qa/commit/b462f6b35b3a4fa83b9b5e299e5efaf931349ebb))
* **persistence:** store divergence findings so the dashboard serves real data ([#903](https://github.com/moaidmoatasem/cherenkov-qa/issues/903)) ([#913](https://github.com/moaidmoatasem/cherenkov-qa/issues/913)) ([7aef8b3](https://github.com/moaidmoatasem/cherenkov-qa/commit/7aef8b314e2f855fa22916db465fedd5ea5e4ac9))
* **qa:** Complete execution plan items 13-23 ([#928](https://github.com/moaidmoatasem/cherenkov-qa/issues/928)) ([4fa3af9](https://github.com/moaidmoatasem/cherenkov-qa/commit/4fa3af96355b9676eba1ad4438e55767767111fb))
* Scaffold MCP server and Playwright plugin for integration ([12152c9](https://github.com/moaidmoatasem/cherenkov-qa/commit/12152c94886d112e2050abd7f5e9134cb8957ed0))
* **settings:** Export ModelProviderSettings from index ([0a58760](https://github.com/moaidmoatasem/cherenkov-qa/commit/0a58760f50897f78b93d4c30e8f06d5ef7f1fba3))
* **triage:** D-3 reactive divergence tables + D-5 suggest-only healing endpoint ([489af17](https://github.com/moaidmoatasem/cherenkov-qa/commit/489af17b6b7928923b7002e92cf67d93d3fc617d))
* **triage:** PRODUCT_BUG bucket for post-execution failure classification ([#880](https://github.com/moaidmoatasem/cherenkov-qa/issues/880)) ([#883](https://github.com/moaidmoatasem/cherenkov-qa/issues/883)) ([ae2c130](https://github.com/moaidmoatasem/cherenkov-qa/commit/ae2c13009b11c25ac3725c03ce546dc9d8c99f1c))
* **ui/guardian:** surface Spec Guardian API and dashboard widget ([#764](https://github.com/moaidmoatasem/cherenkov-qa/issues/764)/[#765](https://github.com/moaidmoatasem/cherenkov-qa/issues/765)/[#772](https://github.com/moaidmoatasem/cherenkov-qa/issues/772)) ([667c5fe](https://github.com/moaidmoatasem/cherenkov-qa/commit/667c5fea0a0e5920498f939c128aac8b176da9ec))
* **ui:** phase 2a reachability — code-split workspaces, mount signals screen, purge dead orphans ([ce02f3b](https://github.com/moaidmoatasem/cherenkov-qa/commit/ce02f3b10573e65228f8d3292ad562a4895329c7))
* **ui:** Phase 3 navigation & IA revamp (N-1..N-8) ([46b022a](https://github.com/moaidmoatasem/cherenkov-qa/commit/46b022a808eec0544928c85861f6f50f63a0e396))
* **ui:** Phase 4 journeys (J1-J3) — evidence disclosure, virtualization, authoring deep-links ([2bd248d](https://github.com/moaidmoatasem/cherenkov-qa/commit/2bd248d2f8c0ed8da966d41b88364cf1b941925d))
* **ui:** Phase 7 UX/a11y — focus traps, dialog semantics, density & motion preferences ([c30f861](https://github.com/moaidmoatasem/cherenkov-qa/commit/c30f8618230dd9b5c2811b07f820887ee947f82f))
* **ui:** Post-execution failure classification (closes [#880](https://github.com/moaidmoatasem/cherenkov-qa/issues/880)) ([4bcd668](https://github.com/moaidmoatasem/cherenkov-qa/commit/4bcd6686b38b397b57201a54d71d039e7b518fa9))
* **ui:** vanilla css design system foundation ([591422e](https://github.com/moaidmoatasem/cherenkov-qa/commit/591422e5f7a5637da54e1318fd4c44d81fc2b4a3))
* **verification:** add AST docstring remediator and standalone docstring stress tests ([eedbabc](https://github.com/moaidmoatasem/cherenkov-qa/commit/eedbabc067609b95409bd742c2ba2902bcaf94e2))
* **verification:** implement automated check_docstrings and check_docs_markdown scripts with tests ([88f0413](https://github.com/moaidmoatasem/cherenkov-qa/commit/88f041319592f7e1c700136b9b504cddb48b4cf5))
* **verify:** --json emits the report on stdout; fix a red flag gate on main ([#934](https://github.com/moaidmoatasem/cherenkov-qa/issues/934)) ([3dff064](https://github.com/moaidmoatasem/cherenkov-qa/commit/3dff064fdaeb5727c5c42305fdd561261fefa8ee))
* **web:** wire Live Surface Explorer (Phase 2b) ([1e87853](https://github.com/moaidmoatasem/cherenkov-qa/commit/1e87853e7427ee29197d9d31282f1bd597e4526c))


### Bug Fixes

* **airllm:** preserve model name and last raw output in complete_json retry loop ([#860](https://github.com/moaidmoatasem/cherenkov-qa/issues/860)) ([bb8e6d6](https://github.com/moaidmoatasem/cherenkov-qa/commit/bb8e6d6412df3b729214dd2448e05bce3298889b))
* **check-suite:** see compound assertions, and scope HALLUCINATED to the endpoint ([#990](https://github.com/moaidmoatasem/cherenkov-qa/issues/990)) ([3223c47](https://github.com/moaidmoatasem/cherenkov-qa/commit/3223c47f613a20ca88bbcad94926d3fb250415e9))
* **check-suite:** stop reporting response attributes as hallucinated fields ([#992](https://github.com/moaidmoatasem/cherenkov-qa/issues/992)) ([7300206](https://github.com/moaidmoatasem/cherenkov-qa/commit/7300206d831660d5104166cb5f5d525b75c585d4))
* **ci:** cross-platform path normalization in check_layer_imports.py and SKIP_DIRS in test_python_sources_parse.py ([41d120f](https://github.com/moaidmoatasem/cherenkov-qa/commit/41d120f333bc474dbf8d5d70dd4d1eebe67018f7))
* **ci:** export CHANGED_FILES in layer-guard; correct web/ui path in merge-queue ([#875](https://github.com/moaidmoatasem/cherenkov-qa/issues/875)) ([5e15ae9](https://github.com/moaidmoatasem/cherenkov-qa/commit/5e15ae9d6b02e45e004d74017beae2498a7218b9))
* **ci:** extend flag guard to ci/ templates; repair broken Jenkins invocation ([#966](https://github.com/moaidmoatasem/cherenkov-qa/issues/966)) ([3bf8c46](https://github.com/moaidmoatasem/cherenkov-qa/commit/3bf8c46cd899b32511d489d1368cbcc594df66ed))
* **ci:** green up the five red gates on main, two of which had never run ([#930](https://github.com/moaidmoatasem/cherenkov-qa/issues/930)) ([441cab8](https://github.com/moaidmoatasem/cherenkov-qa/commit/441cab890c70aeb6f459738a75a1de068318d3d1))
* **ci:** guard CI templates for flag drift; repair the Jenkins template ([#971](https://github.com/moaidmoatasem/cherenkov-qa/issues/971)) ([d3e0fc1](https://github.com/moaidmoatasem/cherenkov-qa/commit/d3e0fc1bacd55f5edfdd01b22caee4883159b95c))
* **ci:** make apply-rulesets.sh idempotent via upsert (PUT existing, POST new) ([#899](https://github.com/moaidmoatasem/cherenkov-qa/issues/899)) ([1df8e1d](https://github.com/moaidmoatasem/cherenkov-qa/commit/1df8e1da02aa632e0522804cab50d6cdaacbe1f0))
* **ci:** repair broken validate-smoke gate; rewrite dead epoch5 CLI test ([#904](https://github.com/moaidmoatasem/cherenkov-qa/issues/904)) ([8793115](https://github.com/moaidmoatasem/cherenkov-qa/commit/8793115db81aa41359dc53fc8bdc7d7c1c27ebdc))
* **ci:** repair layer-guard enforcement (real paths, valid context, dead branch patterns removed) ([916f293](https://github.com/moaidmoatasem/cherenkov-qa/commit/916f2933d9249175cc54a55080c824198c9b0f0f))
* **ci:** repoint retired cherenkov.py shim callers to ./bin/cherenkov; fix cherenkov review subcommand ([#892](https://github.com/moaidmoatasem/cherenkov-qa/issues/892)) ([7bd6ad2](https://github.com/moaidmoatasem/cherenkov-qa/commit/7bd6ad242ac318cbc78c8107f93979440abd9137))
* **ci:** stop the coverage job failing on live-server demo tests ([#906](https://github.com/moaidmoatasem/cherenkov-qa/issues/906)) ([#909](https://github.com/moaidmoatasem/cherenkov-qa/issues/909)) ([1ae65df](https://github.com/moaidmoatasem/cherenkov-qa/commit/1ae65df3c6e014f30cfc99ea63fe32094aa8b36d))
* **ci:** update smoke_test_polish.py for new CLI structure ([8ed8182](https://github.com/moaidmoatasem/cherenkov-qa/commit/8ed8182d7859489984de0f6d40ab9477b6ac1c0c))
* **cli:** clean the first-run surface — help scaffolding and init's next steps ([#985](https://github.com/moaidmoatasem/cherenkov-qa/issues/985)) ([07d24cf](https://github.com/moaidmoatasem/cherenkov-qa/commit/07d24cfc1685a46f7bb6a1034eeefb12d1503b96))
* **cli:** register orphaned `mobile` command; add capability coverage audit ([#959](https://github.com/moaidmoatasem/cherenkov-qa/issues/959)) ([3161455](https://github.com/moaidmoatasem/cherenkov-qa/commit/3161455f8673ee5db00d264599aa12eabfed713f))
* **cli:** resolve residual QA plan issues R1-R6 ([2b17c67](https://github.com/moaidmoatasem/cherenkov-qa/commit/2b17c67ba30a32988ebb5fffdbcbecc5f79765b3))
* **core:** take mypy to zero — declare the DataCollector optional import ([#969](https://github.com/moaidmoatasem/cherenkov-qa/issues/969)) ([45735c9](https://github.com/moaidmoatasem/cherenkov-qa/commit/45735c92620c125574880df370f2efd286a7fa83))
* **docs:** correct fabricated CLI invocations and Windows path separator in guard test ([9ec2df6](https://github.com/moaidmoatasem/cherenkov-qa/commit/9ec2df6bce10465174f280b8f887053451f9a129))
* **docs:** document federation + testerarmy commands (docs-parity gate) ([#947](https://github.com/moaidmoatasem/cherenkov-qa/issues/947)) ([70ddf3f](https://github.com/moaidmoatasem/cherenkov-qa/commit/70ddf3fe07d49ea1209c8b88d48f5987f0437e46))
* **docs:** green up docs-parity gate + real onboarding transcript verifier ([#936](https://github.com/moaidmoatasem/cherenkov-qa/issues/936)) ([687b727](https://github.com/moaidmoatasem/cherenkov-qa/commit/687b727890e5166b37e5b9421e939d6f6ddc3af7))
* **docs:** stop the docs site's 'latest' alias from moving backwards ([#987](https://github.com/moaidmoatasem/cherenkov-qa/issues/987)) ([068f78b](https://github.com/moaidmoatasem/cherenkov-qa/commit/068f78bd6b3b9dfe60a930e10183b93934f1fc41))
* **eject:** don't refuse a source checkout's own generated tests ([#986](https://github.com/moaidmoatasem/cherenkov-qa/issues/986)) ([017790e](https://github.com/moaidmoatasem/cherenkov-qa/commit/017790e0952a8b5bafdb518db19b5a0af53b97b2))
* **eject:** stop shipping CHERENKOV's own sabotaged fixtures into user repos ([#983](https://github.com/moaidmoatasem/cherenkov-qa/issues/983)) ([33b3e50](https://github.com/moaidmoatasem/cherenkov-qa/commit/33b3e5029e2ca51f69e13be21a90b054f6ddb674))
* **enterprise:** measure run statistics instead of fabricating them ([#974](https://github.com/moaidmoatasem/cherenkov-qa/issues/974)) ([50f0795](https://github.com/moaidmoatasem/cherenkov-qa/commit/50f079511af1e0b52dbf2517976e9f7a3da30d6c))
* **errors:** log swallowed failures in notifier, storage, web and webhook adapters ([#896](https://github.com/moaidmoatasem/cherenkov-qa/issues/896)) ([af9e5c4](https://github.com/moaidmoatasem/cherenkov-qa/commit/af9e5c4c03a595f8f01f91bad4b524aefeaf87d2))
* **errors:** propagate and log errors swallowed in core and pipeline stages ([#895](https://github.com/moaidmoatasem/cherenkov-qa/issues/895)) ([6805eb2](https://github.com/moaidmoatasem/cherenkov-qa/commit/6805eb2b790f3a9df2bf7c90ca3be0ca40e5e333))
* include password in real integration test POST /users to satisfy API validation\n\nCo-authored-by: Copilot &lt;223556219+Copilot@users.noreply.github.com&gt; ([#855](https://github.com/moaidmoatasem/cherenkov-qa/issues/855)) ([282e9c5](https://github.com/moaidmoatasem/cherenkov-qa/commit/282e9c5952a0d8ef90e0dd9000dcb3d419710950))
* **infra:** resolve issues 901, 905, 921 (untrack dist, fix desktop updater, correct budget docs) ([8c1debb](https://github.com/moaidmoatasem/cherenkov-qa/commit/8c1debb365ef763be515453f60aab040c62dabfe))
* **IntegrityHeatmap:** derive real scores from divergence severity data ([9f77b8c](https://github.com/moaidmoatasem/cherenkov-qa/commit/9f77b8c9b26abb6428bb7297395466996ee083f1))
* **integrity:** three detector bugs found by auditing 594 real test files ([#991](https://github.com/moaidmoatasem/cherenkov-qa/issues/991)) ([1586d70](https://github.com/moaidmoatasem/cherenkov-qa/commit/1586d70e279955830d175d84593241b8717abede))
* **mypy:** make CI mypy gate green (9 errors in 3 files fixed) ([#871](https://github.com/moaidmoatasem/cherenkov-qa/issues/871)) ([5fd9567](https://github.com/moaidmoatasem/cherenkov-qa/commit/5fd95678b2cda72f39efd5de91fe28f5282402e2))
* **ocr:** honor CHERENKOV_OCR_BINARY setting for OCR binary resolution ([#861](https://github.com/moaidmoatasem/cherenkov-qa/issues/861)) ([a5d88f7](https://github.com/moaidmoatasem/cherenkov-qa/commit/a5d88f729eb9d436ab62117f089e2bfa84c0878b))
* **ready-tickets:** CODEOWNERS owners, README compose pointer, LocalAI image tag ([#846](https://github.com/moaidmoatasem/cherenkov-qa/issues/846), [#849](https://github.com/moaidmoatasem/cherenkov-qa/issues/849), [#850](https://github.com/moaidmoatasem/cherenkov-qa/issues/850)) ([9b7a860](https://github.com/moaidmoatasem/cherenkov-qa/commit/9b7a860cc0956f4dd52372e60317d574931dce57))
* repair 168 files broken by autogenerated placeholder docstrings — main was unbuildable ([#953](https://github.com/moaidmoatasem/cherenkov-qa/issues/953)) ([f2c1883](https://github.com/moaidmoatasem/cherenkov-qa/commit/f2c1883b9b171e93fd9af937b27de12e4df19fd9))
* repair four Python files that do not parse, and gate against more ([#977](https://github.com/moaidmoatasem/cherenkov-qa/issues/977)) ([08a8e3a](https://github.com/moaidmoatasem/cherenkov-qa/commit/08a8e3ac8cdd75a8da650e39727febdd03ebd2b9))
* repair the 21 mypy errors, four of which were live bugs ([#967](https://github.com/moaidmoatasem/cherenkov-qa/issues/967)) ([64118e0](https://github.com/moaidmoatasem/cherenkov-qa/commit/64118e074a77eec775d340ce6fae78301344f373))
* **security:** path traversal, bootstrap auth bypass, hardcoded MCP JWT secret ([#894](https://github.com/moaidmoatasem/cherenkov-qa/issues/894)) ([ee4ce57](https://github.com/moaidmoatasem/cherenkov-qa/commit/ee4ce578200bdf823745994cc199fa99fbe5a624))
* serve real run data on the enterprise SLA view; stop faking support tickets ([#973](https://github.com/moaidmoatasem/cherenkov-qa/issues/973)) ([80420a1](https://github.com/moaidmoatasem/cherenkov-qa/commit/80420a15b56d1fb5557dad9d3fdc11827ad47e28))
* **settings:** Phase 5 truthful settings surface + event-loop-safe doctor/eject ([14760fe](https://github.com/moaidmoatasem/cherenkov-qa/commit/14760fe4d2059dcfb17506cd4b58f8e928ed7f9c))
* **settings:** Wire /api/v1/settings to real CherenkovSettings backend ([13cce9b](https://github.com/moaidmoatasem/cherenkov-qa/commit/13cce9b643a093470f182b7b6bf52210f4e9c9dc))
* **tests:** eliminate WSL-environment test hangs — mock live service calls and fix subprocess cleanup ([b44f936](https://github.com/moaidmoatasem/cherenkov-qa/commit/b44f936b2bb52458fae8d8975199452e7e99c4bb))
* **tests:** mock socket calls and service checks in test_probe_planner and test_cli_help_quality ([f4a0637](https://github.com/moaidmoatasem/cherenkov-qa/commit/f4a06370ccc325ccfd3cc5fa196f17ee96edee1d))
* **tests:** mock subprocess and verify engine in test_asyncapi_support and test_coverage ([3a22bc2](https://github.com/moaidmoatasem/cherenkov-qa/commit/3a22bc2ff09080e9ca9490b694ce9e31919098d2))
* **tests:** remove dead InferenceRouter tests broken by [#815](https://github.com/moaidmoatasem/cherenkov-qa/issues/815) AI-routing consolidation ([#877](https://github.com/moaidmoatasem/cherenkov-qa/issues/877)) ([3736cf3](https://github.com/moaidmoatasem/cherenkov-qa/commit/3736cf3d2e2644facd897e486461d3a49d0fb39d))
* **tests:** repair broken SAML user-sync test; fix dangling roadmap links ([#957](https://github.com/moaidmoatasem/cherenkov-qa/issues/957)) ([d05ce71](https://github.com/moaidmoatasem/cherenkov-qa/commit/d05ce71c937693837743562f29ab80e615c1e98b))
* **tests:** stabilize standalone tests for langchain tool, map cmd, and docker sandbox ([faa1dcf](https://github.com/moaidmoatasem/cherenkov-qa/commit/faa1dcf93a1635bbf2fc0c1bee9642d053b5d4c1))
* **test:** update mock assertion in test_verify_cmd.py for headers parameter ([2b12a70](https://github.com/moaidmoatasem/cherenkov-qa/commit/2b12a70e2f45c1836ecca8dd7008563d1c8af98c))
* **test:** update remaining mock assertion in test_verify_cmd.py ([c3af39f](https://github.com/moaidmoatasem/cherenkov-qa/commit/c3af39f636027f6560a09e3c90df92e8a45048e4))
* **ui:** eliminate e2e load-flake root causes at the source ([de2974a](https://github.com/moaidmoatasem/cherenkov-qa/commit/de2974aa9c8002cdcfe1407f4eaec17f952d40e7))
* **ui:** restore api_mocks.ts — the Playwright suite loaded zero tests ([#978](https://github.com/moaidmoatasem/cherenkov-qa/issues/978)) ([910ee48](https://github.com/moaidmoatasem/cherenkov-qa/commit/910ee48d807f785f31ea164ea1926aaf696781aa))
* **ui:** rewrite the a11y audit against the shipping IA, and fix the ten violations it found ([#980](https://github.com/moaidmoatasem/cherenkov-qa/issues/980)) ([c36d471](https://github.com/moaidmoatasem/cherenkov-qa/commit/c36d471065b53af68aa9c69027f5a3338d8a47ac))
* **ui:** time-box the auth probe so the shell cannot block on a slow doctor ([cc0387e](https://github.com/moaidmoatasem/cherenkov-qa/commit/cc0387e652ab7c316535d7f33ef783440b52de9b))
* **ui:** validate 48-test suite against live backend + logger json-safety ([df307ed](https://github.com/moaidmoatasem/cherenkov-qa/commit/df307edd6286947b419833b2e5f447b66960ece0))
* unbreak the dashboard build and make the link gate executable ([#958](https://github.com/moaidmoatasem/cherenkov-qa/issues/958)) ([25dcafd](https://github.com/moaidmoatasem/cherenkov-qa/commit/25dcafd02f4e06e33270dcebabb414be51634350))
* **validate:** print tightening suggestions; fix smoke test fixture scoping ([#891](https://github.com/moaidmoatasem/cherenkov-qa/issues/891)) ([#902](https://github.com/moaidmoatasem/cherenkov-qa/issues/902)) ([fed6c39](https://github.com/moaidmoatasem/cherenkov-qa/commit/fed6c39e9aaa56bf2bba4b4fc9920bb65d7abe23))


### Documentation

* **1.4:** synchronize 1.4 documentation parity, configure banner suppression, and clean test artifacts ([#1002](https://github.com/moaidmoatasem/cherenkov-qa/issues/1002)) ([fbb3697](https://github.com/moaidmoatasem/cherenkov-qa/commit/fbb369778cb324eba33955983e107d2f8c6a5516))
* add agentic test plan with measured coverage baseline ([#956](https://github.com/moaidmoatasem/cherenkov-qa/issues/956)) ([3568126](https://github.com/moaidmoatasem/cherenkov-qa/commit/3568126ccfe6768ba13c5c41e374ccb9c9208695))
* add Architecture landing page; fix README link + nav consistency ([#916](https://github.com/moaidmoatasem/cherenkov-qa/issues/916)) ([70be498](https://github.com/moaidmoatasem/cherenkov-qa/commit/70be4983269c964e123875fc2d2d3165210fa045))
* add platform direction handover to HANDOVER.md ([#911](https://github.com/moaidmoatasem/cherenkov-qa/issues/911)) ([6b1e6b0](https://github.com/moaidmoatasem/cherenkov-qa/commit/6b1e6b04800c320035a778e8ec8e5ba6c35ba4e3))
* align roadmap and backlog detail to north star; document `train` ([#955](https://github.com/moaidmoatasem/cherenkov-qa/issues/955)) ([5950b9b](https://github.com/moaidmoatasem/cherenkov-qa/commit/5950b9b7f346141e1fd3a010af11ba8046455006))
* author AGENT_COLLABORATION_PROTOCOL.md (parallel multi-agent safety) ([#873](https://github.com/moaidmoatasem/cherenkov-qa/issues/873)) ([44de078](https://github.com/moaidmoatasem/cherenkov-qa/commit/44de078cfaf16acdeae933c77739921128501186))
* author WAYS_OF_WORKING.md (branching, PRs, reviews, CI gates, DoR/DoD) ([#872](https://github.com/moaidmoatasem/cherenkov-qa/issues/872)) ([b2bbcee](https://github.com/moaidmoatasem/cherenkov-qa/commit/b2bbcee0271b27ce1addfb81f2225d85fdd1736b))
* comprehensive documentation overhaul — 100% coverage, consistency, and accuracy ([#912](https://github.com/moaidmoatasem/cherenkov-qa/issues/912)) ([0fa8a60](https://github.com/moaidmoatasem/cherenkov-qa/commit/0fa8a60893f2dbc2380c5cae8e5df26268812aae))
* connect platform direction to architecture ([6b645c2](https://github.com/moaidmoatasem/cherenkov-qa/commit/6b645c29e5f8092f8620b5a719865aef86ce02ba))
* consolidate CHERENKOV-QA documentation into version 1.4 ([5778b5b](https://github.com/moaidmoatasem/cherenkov-qa/commit/5778b5be20ca187db3a36fae350cdfa4f80a03ed))
* consolidate FE dashboard docs, archive parity audit ([#857](https://github.com/moaidmoatasem/cherenkov-qa/issues/857)) ([6ded9f6](https://github.com/moaidmoatasem/cherenkov-qa/commit/6ded9f6f5f1807b255cdc388b8baf7a20ec9a091))
* consolidate superseded/duplicate docs to _archive/ (SSOT) ([0d50e48](https://github.com/moaidmoatasem/cherenkov-qa/commit/0d50e488f86c0b0aa2fd82a9bc0539833cc9756f))
* correct command counts and group listings after mobile registration ([#965](https://github.com/moaidmoatasem/cherenkov-qa/issues/965)) ([3aef78c](https://github.com/moaidmoatasem/cherenkov-qa/commit/3aef78c9c17ee93e7f3fc6e058db8f16cc828580))
* define Quality Intelligence Platform ([#908](https://github.com/moaidmoatasem/cherenkov-qa/issues/908)) ([13ac770](https://github.com/moaidmoatasem/cherenkov-qa/commit/13ac7701dfd7fff39d28827d4d70e8842d37bb7e))
* **devops:** refine hostname and sanitizer checks for public docs clean ([b328ae9](https://github.com/moaidmoatasem/cherenkov-qa/commit/b328ae952773ae2a5c19465c6ded031f0df2c4ea))
* **fe:** Phase 8 spec/doc alignment — mark revamp implementation status ([0564041](https://github.com/moaidmoatasem/cherenkov-qa/commit/05640410c51f1c19afa57db5368b05489195d5b2))
* final review — align docs-site with Quality Intelligence Platform direction ([#914](https://github.com/moaidmoatasem/cherenkov-qa/issues/914)) ([d627a93](https://github.com/moaidmoatasem/cherenkov-qa/commit/d627a93e4507fa5f8e4d4fb8609e678f51b0396b))
* fix CLI reference flags that don't exist on the real commands ([#920](https://github.com/moaidmoatasem/cherenkov-qa/issues/920)) ([5f07a76](https://github.com/moaidmoatasem/cherenkov-qa/commit/5f07a767b4a9984a13426695b3ba590a8e827c05))
* **handover:** record 2026-08-16 alignment and test stabilization sweep ([b472ece](https://github.com/moaidmoatasem/cherenkov-qa/commit/b472ecea8ff4722bdfc9f9a4c608fe668f123b91))
* **handover:** record that the real_demo test failures are fixed ([#906](https://github.com/moaidmoatasem/cherenkov-qa/issues/906)) ([#910](https://github.com/moaidmoatasem/cherenkov-qa/issues/910)) ([c2cf403](https://github.com/moaidmoatasem/cherenkov-qa/commit/c2cf403a8feccd705f00e09310bd8253e02604a5))
* implement world-class documentation architecture (llms.txt, llms-full.txt, Diataxis INDEX.md, C4 Diagrams-as-Code, Vale, Spectral, docs-governance workflow) ([4c8e4f0](https://github.com/moaidmoatasem/cherenkov-qa/commit/4c8e4f0e7683767623d04fe036b20b024f454e7a))
* mark Phases -1 through 16 as complete in Master Roadmap ([eaeb7b2](https://github.com/moaidmoatasem/cherenkov-qa/commit/eaeb7b27df3bb7a0372770606ef0ce3db046210a))
* purge retired cherenkov.py entrypoint from current how-to docs ([#919](https://github.com/moaidmoatasem/cherenkov-qa/issues/919)) ([245ec3a](https://github.com/moaidmoatasem/cherenkov-qa/commit/245ec3a08e005b01212d0c7f092556a74dae486c))
* reading note on agentic-playwright, with what maps onto our gates ([#984](https://github.com/moaidmoatasem/cherenkov-qa/issues/984)) ([21eebb3](https://github.com/moaidmoatasem/cherenkov-qa/commit/21eebb322a9b02704151c4fef7f2204935ced619))
* reconcile docs around the Quality Intelligence Platform narrative ([#917](https://github.com/moaidmoatasem/cherenkov-qa/issues/917)) ([66708ab](https://github.com/moaidmoatasem/cherenkov-qa/commit/66708ab8c6b658bbc9c3e909181bfcfcf80d1325))
* reconcile MCP tool catalogue and transport with the codebase ([#918](https://github.com/moaidmoatasem/cherenkov-qa/issues/918)) ([ce45581](https://github.com/moaidmoatasem/cherenkov-qa/commit/ce45581fde5c2866fe78cf22c694498fe745857a))
* reconcile Phase 13/15/16 issue backlog against actual code ([#954](https://github.com/moaidmoatasem/cherenkov-qa/issues/954)) ([ea065a2](https://github.com/moaidmoatasem/cherenkov-qa/commit/ea065a2cae9465d809f1297ad0fb5e6b3b5159c6))
* reconcile README, wiki, and MCP-server README with current facts ([#915](https://github.com/moaidmoatasem/cherenkov-qa/issues/915)) ([41075b0](https://github.com/moaidmoatasem/cherenkov-qa/commit/41075b092ce0f3b1a67a684d5d5850a81add1fb3))
* reconcile ROADMAP section 3 integration tiers with the code ([#972](https://github.com/moaidmoatasem/cherenkov-qa/issues/972)) ([b4353b1](https://github.com/moaidmoatasem/cherenkov-qa/commit/b4353b1eead49b4c008c891971ce9daf433d483e))
* reconcile v1.3.0 across docs, CLI_GROUPS, release metadata ([e1b156a](https://github.com/moaidmoatasem/cherenkov-qa/commit/e1b156ae3879dc44c67c2973643cff930cd68064))
* record 7 defects found by a real-user walkthrough of the product ([#975](https://github.com/moaidmoatasem/cherenkov-qa/issues/975)) ([80da595](https://github.com/moaidmoatasem/cherenkov-qa/commit/80da59503d5bab470ec905876b17e8c71e840c2e))
* record CI green on main; correct the Phase 13 org-management claim ([#970](https://github.com/moaidmoatasem/cherenkov-qa/issues/970)) ([5fce9f7](https://github.com/moaidmoatasem/cherenkov-qa/commit/5fce9f7d6079ebdfc44f330dafbf0a550fd6f4d6))
* resolve broken relative links for clean strict mkdocs build ([9f96cde](https://github.com/moaidmoatasem/cherenkov-qa/commit/9f96cde15dc050a8235897f213989c6a2635046e))
* retire cherenkov.py from QA validation runbook ([#922](https://github.com/moaidmoatasem/cherenkov-qa/issues/922)) ([#932](https://github.com/moaidmoatasem/cherenkov-qa/issues/932)) ([e6b1fc3](https://github.com/moaidmoatasem/cherenkov-qa/commit/e6b1fc3923f1673e76c5b07abf2c2750195a3f04))
* **reviews:** TesterArmy teardown + phased plan for the gaps it exposes ([#929](https://github.com/moaidmoatasem/cherenkov-qa/issues/929)) ([2c11997](https://github.com/moaidmoatasem/cherenkov-qa/commit/2c119976aa7193f0d2eb99f1487c5eaf20bd7cb2))
* settle two open questions with evidence, and drop a stale ignore ([#982](https://github.com/moaidmoatasem/cherenkov-qa/issues/982)) ([8074c4d](https://github.com/moaidmoatasem/cherenkov-qa/commit/8074c4d285e586ddac1548d165b00cdb4b5ca579))
* setup MkDocs configuration and Petstore Quickstart guide ([98e0e0e](https://github.com/moaidmoatasem/cherenkov-qa/commit/98e0e0ebc67317b962f03dcd2825d12a4b93f8bd))
* state the security capability accurately; document CHERENKOV_DAST_ENABLED ([#988](https://github.com/moaidmoatasem/cherenkov-qa/issues/988)) ([294a292](https://github.com/moaidmoatasem/cherenkov-qa/commit/294a2925366c0706f06d0a95394ce1193b27380a))
* update HANDOVER.md with 2026-08-10 tech-debt sweep ([986658c](https://github.com/moaidmoatasem/cherenkov-qa/commit/986658c4b500773cacdc72de1d8dc8335e9d6606))
* update HANDOVER.md with completed roadmap Phases 13-16 ([900863a](https://github.com/moaidmoatasem/cherenkov-qa/commit/900863ab0b1b22b044893521a6eef401fc8aaa00))
* update HANDOVER.md with docs consolidation and deployment status ([09498f0](https://github.com/moaidmoatasem/cherenkov-qa/commit/09498f07642fa710e366bc485524a25a88913a31))
* update INDEX with archived FE parity audit, mark plan steps done ([#859](https://github.com/moaidmoatasem/cherenkov-qa/issues/859)) ([a7b5a16](https://github.com/moaidmoatasem/cherenkov-qa/commit/a7b5a166c0e91cff3afe8919232baa40ee2c1eb3))

## [1.3.0](https://github.com/moaidmoatasem/cherenkov-qa/compare/v1.2.0...v1.3.0) (2026-08-02)


### Features

* **cli:** add guardian start CLI entrypoint for Spec Guardian daemon ([#811](https://github.com/moaidmoatasem/cherenkov-qa/issues/811)) ([c5ca28a](https://github.com/moaidmoatasem/cherenkov-qa/commit/c5ca28a15365dcac08cdf25d44cd922bd8611da9))
* **cli:** add guardian start CLI entrypoint for Spec Guardian daemon ([#811](https://github.com/moaidmoatasem/cherenkov-qa/issues/811)) ([#823](https://github.com/moaidmoatasem/cherenkov-qa/issues/823)) ([296d4d5](https://github.com/moaidmoatasem/cherenkov-qa/commit/296d4d505f74c07a4bebbc20dd3e28a8353bf7f3))
* **cli:** give the Spec Guardian daemon a CLI entrypoint ([#811](https://github.com/moaidmoatasem/cherenkov-qa/issues/811)) ([4ac1f1e](https://github.com/moaidmoatasem/cherenkov-qa/commit/4ac1f1e1d151d20085f07de42c6a26067160f2d2))
* **cli:** wire SAML/RBAC commands to real modules ([#810](https://github.com/moaidmoatasem/cherenkov-qa/issues/810)) ([352153d](https://github.com/moaidmoatasem/cherenkov-qa/commit/352153dcd9b21b6e36d530e5a3eaf86df448dcf8))
* **cli:** wire SAML/RBAC commands to real modules ([#810](https://github.com/moaidmoatasem/cherenkov-qa/issues/810)) ([#824](https://github.com/moaidmoatasem/cherenkov-qa/issues/824)) ([f86d624](https://github.com/moaidmoatasem/cherenkov-qa/commit/f86d624b9370f6e8aeea9ddd70dc104cef5eff71))
* **mcp:** expose check-suite/verify/generate as agent-invokable tools ([#812](https://github.com/moaidmoatasem/cherenkov-qa/issues/812)) ([c2b1bf2](https://github.com/moaidmoatasem/cherenkov-qa/commit/c2b1bf2730392c4f8b385a442ca33ad264a532f2))
* **mcp:** expose check-suite/verify/generate as agent-invokable tools ([#812](https://github.com/moaidmoatasem/cherenkov-qa/issues/812)) ([#821](https://github.com/moaidmoatasem/cherenkov-qa/issues/821)) ([39d592d](https://github.com/moaidmoatasem/cherenkov-qa/commit/39d592d3e28b6dd76a78f9e156227c6c0850d4ae))
* **mcp:** registry manifest + publish instructions, ready for submission ([#792](https://github.com/moaidmoatasem/cherenkov-qa/issues/792)) ([69b8540](https://github.com/moaidmoatasem/cherenkov-qa/commit/69b854025cb828284ef3298fec044386f0c23d5f))
* **ui:** Complete 5-Workspace UI/UX Revamp, FastAPI Backend Wiring, and Playwright E2E Test Suite ([2e66658](https://github.com/moaidmoatasem/cherenkov-qa/commit/2e6665888d4a735f7a0dadb0be0e9bfdf1695de6))
* **validate:** add --tests filter to scope runs ([#829](https://github.com/moaidmoatasem/cherenkov-qa/issues/829)) ([e35e3ba](https://github.com/moaidmoatasem/cherenkov-qa/commit/e35e3bae3c316e3b527061b995ea29d20bfbea4a))


### Bug Fixes

* fix:  ([ea555e7](https://github.com/moaidmoatasem/cherenkov-qa/commit/ea555e72485fec904e62b60a43d82adf4da732cd))
* **core:** Resolve top 6 technical debt items identified in architecture review ([#832](https://github.com/moaidmoatasem/cherenkov-qa/issues/832)) ([00d277e](https://github.com/moaidmoatasem/cherenkov-qa/commit/00d277e876461f0f8dc27bd3712699c237422a2d))
* **generate:** persist one distinct file per scenario ([#828](https://github.com/moaidmoatasem/cherenkov-qa/issues/828)) ([7c77fb4](https://github.com/moaidmoatasem/cherenkov-qa/commit/7c77fb4cf574b89eec40073b3c2d7afc4427444a))
* **M1:** resolve friction bugs, tests, and ui automation ([6c7335b](https://github.com/moaidmoatasem/cherenkov-qa/commit/6c7335ba67cf162486f651d97f9c9c531c79f71a))
* **sdd:** repair agent_sync MemSearch workspace_dir API mismatch ([c7b2008](https://github.com/moaidmoatasem/cherenkov-qa/commit/c7b20080ad000320253692c77241ee5ed645ed38))
* **validate:** accept OpenAPI 3.0.x patch versions ([#829](https://github.com/moaidmoatasem/cherenkov-qa/issues/829)) ([fc48936](https://github.com/moaidmoatasem/cherenkov-qa/commit/fc48936e914aa35e897f07cfab59252140790f6c))


### Documentation

* add comprehensive architecture review report ([349d438](https://github.com/moaidmoatasem/cherenkov-qa/commit/349d43857e9b30e4b2112fa377c693c8f5b9fd07))
* **cli:** document audit + record commands, update MCP config examples ([#814](https://github.com/moaidmoatasem/cherenkov-qa/issues/814)) ([ac6b977](https://github.com/moaidmoatasem/cherenkov-qa/commit/ac6b9777c9262ea1f8c363279ff46f3f16cb4ac7))
* **getting-started:** document the `guardian` CLI command ([7a8a9a2](https://github.com/moaidmoatasem/cherenkov-qa/commit/7a8a9a26aabff47d8ddab918e213c14c29381c76))
* **handover:** note [#811](https://github.com/moaidmoatasem/cherenkov-qa/issues/811) PR status ([02ef89b](https://github.com/moaidmoatasem/cherenkov-qa/commit/02ef89b02add2e4ad0242aae80d465332e084f4c))
* lead verification pass — main certified, PAT expiry blocker recorded ([2483feb](https://github.com/moaidmoatasem/cherenkov-qa/commit/2483feb5ce724e9750a61f6620867079b29f1ceb))
* **onboarding:** add prerequisites + tool install steps, fix cold-run blocker ([#826](https://github.com/moaidmoatasem/cherenkov-qa/issues/826), [#827](https://github.com/moaidmoatasem/cherenkov-qa/issues/827)) ([4fab3c1](https://github.com/moaidmoatasem/cherenkov-qa/commit/4fab3c11e8f07a5118db40779d78483b7128be39))
* **onboarding:** align init visual with real cold-run output ([#826](https://github.com/moaidmoatasem/cherenkov-qa/issues/826)) ([8b13145](https://github.com/moaidmoatasem/cherenkov-qa/commit/8b131454bf4f2a348e3ce8694db7836e4ad5b83e))
* **onboarding:** fix Act 4 transcript and scoping guidance ([#829](https://github.com/moaidmoatasem/cherenkov-qa/issues/829)) ([8c9c215](https://github.com/moaidmoatasem/cherenkov-qa/commit/8c9c215f4151e6d2e858d6772ef83dbc1c36d86e))
* **onboarding:** fix stale refs in FAQ + init transcript ([#830](https://github.com/moaidmoatasem/cherenkov-qa/issues/830), [#831](https://github.com/moaidmoatasem/cherenkov-qa/issues/831)) ([e3b77a7](https://github.com/moaidmoatasem/cherenkov-qa/commit/e3b77a7c90a8c70640449abb79388ace138023aa))
* reconcile phase 13/14 status with wired CLI ([#810](https://github.com/moaidmoatasem/cherenkov-qa/issues/810) [#811](https://github.com/moaidmoatasem/cherenkov-qa/issues/811) [#824](https://github.com/moaidmoatasem/cherenkov-qa/issues/824) [#823](https://github.com/moaidmoatasem/cherenkov-qa/issues/823)) ([307e9c4](https://github.com/moaidmoatasem/cherenkov-qa/commit/307e9c4b9a8a8e6a293db7a3c797ba04553b33f9))
* reconcile release docs with v1.2.0 ([9f62a9a](https://github.com/moaidmoatasem/cherenkov-qa/commit/9f62a9a161960c0fdf215d76b28c89182379a11c))
* **refactor:** map dual AI routing layers, propose consolidation ([#815](https://github.com/moaidmoatasem/cherenkov-qa/issues/815)) ([b23581f](https://github.com/moaidmoatasem/cherenkov-qa/commit/b23581fca06475e218d0b9759c786733e55871e7))
* **refactor:** map dual AI routing layers, propose consolidation ([#815](https://github.com/moaidmoatasem/cherenkov-qa/issues/815)) ([#820](https://github.com/moaidmoatasem/cherenkov-qa/issues/820)) ([11a6c52](https://github.com/moaidmoatasem/cherenkov-qa/commit/11a6c524219fe4b3242fc10bcdaf89525a09c30f))
* round-2 swarm result — friction fixes merged, M1 prep unblocked ([da97789](https://github.com/moaidmoatasem/cherenkov-qa/commit/da9778989560f786afb9d9828e460920e67bc6fa))
* round-3 swarm result — wiki env-var refs fixed, tree hygiene, fresh verification ([d9a161f](https://github.com/moaidmoatasem/cherenkov-qa/commit/d9a161fad6c70faaffbc2891108d6874ec63dfba))
* T-track swarm result — [#810](https://github.com/moaidmoatasem/cherenkov-qa/issues/810)-[#816](https://github.com/moaidmoatasem/cherenkov-qa/issues/816) done, friction logs filed ([#826](https://github.com/moaidmoatasem/cherenkov-qa/issues/826)-831), [#819](https://github.com/moaidmoatasem/cherenkov-qa/issues/819) tracked ([fe6f37b](https://github.com/moaidmoatasem/cherenkov-qa/commit/fe6f37b6164cca08a9c73f17464370b73a53bfbc))
* **wiki:** replace stale env vars with real settings names ([156dba0](https://github.com/moaidmoatasem/cherenkov-qa/commit/156dba073d1823d28bf2edecaed0772eb685dd5d))

## [1.2.0] - 2026-08-01

### Added
- **GraphQL/gRPC/AsyncAPI ingest + generation** (Phase 12): schema/proto ingest, test generation, conformance validation, and Buf schema registry integration are real and wired into the CLI.
- **VS Code extension** (Phase 11): inline conformance indicators, healing suggestions, drift-on-save, test explorer, and quick-fix are all wired into the extension.
- **Enterprise audit log** and **LangChain tool package**: real, wired implementations.
- **Desktop auto-setup wizard**: real Tauri state machine.
- **Market Launch Documentation**: Added `docs/landing_page_copy.md` and `docs/demo_script.md`.
- **UX Redesign**: 5-hub information architecture, Kanban triage, live-wired Spec vs. Reality / Coverage & Certification / Test Management screens, real chat session history.

### Corrected
- **The previous entry in this changelog claimed Phase 11-16 was "fully implemented," including Enterprise tier, Spec Guardian, and the Phase 16 marketplace/webhook/analytics ecosystem. That claim was false.** A code-level audit (2026-08-01) against the corresponding GitHub issues found: Enterprise SAML/RBAC/GDPR (Phase 13) have real logic modules but are not wired into any route or CLI command (several are literal `"""Placeholder"""` stubs); the Spec Guardian daemon (Phase 14) exists but has zero callers anywhere in the codebase; the fine-tuning pipeline (Phase 15) is an explicit simulation (`"SIMULATION: would train..."`, a fake `"SIMULATED_LORA_WEIGHTS"` marker file); and the Phase 16 platform/marketplace layer is almost entirely absent or stub data. See the tracking issues on GitHub for the current, per-item status.

### Fixed
- **Repository Alignment**: Resolved merge conflicts in `HANDOVER.md` and fully synchronized `feat/qa-headless-locator-alignment` with `origin/main`.
- **Ruff Compliance**: Resolved 383 linting issues (primarily `E402` and `F401`) across `tests/` and `cherenkov/`.
- **Release/tag reconciliation**: `.release-please-manifest.json` and `package.json` had drifted to `1.0.0`; the `v1.1.1` release was tagged `v.1.1.1` (stray dot), breaking the docs-deploy version-extraction step.

## [1.1.2] - 2026-07-31

### Added
- **Unprobed-endpoint reporting** — `unprobed_endpoints()` (`cherenkov/divergence/probe_planner.py`) lists every operation probe planning produced nothing for, with the real reason, and `cherenkov verify` prints them before running. A zero-probe endpoint contributes no divergences, so a clean exit code previously implied coverage that never happened. Applied to `petstore.json` this reports **7 of 19 operations unprobed** — coverage was 12/19, not 19/19. Most causes are deliberate limits and are labelled as such: happy-path probes are GET-only (sampled data would mutate state), skipped on templated paths (a sampled identifier need not exist, and its 404 would read as a divergence), and skipped when query parameters are required. Truncation by `--max-probes` is reported rather than silent. Advisory, not fatal.
- **`RecordingProxy`** (`cherenkov/verdict/traffic_capture.py`) — a forwarding HTTP proxy that records what a test suite actually receives from a live target. Where `CapturingWitnessAgent` records CHERENKOV's own probe traffic, this records someone else's suite: point their `API_URL` at the proxy and every request is forwarded while the response is captured. `recorded_base()` feeds straight into `synthesize_mutant_battery(base=...)`, completing a **record-then-perturb** audit that needs no known-honest baseline suite — only a live target, which `verify` already requires. Demonstrated end to end against a live server with no hand-supplied values: 3 of 3 cheat classes detected, 0 false alarms; hallucinated suites are caught by the green run itself, before any mutation.
- **`synthesize_mutant_battery()`** (`cherenkov/divergence/mutant_synth.py`) — emits one mutant per failure axis (status, single-value, enum, missing-field) plus a conforming control, so a test's failure is attributable to a specific weak assertion. Validated against the labelled cheat corpus in `demos/catch-the-ai-cheating/`: 3 of 3 cheat classes detected with no false alarm on the honest suite, where the existing single coarse mutant detects none. Takes an optional `base` — the response actually recorded from the target — because a spec constrains types, not instance values, and mutating a schema-sampled body makes an honest suite fail its own control.

### Fixed

- **Soundness: `verify` could report a clean run on an endpoint it never probed.** OpenAPI 3.x allows a path parameter to be declared once on the PathItem and inherited by every operation beneath it. Probe planning read only `operation.parameters`, so on the inherited form the path placeholder was never filled and the endpoint was dropped from planning entirely — yielding zero divergences and exit code 0. The same API written the two legal ways planned 1 probe and 0 probes respectively. `merge_path_item_parameters()` is now the single definition of the `(name, in)` precedence rule, applied both in `cherenkov/divergence/probe_planner.py` and at the ingestion slicing point in `cherenkov/stages/ingest.py`, so every downstream consumer — probe planning, the meaningful-assertion gate, `truth/sources/openapi.py` — receives inherited parameters. 11 regression tests.
- **Misleading gate skip message.** `synthesize_mutant_response()` returns `None` for two unrelated reasons — no documented 2xx response, or path parameters that cannot be sampled — and both were reported as "spec has no documented success response to mutate". `explain_unmutatable()` now names the real cause, and for unfillable parameters says where to declare them.
- **Hanging unit test.** `test_returns_suggested_patch_not_applied` patched the handler with `wraps=`, which mocks nothing, so the real inference router opened a live LLM connection and the test hung until the suite timed out.

### Documentation

- **`docs/ROADMAP_2026H2.md`** — consolidated forward plan (milestones M0–M5) with verifiable exit criteria, derived from `HANDOVER.md`. Supersedes the scattered roadmap documents as the forward reference; `PRODUCT_STRATEGY_ROADMAP.md` is reclassified as a hypothesis register rather than a plan.
- **`docs/evidence/e0.5e_oracle_discrimination.md`** — measured the baseline-free integrity oracle against the labelled cheat corpus. Isolated single-axis mutants plus a conforming run separate all three cheat classes with no false alarm on the honest suite; the coarse status-plus-field mutation currently used by the meaningful-assertion gate separates none of them. Building the mutation battery is tracked as roadmap item E0.5f.
- `HANDOVER.md` status anchor refreshed — the stale "788+ tests" figure corrected to a measured 1753, and the "mypy runs clean" claim corrected to record the gate as failing.

### Known issues

- **Mypy gate is failing** — 7 errors across `cherenkov/ai/openai_client.py`, `cherenkov/ai/nemoclaw_client.py` and `cherenkov/substrate/providers/localai.py`.
- **Release tags are inconsistent with the package version.** `pyproject.toml` declares `1.1.1`, while the tag list contains `v1.2.0`, `v3.1-delta` and a malformed `v.1.1.1`. Reconcile before the next publish — a release cut from this state is not reproducible.
- **The meaningful-assertion gate under-detects.** See the evidence document above; it is sound as a per-test check behind the prism-dryrun precondition, but its single coarse mutant does not catch a deliberately weakened suite.

## [1.1.1] - 2026-06-29

### Added

- **Auto-Memory + Hooks (CC-1)**: SQLite FTS5 memory repository, HookRegistry with 10 hook events, SubprocessHookExecutor with warn/abort fail modes. ADR-011, ADR-012.
- **Multi-Agent Conductor (CC-2)**: Fan-out/fan-in agent orchestration over MCP mesh.
- **MCP Ecosystem Expansion (CC-3)**: MCP marketplace, push events, JWT auth, 5 new integrations.
- **Scheduling + Routines (CC-4)**: APScheduler integration, web UI, GitHub webhook trigger.
- **Remote Control + Teleport (CC-5)**: Session snapshot, QR-code join, SSH/Docker remote runner.
- **CLI Composability (CC-6)**: `--json`/`--quiet` on all commands, pipe mode, shell completions.
- **Phase 9 — Semantic Memory**: MemSearch repository integration with SDD protocol.
- **Phase 10 — CI/CD Native**: CI/CD reorganization + Jenkins Shared Library.
- **Phase 11 — VS Code Extension**: Full extension wiring with 11 commands.
- **Phase 12 — gRPC Support**: Buf Schema Registry integration.
- **Phase 13 — Drift Reconciliation**: L2 maker/checker, CLI autonomy flag.
- **Phase 14 — Eval Pipeline**: generate→grade→compare→optimize loop.
- **Phase 15 — Synthetic Suite Generation**: STORM-inspired multi-persona suite generation.
- **Multi-Agent Verdict Engine**: Rich verdict engine with resume-inspired web UI.
- **JWT + RBAC Auth Layer**: Opt-in authentication across all backend routes.
- **Public Documentation Site**: Material for MkDocs site hosted on GitHub Pages.
- **`cherenkov demo` command**: Offline 60-second onboarding.
- **`cherenkov drift` command**: Spec-drift CLI with reconciliation.
- **`cherenkov report` command**: Divergence JSON summary + diff.
- **`cherenkov check-suite` command**: AI cheating detection in test suites.
- **Coverage gap reporting**: `--coverage-report` flag on verify/certify.

### Changed

- Architecture improvements across Phases 0-2: port dedup, orchestrator decomposition, event bus, use cases layer.
- All CLI commands support `--json` and `--quiet` flags.
- Config consolidated with structured errors and validation.

### Fixed

- 8 P0 fixes across security, code quality, stability, and governance.
- Windows WSL SQLite UNC path handling.
- Node.js detection and Ollama onboarding false negatives.
- Test staleness detection.
- Lint cleanup across 30+ files.

## [1.1.0] - 2026-06-19

### Added

- **Multi-Protocol Support**: GraphQL schema ingestion, gRPC/Protobuf via Buf CLI, AsyncAPI/WebSocket.
- **Enterprise Tier**: SAML 2.0 / SSO (Okta, Azure AD, Google Workspace), SOC2 readiness, GDPR compliance, RBAC, audit logging, org management, BYO-LLM (Azure OpenAI, AWS Bedrock).
- **VS Code Extension**: 11 commands, gutter indicators, CodeLens, diagnostics, test explorer.
- **GitHub Actions**: `cherenkov-qa/action@v1` with SARIF output.
- **GitLab CI / CircleCI**: Templates for both platforms.
- **Jira Integration**: REST v3 client with `--export-jira` CLI flag.
- **Pre-commit hook**: `.pre-commit-hooks.yaml` for drift detection.
- **Spec Guardian**: Continuous conformance monitoring daemon.
- **Training Pipeline**: Dataset collector, LoRA fine-tune trainer, evaluation harness.
- **Launch Materials**: Product Hunt kit, demo script, Discord setup guide.

### Changed

- Upgraded from v1.0.0 core to full extended roadmap (Phases 9-16).

### Fixed

- Various K8s operator deployment and RBAC fixes.
- CRD extension validation.

## [1.0.0] - 2026-06-20

### Added
- **Core Engine**: AI-native API conformance testing engine.
- **Spec-derived Validation**: OpenAPI ingest → LLM tests → Conformance Validation.
- **Suggest-only Healing**: Provides code suggestions without auto-applying to maintain invariants.
- **Eject Capability**: Strip all CHERENKOV imports to export vanilla Playwright tests (Zero lock-in).
- **Security Check**: Embedded OWASP mutation payloads (DAST lite).
- **VLM & Visual Oracle**: Support for Ollama and local model tier routing. Visual validation of the Dashboard via `qwen2.5-coder:7b`.
- **GraphRAG Second Brain**: Knowledge mesh for idioms, incidents, and verdicts.
- **Chat Agent**: Conversational agent with tool-calling capabilities and SSE streaming.
- **Dashboard UI**: Comprehensive React dashboard with 9 screens, including Device Manager, Health Widget, and Truth Map.
- **K8s Operator**: `ConformanceCheck` CRD and Go operator for Kubernetes-native CI/CD runs.
- **Quickstart CLI**: `npx cherenkov init` zero-install script.
- **Comprehensive QA Suite**: Integrated UI testing with Playwright for the Dashboard.

### Changed
- Transitioned default LLM to offline-first `qwen2.5-coder:7b` via Ollama.

### Fixed
- Stabilized and integrated K8s fixes.
- Validated CRD extensions and device env vars.
