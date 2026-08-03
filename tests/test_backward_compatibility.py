from tools.bundle_analyzer.deadlibs import DeadLibraryAnalyzer as LegacyDeadLibraryAnalyzer
from tools.bundle_analyzer.macho import DependencyGraph as LegacyDependencyGraph
from tools.bundle_analyzer.scanner2 import Scanner as LegacyScanner

from zerorod_analysis.deadlibs import DeadLibraryAnalyzer
from zerorod_analysis.macho import DependencyGraph
from zerorod_analysis.scanner import Scanner


def test_legacy_imports_delegate_to_analysis_package() -> None:
    assert LegacyDeadLibraryAnalyzer is DeadLibraryAnalyzer
    assert LegacyDependencyGraph is DependencyGraph
    assert LegacyScanner is Scanner


def test_legacy_nested_module_imports_delegate() -> None:
    from tools.bundle_analyzer.deadlibs.models import Recommendation as LegacyRecommendation
    from tools.bundle_analyzer.scanner2.models import BundleSection as LegacyBundleSection

    from zerorod_analysis.deadlibs.models import Recommendation
    from zerorod_analysis.scanner.models import BundleSection

    assert LegacyRecommendation is Recommendation
    assert LegacyBundleSection is BundleSection
