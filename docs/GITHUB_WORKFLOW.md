# GitHub Workflow

## Initial publication

```bash
git init
git add .
git commit -m "build(010): establish desktop foundation"
git branch -M main
git remote add origin <YOUR-GITHUB-REPOSITORY-URL>
git push -u origin main
```

## Development build

```bash
git checkout main
git pull
git checkout -b build/011-3d-preview
```

After development:

```bash
git status
git diff
pytest -v
git add .
git commit -m "build(011): add interactive 3d preview"
git push -u origin build/011-3d-preview
```

Create a pull request, review tests and changes, then merge to `main`.
