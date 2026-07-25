from pathlib import Path

from tools.bundle_analyzer.deadlibs import (
    ConfidenceLevel,
    DeadLibraryAnalyzer,
    FindingCategory,
    Recommendation,
    aggregate_library_units,
    compute_savings,
)
from tools.bundle_analyzer.macho import DependencyGraph
from tools.bundle_analyzer.scanner2 import (
    BundleDatabase,
    BundleFile,
    BundleSection,
)


def bundle_file(
    root: Path,
    relative_path: str,
    *,
    size: int,
    is_macho: bool = False,
    symlink: bool = False,
) -> BundleFile:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    if not symlink:
        path.write_text("", encoding="utf-8")
    return BundleFile(
        path=path,
        relative_path=relative_path,
        filename=path.name,
        extension=path.suffix,
        size_bytes=size,
        sha256=relative_path,
        modified_ns=1,
        inode=1,
        device=1,
        is_symlink=symlink,
        symlink_target=None,
        section=BundleSection.FRAMEWORKS,
        is_macho=is_macho,
        architecture=("arm64",) if is_macho else (),
    )


def test_framework_files_are_aggregated_without_double_counting_symlinks(
    tmp_path: Path,
) -> None:
    files = (
        bundle_file(
            tmp_path,
            "Contents/Frameworks/QtCore.framework/Versions/A/QtCore",
            size=100,
            is_macho=True,
        ),
        bundle_file(
            tmp_path,
            "Contents/Frameworks/QtCore.framework/Resources/Info.plist",
            size=20,
        ),
        bundle_file(
            tmp_path,
            "Contents/Frameworks/QtCore.framework/QtCore",
            size=100,
            symlink=True,
        ),
    )
    database = BundleDatabase(tmp_path, files, directory_count=4)

    units = aggregate_library_units(database)

    assert len(units) == 1
    assert units[0].identifier == "Contents/Frameworks/QtCore.framework"
    assert units[0].category is FindingCategory.FRAMEWORK
    assert units[0].size_bytes == 120
    assert len(units[0].paths) == 3


def test_analyzer_keeps_referenced_framework_and_marks_unused_dylib(tmp_path: Path) -> None:
    executable = bundle_file(
        tmp_path,
        "Contents/MacOS/ZeroRodCAD",
        size=50,
        is_macho=True,
    )
    framework = bundle_file(
        tmp_path,
        "Contents/Frameworks/QtCore.framework/Versions/A/QtCore",
        size=100,
        is_macho=True,
    )
    dylib = bundle_file(
        tmp_path,
        "Contents/Frameworks/libUnused.dylib",
        size=25,
        is_macho=True,
    )
    database = BundleDatabase(tmp_path, (executable, framework, dylib), directory_count=3)
    graph = DependencyGraph(
        edges={
            executable.relative_path: (framework.relative_path,),
            framework.relative_path: (),
            dylib.relative_path: (),
        },
        external_dependencies={
            executable.relative_path: (),
            framework.relative_path: (),
            dylib.relative_path: (),
        },
        reverse_edges={
            executable.relative_path: (),
            framework.relative_path: (executable.relative_path,),
            dylib.relative_path: (),
        },
    )

    result = DeadLibraryAnalyzer().analyze(database, graph)
    by_id = {finding.library.identifier: finding for finding in result.findings}

    qt = by_id["Contents/Frameworks/QtCore.framework"]
    unused = by_id["Contents/Frameworks/libUnused.dylib"]
    assert qt.recommendation is Recommendation.KEEP
    assert qt.confidence is ConfidenceLevel.HIGH
    assert unused.recommendation is Recommendation.SAFE_REMOVE
    assert unused.confidence is ConfidenceLevel.HIGH
    assert result.potential_savings_bytes == 25


def test_compute_savings_is_sorted_descending(tmp_path: Path) -> None:
    files = (
        bundle_file(tmp_path, "Contents/Frameworks/libA.dylib", size=10),
        bundle_file(tmp_path, "Contents/Frameworks/libB.dylib", size=30),
    )
    database = BundleDatabase(tmp_path, files, directory_count=1)
    graph = DependencyGraph(
        edges={item.relative_path: () for item in files},
        external_dependencies={item.relative_path: () for item in files},
        reverse_edges={item.relative_path: () for item in files},
    )

    result = DeadLibraryAnalyzer().analyze(database, graph)
    analysis = compute_savings(result.findings)

    assert analysis.entries == (
        ("Contents/Frameworks/libB.dylib", 30),
        ("Contents/Frameworks/libA.dylib", 10),
    )
    assert analysis.total_bytes == 40
