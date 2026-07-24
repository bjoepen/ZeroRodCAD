from pathlib import Path


def test_packaging_requirements_exist():
    assert Path("packaging/macos/requirements-build.txt").is_file()
    assert Path("packaging/macos/requirements-audit.txt").is_file()


def test_audit_scripts_exist():
    required = (
        "scripts/audit_dependencies.sh",
        "scripts/runtime_import_probe.py",
        "scripts/report_suspect_dependencies.sh",
        "scripts/analyze_pyinstaller_build.sh",
    )
    for filename in required:
        assert Path(filename).is_file()


def test_spec_excludes_known_unrelated_heavy_modules():
    content = Path("packaging/macos/ZeroRodCAD.spec").read_text(encoding="utf-8")
    assert '"casadi"' in content
    assert '"llvmlite"' in content
    assert '"numba"' in content
