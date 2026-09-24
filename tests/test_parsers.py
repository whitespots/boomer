import json
import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner

from boomer import cli
from parsers.java_parser import JavaParser
from parsers.python_parser import PythonParser
from parsers.ruby_parcer import RubyParser


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class ScannerFixtureTests(unittest.TestCase):
    def scan_fixture(self, fixture_name, *extra_args):
        fixture_path = FIXTURES_DIR / fixture_name
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "bom.json"
            result = CliRunner().invoke(
                cli,
                ["scan", str(fixture_path), "--output", str(report_path), *extra_args],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            with report_path.open(encoding="utf-8") as report_file:
                return json.load(report_file)

    def components_by_name(self, report):
        return {component["name"]: component for component in report["components"][1:]}

    def assert_source_file(self, component, name, value):
        self.assertIn({"name": name, "value": value}, component["properties"])

    def dependency_map(self, report):
        return {
            dependency["ref"]: dependency["dependsOn"]
            for dependency in report["dependencies"]
        }

    def test_python_fixture_generates_requirements_source_property(self):
        components = self.components_by_name(self.scan_fixture("python"))

        self.assertEqual(
            set(components),
            {"requests", "flask", "celery", "my-package-name"},
        )
        self.assert_source_file(
            components["requests"],
            "cdx:pypi:source:file",
            "requirements.txt",
        )
        self.assertEqual(components["requests"]["purl"], "pkg:pypi/requests@==2.32.3")
        self.assertEqual(components["requests"]["bom-ref"], components["requests"]["purl"])
        self.assert_source_file(
            components["flask"],
            "cdx:pypi:source:file",
            "requirements.txt",
        )
        self.assertEqual(
            components["celery"]["purl"],
            "pkg:pypi/celery@==5.5.1",
        )
        self.assert_source_file(
            components["celery"],
            "cdx:pypi:package:extras",
            "amqp,redis",
        )
        self.assertEqual(
            components["my-package-name"]["purl"],
            "pkg:pypi/my-package-name@==1.2.3",
        )

    def test_prefer_locks_uses_package_lock_and_generates_dependency_graph(self):
        report = self.scan_fixture("javascript", "--prefer-locks")
        components = self.components_by_name(report)

        self.assertEqual(set(components), {"lodash", "is-number"})
        self.assert_source_file(
            components["lodash"],
            "cdx:npm:source:file",
            "package-lock.json",
        )
        self.assertEqual(components["lodash"]["purl"], "pkg:npm/lodash@4.17.21")
        self.assertEqual(components["lodash"]["bom-ref"], components["lodash"]["purl"])
        self.assertEqual(
            components["lodash"]["licenses"],
            [{"license": {"name": "MIT"}}],
        )
        self.assert_source_file(
            components["lodash"],
            "cdx:npm:package:resolved",
            "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
        )
        self.assertEqual(
            self.dependency_map(report),
            {
                "project": ["pkg:npm/lodash@4.17.21"],
                "pkg:npm/lodash@4.17.21": ["pkg:npm/is-number@7.0.0"],
            },
        )

    def test_javascript_direct_mode_skips_package_lock(self):
        components = self.components_by_name(
            self.scan_fixture("javascript", "--direct", "true")
        )

        self.assertEqual(set(components), {"left-pad"})

    def test_javascript_falls_back_to_package_lock_without_package_json(self):
        components = self.components_by_name(
            self.scan_fixture("javascript-lock-only")
        )

        self.assertEqual(set(components), {"lock-only"})
        self.assert_source_file(
            components["lock-only"],
            "cdx:npm:source:file",
            "package-lock.json",
        )

    def test_prefer_locks_uses_yarn_lock_and_generates_dependency_graph(self):
        report = self.scan_fixture("javascript-yarn", "--prefer-locks")
        components = self.components_by_name(report)

        self.assertEqual(set(components), {"chalk", "supports-color"})
        self.assert_source_file(
            components["chalk"],
            "cdx:npm:source:file",
            "yarn.lock",
        )
        self.assert_source_file(
            components["chalk"],
            "cdx:npm:package:resolved",
            "https://registry.yarnpkg.com/chalk/-/chalk-4.1.2.tgz#d792",
        )
        self.assertEqual(
            self.dependency_map(report),
            {
                "pkg:npm/chalk@4.1.2": ["pkg:npm/supports-color@7.2.0"],
            },
        )

    def test_go_fixture_generates_go_mod_source_property(self):
        components = self.components_by_name(self.scan_fixture("go"))

        self.assertEqual(
            set(components),
            {
                "github.com/google/uuid",
                "github.com/stretchr/testify",
                "golang.org/x/net",
            },
        )
        for component in components.values():
            self.assert_source_file(
                component,
                "cdx:golang:source:file",
                "go.mod",
            )
        self.assertEqual(
            components["github.com/google/uuid"]["purl"],
            "pkg:golang/github.com/google/uuid@v1.6.0",
        )
        self.assertEqual(
            components["github.com/google/uuid"]["bom-ref"],
            components["github.com/google/uuid"]["purl"],
        )

    def test_go_direct_mode_excludes_indirect_dependencies(self):
        components = self.components_by_name(self.scan_fixture("go", "--direct", "true"))

        self.assertEqual(
            set(components),
            {"github.com/google/uuid", "github.com/stretchr/testify"},
        )

    def test_python_manifest_formats(self):
        components = self.components_by_name(self.scan_fixture("python-manifests"))

        self.assertEqual(
            set(components),
            {"requests", "poetry-lib", "pep621-lib", "setup-lib", "pipfile-lib", "locked-lib"},
        )

    def test_python_pyproject_manifest(self):
        dependencies = PythonParser(FIXTURES_DIR / "python-manifests").parse_dependencies(
            FIXTURES_DIR / "python-manifests" / "pyproject.toml"
        )

        self.assertIn(("Python", "poetry-lib", "^1.0.0"), dependencies)
        self.assertIn(("Python", "pep621-lib", "2.0.0"), dependencies)

    def test_python_poetry_uses_manifest_by_default(self):
        components = self.components_by_name(self.scan_fixture("python-poetry"))

        self.assertEqual(set(components), {"requests"})
        self.assertEqual(components["requests"]["version"], "^2.32.0")
        self.assert_source_file(
            components["requests"],
            "cdx:pypi:source:file",
            "pyproject.toml",
        )

    def test_python_poetry_prefer_locks_uses_exact_versions_and_graph(self):
        report = self.scan_fixture("python-poetry", "--prefer-locks")
        components = self.components_by_name(report)

        self.assertEqual(set(components), {"requests", "certifi", "pytest"})
        self.assertEqual(components["requests"]["version"], "2.32.3")
        self.assert_source_file(
            components["requests"],
            "cdx:pypi:source:file",
            "poetry.lock",
        )
        self.assertEqual(
            self.dependency_map(report),
            {
                "project": ["pkg:pypi/requests@2.32.3"],
                "pkg:pypi/requests@2.32.3": ["pkg:pypi/certifi@2024.2.2"],
            },
        )

    def test_python_poetry_direct_mode_excludes_transitive_and_dev_packages(self):
        components = self.components_by_name(
            self.scan_fixture("python-poetry", "--prefer-locks", "--direct", "true")
        )

        self.assertEqual(set(components), {"requests"})

    def test_python_poetry_falls_back_to_lock_without_pyproject(self):
        components = self.components_by_name(
            self.scan_fixture("python-poetry-lock-only")
        )

        self.assertEqual(set(components), {"lock-only-python-package"})
        self.assertEqual(components["lock-only-python-package"]["version"], "1.2.3")

    def test_java_maven_and_gradle_manifests(self):
        components = self.components_by_name(self.scan_fixture("java"))

        self.assertEqual(
            set(components),
            {"org.example:maven-lib", "org.example:gradle-lib"},
        )
        self.assertEqual(
            components["org.example:maven-lib"]["purl"],
            "pkg:maven/org.example:maven-lib@1.0.0",
        )

    def test_maven_uses_pom_by_default(self):
        components = self.components_by_name(self.scan_fixture("java-maven-lock"))

        self.assertEqual(set(components), {"org.example:direct-lib"})
        self.assertEqual(components["org.example:direct-lib"]["version"], "1.0.0")

    def test_maven_prefer_locks_uses_resolved_versions_and_graph(self):
        report = self.scan_fixture("java-maven-lock", "--prefer-locks")
        components = self.components_by_name(report)

        self.assertEqual(
            set(components),
            {"org.example:direct-lib", "org.example:transitive-lib"},
        )
        self.assertEqual(components["org.example:direct-lib"]["version"], "1.2.0")
        self.assertEqual(
            self.dependency_map(report),
            {
                "project": ["pkg:maven/org.example:direct-lib@1.2.0"],
                "pkg:maven/org.example:direct-lib@1.2.0": [
                    "pkg:maven/org.example:transitive-lib@2.1.0"
                ],
            },
        )

    def test_maven_lock_direct_mode_excludes_transitive_dependencies(self):
        components = self.components_by_name(
            self.scan_fixture(
                "java-maven-lock",
                "--prefer-locks",
                "--direct",
                "true",
            )
        )

        self.assertEqual(set(components), {"org.example:direct-lib"})

    def test_maven_falls_back_to_lock_without_pom(self):
        components = self.components_by_name(
            self.scan_fixture("java-maven-lock-only")
        )

        self.assertEqual(set(components), {"org.example:lock-only-lib"})

    def test_maven_prefer_locks_falls_back_to_pom_without_lock(self):
        components = self.components_by_name(
            self.scan_fixture("java", "--prefer-locks")
        )

        self.assertIn("org.example:maven-lib", components)

    @unittest.expectedFailure
    def test_java_gradle_kotlin_manifest(self):
        dependencies = JavaParser(FIXTURES_DIR / "java").parse_dependencies(
            FIXTURES_DIR / "java" / "build.gradle.kts"
        )

        self.assertIn(("Java", "org.example:kotlin-lib", "1.0.0"), dependencies)

    def test_cpp_cmake_conan_and_vcpkg_manifests(self):
        components = self.components_by_name(self.scan_fixture("cpp"))

        self.assertEqual(
            set(components),
            {"Boost", "external-lib", "fmt", "catch2", "zlib", "openssl"},
        )
        self.assertEqual(components["Boost"]["purl"], "pkg:generic/Boost@1.84")
        self.assertEqual(components["fmt"]["purl"], "pkg:conan/fmt@10.2.1")

    def test_csharp_nuget_manifests(self):
        components = self.components_by_name(self.scan_fixture("csharp"))

        self.assertEqual(
            set(components),
            {"Newtonsoft.Json", "Serilog", "NUnit", "Microsoft.CSharp"},
        )
        self.assertEqual(
            components["Newtonsoft.Json"]["purl"],
            "pkg:nuget/Newtonsoft.Json@13.0.3",
        )

    def test_go_mod_and_dep_manifests(self):
        components = self.components_by_name(self.scan_fixture("go-manifests"))

        self.assertEqual(
            set(components),
            {"example.com/direct", "github.com/dep/constraint", "github.com/dep/locked"},
        )

    def test_rust_cargo_manifests(self):
        components = self.components_by_name(self.scan_fixture("rust"))

        self.assertEqual(set(components), {"serde", "anyhow"})
        self.assertEqual(components["serde"]["purl"], "pkg:cargo/serde@1.0.197")

    def test_php_composer_manifests(self):
        components = self.components_by_name(self.scan_fixture("php"))

        self.assertEqual(set(components), {"monolog/monolog", "phpunit/phpunit"})

    def test_php_prefer_locks_uses_composer_lock_and_generates_dependency_graph(self):
        report = self.scan_fixture("php", "--prefer-locks")
        components = self.components_by_name(report)

        self.assertEqual(
            set(components),
            {"monolog/monolog", "psr/log", "phpunit/phpunit"},
        )
        self.assertEqual(
            self.dependency_map(report),
            {
                "pkg:composer/monolog/monolog@3.6.0": ["pkg:composer/psr/log@3.0.0"],
            },
        )

    def test_php_falls_back_to_composer_lock_without_composer_json(self):
        components = self.components_by_name(self.scan_fixture("php-lock-only"))

        self.assertEqual(set(components), {"lock-only/package"})

    def test_ruby_gemfile_manifest(self):
        components = self.components_by_name(self.scan_fixture("ruby"))

        self.assertEqual(set(components), {"rails"})
        self.assertTrue(components["rails"]["purl"].startswith("pkg:gem/rails@"))

    @unittest.expectedFailure
    def test_ruby_gemfile_lock_manifest(self):
        dependencies = RubyParser(FIXTURES_DIR / "ruby").parse_dependencies(
            FIXTURES_DIR / "ruby" / "Gemfile.lock"
        )

        self.assertIn(("Ruby", "rack", "2.2.8"), dependencies)


if __name__ == "__main__":
    unittest.main()
