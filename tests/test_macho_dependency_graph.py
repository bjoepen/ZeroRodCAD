from tools.bundle_analyzer.macho import MachOBinary, build_dependency_graph


def test_dependency_graph_resolves_rpath_and_reachability() -> None:
    binaries = (
        MachOBinary(
            relative_path="Contents/MacOS/ZeroRodCAD",
            macho_id=None,
            raw_dependencies=("@rpath/QtCore.framework/Versions/A/QtCore",),
        ),
        MachOBinary(
            relative_path="Contents/Frameworks/QtCore.framework/Versions/A/QtCore",
            macho_id="@rpath/QtCore.framework/Versions/A/QtCore",
            raw_dependencies=("/usr/lib/libSystem.B.dylib",),
        ),
    )

    graph = build_dependency_graph(binaries)

    assert graph.edges["Contents/MacOS/ZeroRodCAD"] == (
        "Contents/Frameworks/QtCore.framework/Versions/A/QtCore",
    )
    assert graph.reachable_from(["Contents/MacOS/ZeroRodCAD"]) == frozenset(
        {
            "Contents/MacOS/ZeroRodCAD",
            "Contents/Frameworks/QtCore.framework/Versions/A/QtCore",
        }
    )
    assert graph.external_dependencies[
        "Contents/Frameworks/QtCore.framework/Versions/A/QtCore"
    ] == ("/usr/lib/libSystem.B.dylib",)
