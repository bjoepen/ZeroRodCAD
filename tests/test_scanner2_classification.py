from tools.bundle_analyzer.scanner2.classification import classify_section
from tools.bundle_analyzer.scanner2.models import BundleSection


def test_specialized_sections_precede_generic_bundle_areas() -> None:
    assert (
        classify_section(
            "Contents/Frameworks/vtkmodules/libvtk.dylib",
            is_macho=True,
        )
        is BundleSection.VTK
    )
    assert (
        classify_section(
            "Contents/Resources/OCP/data.bin",
            is_macho=False,
        )
        is BundleSection.OCP
    )


def test_generic_sections_are_detected() -> None:
    assert (
        classify_section(
            "Contents/Frameworks/libx.dylib",
            is_macho=True,
        )
        is BundleSection.FRAMEWORKS
    )
    assert (
        classify_section(
            "Contents/Resources/readme.txt",
            is_macho=False,
        )
        is BundleSection.RESOURCES
    )
