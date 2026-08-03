# Git commit instructions

After applying the drop-in and completing the release gate:

```sh
git status --short
git diff --check
git add CHANGELOG.md docs scripts src tests tools
git commit -m "refactor: extract bundle analyzer core"
```

Review the staged diff before committing. Do not stage caches, generated reports, local bundles,
or the drop-in package itself.
