<!--
============================================================================
Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
Proprietary rights reserved except as expressly licensed herein.

ZX-UX C48 SDK
This file is governed by the SANYALnet Labs Non-Commercial License in the
root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
for AI/ML model training are prohibited unless separately authorized.

Attribution is required: "Based on original work by Supratim Sanyal of
SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
patent, trademark, and governing-law provisions.
============================================================================
-->
# Deterministic Demo and Security-Fixture Hashes - Pre-1.0 SDK

These hashes are release invariants verified by `compiler/verify_release.py`. Each ordinary demo is rebuilt from source, executed from the rebuilt C48B1, and required to produce the exact 6912-byte Spectrum screen hash below. Security fixtures are also rebuilt byte-for-byte; their runtime mitigation behavior is asserted by `compiler/tests/test_security.py`.

`argv` is executed with arguments `alpha beta gamma`; the runtime program token during verification is the deterministic basename `<demo>.c48b`.

| Demo | Source SHA-256 | C48B1 SHA-256 | Screen SHA-256 |
|---|---|---|---|
| `hello` | `314c973f97449348fcafe02d27b8df3f91ecdd41665a2cf2d7baffcb4c5ba7e3` | `4dfbcdb0bc821a94054ef468f5ebe32e59e05e34e6e203284cce6ddceb842665` | `20e491b86cb68ca65eef144c760feaef80995242b258dc2421beda30a68a69f9` |
| `colors` | `d691336881de1f29f6b236e49bbd2b14b41843a6bf1472dd33f7dfef00f60d8c` | `5e9411e2b3f818017373ba389039c169a5d757f913df045443e15410c7eefab4` | `82687c81ba0208c728b1a4643f03b67745b947a39cd252929f4b383d9fba6d55` |
| `graphics` | `1981324b45387acd98e9be80e6800d97e8ccd9937f6af31715b370da0fc4c3e7` | `5d667ab8c3841d91cd97eb4ddd82389c98568dc23bbd979607af4fe7ce4c12ac` | `d2611838b3071ed7e658178d38a7bdd11a0d7fdf2aeffbb15bd65803a878053c` |
| `udg` | `dd15548be86d79b48ca8c5d9d0d87a1425236ccff7e548ef32952eaa031ffeff` | `e6a33f15c8b0990d0c1dab06fddaa38ffdb431dff98f8cf05243dc7e124ffc23` | `297ef51aa92911f090027668d02bc5bd92eac82c72678a708cc9a1097b13081c` |
| `maze` | `982ef55dc51dbaf3566efb5f9af98f98729138c53df8a837b7d435f0b0016ddb` | `635375320159a6c44079d5066ad91d8f8c7f3189614271661e41cabf71389562` | `ca337377f9e1073e895d6ad9240072c37577e6dd16d8c3cd43620c0bec1c2335` |
| `argv` | `b56debabcbc3fe09d8b370f863d673627c3c591db08f87a80fb2d1e8df3cbf8e` | `f9e33f5d72c69a637daf1c863f343095c36df239a3ad4c048f61b5af87f677ea` | `c5fdbdb1e1ee4eeca9df25cf07f2d8747ad9c622befaf9a176398329fa962898` |

## Security fixture binaries

These C48 programs visibly announce the attempted attack and expected mitigation on the emulated 64-column Spectrum screen before exercising the guard. `seckern.c` is intentionally compile-negative and therefore has no C48B1 binary.

| Fixture | C48B1 SHA-256 |
|---|---|
| `secguard` | `d99bf57105e54edad73fac8f7d3558744ab08f02576b03bfcc9c4b69293f8325` |
| `secoob` | `349168f84c3591e3391339b935194369f343e34fe35854a3a2d91705606fcaaa` |
| `secuaf` | `d7ea7af597698c8741da08cd72c3004aa08bae1b8f326be0b48f83202996e764` |
| `secfree` | `854c4fe9ff427b065ebb7d96037e59303b4b1403aeade0868731e65732b243ea` |
| `secdbl` | `77536aa5fa854916c372bc8f24c570abfcc4ddd52f7ba1a3a649467b09be3df4` |
| `secloop` | `08d6fbd9115510fcc2f19e70a0084ed2eb85226eaa7b49eb7599888d0750af10` |
| `secrecur` | `8c3b482b7994601ad34ee2e577333e8653763d0f8caff9797de7f431a0ad8b19` |
| `secforge` | `d0f1abbe4e8658618976b5edfabcd585f482fdac9a02603011dbaf0422e4b50c` |

Host Game API header SHA-256:

`b14d2c7d2558e3016e712107c53692680b62f50b99fc6054660e22c0af02766f`

Default Tasword F4X8 SHA-256:

`90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339`

Alternate ZX-UX F4X8 SHA-256:

`90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339`

In this revision the two supplied F4X8 assets are byte-identical; they are kept under distinct names so either slot can evolve independently while `c48run --font PATH` remains stable.
