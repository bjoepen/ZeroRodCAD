# Apply Build 020 M1 Core Extraction RC

1. Start from an unmodified ZeroRodCAD Build 019.3 M4 checkout.
2. Back up or commit local work.
3. Copy the contents of `PATCH/` into the repository root, preserving paths and replacing files.
4. Copy `docs/` and `scripts/` into the matching repository directories.
5. Replace the repository `CHANGELOG.md` with the supplied file.
6. Verify the payload with `shasum -a 256 -c SHA256SUMS.txt` from this package directory.
7. From the repository root, run `scripts/validate-build020-m1.sh`.

The patch neither deletes bundle content nor changes command-line options. Do not mark the build
Final until user validation succeeds.
