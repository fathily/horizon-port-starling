# Engine port: Minecraft Java 1.21.11

## Goal and branch boundary

Port Minecraft Java Edition 1.21.11 into the **core Horizon Rust engine first**. The Android fork is a later integration target. Do not add a version picker, rename version constants, or package the current 26.3 binary as 1.21.11 and call that a port.

Work for this stage lives on `engine-1.21.11`, based on the upstream Horizon engine. Android-specific work belongs on a separate Starling/Android branch only after the engine target is functional and has passed the required tests.

## Version facts

| Property | 1.21.11 | Existing Horizon target |
| --- | ---: | ---: |
| Java runtime | 21 | 25 |
| Protocol | 774 | 777 |
| World/data version | 4671 | 5023 |
| Resource pack format | 75.0 | 97.1 |
| Data pack format | 94.1 | 121.0 |

These values must be checked against the downloaded Mojang version metadata and the game jar's own `version.json`. They are not, by themselves, evidence of engine compatibility.

## Source inputs and licensing boundary

Mojang's 1.21.11 release page provides an unobfuscated experimental client ZIP and a separate unobfuscated server jar. The analysis helper uses those published artifacts and verifies their SHA-1 digests before reading them.

All downloaded jars, extracted files, decompiled code, reports, and generated resources stay outside the Git checkout under `HORIZON_VERSIONS`. Never commit or publish Mojang game files, assets, decompiled sources, or prepared resources. The player-facing engine continues to consume resources prepared from the player's own legitimate Minecraft installation.

## Port pipeline

1. **Prepare an exact vanilla baseline.** Download and verify the official 1.21.11 development artifacts. Check the client jar's identity, protocol, world version, Java level, and pack formats. Run the matching data generator with Java 21. Index client/server classes for analysis.
2. **Compare against 26.3.** Prepare the known 26.3 baseline separately with Java 25. Produce a report for packet IDs and layouts, registry entries and IDs, block states, item components, commands, world/data JSON, assets, translations, and class changes.
3. **Make the engine version-aware.** Keep 26.3's current generated constants and behavior intact. Introduce an explicit version target/build profile rather than changing the process-wide `horizon_core::version` constants under a 26.3 binary. Separate incompatible protocol tables, registries, data-version handling, resources, and rules.
4. **Port behavior, not labels.** Regenerate only verified data-driven tables. Port code-dependent changes in protocol codecs, chunk palettes, block/item/entity behavior, world generation, commands, data fixes, model parsing/baking, and rendering. Every vanilla behavior change needs a focused parity test or fixture against 1.21.11.
5. **Validate the core target.** Run formatting, clippy, unit/integration tests, the applicable parity harnesses against the 1.21.11 oracle, world create/save/reopen, and matching-version server protocol tests. Do not call the target supported until these pass.
6. **Integrate Android after core parity.** Bring the tested engine changes and version-specific build artifacts into the Android fork. Reuse shared Android UI, controls, storage, and settings only where their behavior is version-independent. Keep version-specific resources, caches, saves, protocol and native libraries isolated.

## Acceptance criteria before Android integration

- The engine selects 1.21.11 explicitly without changing what the 26.3 executable reports or loads.
- 1.21.11's packets, registries, blocks, items, entities, commands, resource formats, data fixes, and world generation match the official target where implemented.
- A new world can be generated, saved, closed, reopened, and played without mixing 26.3 data.
- The 1.21.11 client can complete login/configuration/play with a matching 1.21.11 server.
- Existing 26.3 build and tests remain green.
- CI reports separate outcomes for the 1.21.11 engine target and the existing 26.3 target.

## Current status

This branch is the clean engine baseline plus the preparation/analysis tooling. It is **not yet a working 1.21.11 engine port**. The actual gameplay and compatibility work starts from the generated comparison report; Android packaging must wait until the core acceptance criteria pass.
