<!-- Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs. -->
<!-- Proprietary rights reserved except as expressly licensed herein. -->
<!-- -->
<!-- ZX-UX Sinclair ZX Spectrum Unix -->
<!-- This file is governed by the SANYALnet Labs Non-Commercial License in the -->
<!-- root LICENSE file. Non-Commercial use is permitted; Commercial Use and use -->
<!-- for AI/ML model training are prohibited unless separately authorized. -->
<!-- -->
<!-- Attribution is required: "Based on original work by Supratim Sanyal of -->
<!-- SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination, -->
<!-- patent, trademark, and governing-law provisions. -->

# ZX-UX Version-1 Namespace

The Version-1 fixed namespace is:

- `/`
- `/bin`
- `/dev`
- `/etc`
- `/home`
- `/home/<user>`
- `/tmp`

Directory IDs are `ROOT = 0`, `BIN = 1`, `DEV = 2`, `ETC = 3`, `HOME = 4`,
`USERHOME = 5`, `TMP = 6`; persistence additionally reserves `DIR_SYSTEM = 7`.
SYSTEM is not a user-created directory.

Paths may be absolute or relative. `.` and `..` are navigation components,
repeated separators collapse, and the normalized absolute result is limited to
31 bytes excluding its NUL terminator. Traversal above root and an empty final
object name are invalid. Unknown fixed directory components do not create
directories.

There is no Version-1 mkdir/rmdir, mount layer, permission/ownership-bit model,
or inode API. After login, `/home` contains exactly the current session home
mapping and no general child directories.
