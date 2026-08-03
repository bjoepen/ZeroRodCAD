# Runtime trace safety

The controller treats the `.app` as read-only. It changes no files, signature, plist, quarantine
attribute or packaging content and never writes reports inside it. Tests compare bundle manifests
before and after collection.

The output is mandatory, path traversal is rejected and a resolved destination inside the bundle
is rejected. Writing is atomic through a sibling temporary file. Hook raw data, isolated `HOME`
and preview/export artifacts live in an external temporary directory. They are removed unless
`--keep-raw` explicitly requests an external diagnostic copy.

Paths within the app become bundle-relative. Apple system locations receive stable `<system>`
identities. Home, temporary and other absolute external paths receive labelled SHA-256-derived
identities; raw paths are not silently discarded. Uncertain mappings remain `unresolved`.

The child gets trace variables in its private environment and starts in a new process group. At a
timeout the controller sends SIGTERM, waits a grace period, then uses SIGKILL if necessary. A hard
kill or crash may skip `atexit`, so a missing end record is explicitly incomplete.
