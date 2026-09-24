import os
import re
from typing import List, Tuple
from helpers.log import logs
from .base_parser import Parser
from consts.dependency_files import DEPENDENCY_FILES


class PythonParser(Parser):

    def __init__(self, repo_path: str, only_direct=False, prefer_locks=False):
        super().__init__(repo_path, only_direct, prefer_locks)
        self._dependency_relations = []

    def find_dependency_files(self) -> List[str]:
        dependency_files = []
        python_dep_files = DEPENDENCY_FILES['Python']

        for root, _, files in os.walk(self.repo_path):
            files = set(files)
            for file in files:
                if file not in python_dep_files:
                    continue
                if file == 'pyproject.toml' and self.prefer_locks and 'poetry.lock' in files:
                    continue
                if file == 'poetry.lock' and not self.prefer_locks and 'pyproject.toml' in files:
                    continue
                if file in python_dep_files:
                    dependency_files.append(os.path.join(root, file))

        return dependency_files

    def parse_dependencies(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []
        filename = os.path.basename(file_path)

        if filename == "requirements.txt":
            dependencies = self._parse_requirements_txt(file_path)
        elif filename == "pyproject.toml":
            dependencies = self._parse_pyproject_toml(file_path)
        elif filename == "poetry.lock":
            dependencies = self._parse_poetry_lock(file_path)
        elif filename == "setup.py":
            dependencies = self._parse_setup_py(file_path)
        elif filename in ["Pipfile", "Pipfile.lock"]:
            dependencies = self._parse_pipfile(file_path)

        return dependencies

    def _parse_requirements_txt(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                match = re.match(r'^([\w.-]+)(?:\[([^\]]+)\])?([^;,\s]*)', line)
                if match:
                    package_name = self._normalize_pypi_name(match.group(1))
                    extras = match.group(2)
                    version = match.group(3)
                    metadata = (('extras', extras),) if extras else ()
                    dependencies.append(('Python', package_name, version, metadata))
                else:
                    dependencies.append(('Python', line, 'latest'))

        return dependencies

    def _parse_pyproject_toml(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []
        try:
            import toml
            pyproject = toml.load(file_path)

            if 'tool' in pyproject and 'poetry' in pyproject['tool']:
                poetry_deps = pyproject['tool']['poetry'].get('dependencies', {})
                for package, version in poetry_deps.items():
                    if package != 'python' and isinstance(version, str):
                        dependencies.append(('Python', package, version))
                    elif package != 'python' and isinstance(version, dict):
                        dependencies.append(('Python', package, version.get('version', 'latest')))

            if 'project' in pyproject and 'dependencies' in pyproject['project']:
                for dep in pyproject['project']['dependencies']:
                    match = re.match(r'^([a-zA-Z0-9_.-]+)([~<>=!]=?|===)(.+)$', dep)
                    if match:
                        package_name = match.group(1)
                        version = match.group(3)
                        dependencies.append(('Python', package_name, version))
                    else:
                        dependencies.append(('Python', dep, 'latest'))
        except ImportError:
            pass
        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    def _parse_setup_py(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        with open(file_path, 'r') as file:
            content = file.read()

        install_requires = re.search(r'install_requires\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if install_requires:
            deps_str = install_requires.group(1)
            for dep in re.finditer(r'[\'"]([^\'"]*)[\'"]\s*,?', deps_str):
                req_str = dep.group(1)
                match = re.match(r'^([a-zA-Z0-9_.-]+)([~<>=!]=?|===)(.+)$', req_str)
                if match:
                    package_name = match.group(1)
                    version = match.group(3)
                    dependencies.append(('Python', package_name, version))
                else:
                    dependencies.append(('Python', req_str, 'latest'))

        return dependencies

    def _parse_pipfile(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        if file_path.endswith('Pipfile.lock'):
            try:
                import json
                with open(file_path, 'r') as file:
                    data = json.load(file)

                if 'default' in data:
                    for package, info in data['default'].items():
                        version = info.get('version', 'latest')
                        if version.startswith('=='):
                            version = version[2:]
                        dependencies.append(('Python', package, version))
            except Exception as e:
                logs.error(f"Error parsing {file_path}: {e}")
        else:  # Pipfile
            try:
                import toml
                with open(file_path, 'r') as file:
                    data = toml.load(file)

                if 'packages' in data:
                    for package, version in data['packages'].items():
                        dependencies.append(('Python', package, str(version)))
            except ImportError:
                pass
            except Exception as e:
                logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    def _parse_poetry_lock(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []
        try:
            import toml
            data = toml.load(file_path)
            packages = data.get('package', [])
            direct_names = self._poetry_direct_names(file_path)

            package_components = {}
            for package in packages:
                name = package.get('name')
                version = package.get('version')
                if not name or not version or not self._include_poetry_package(package, direct_names):
                    continue
                component = ('Python', self._normalize_pypi_name(name), str(version))
                package_components.setdefault(self._normalize_pypi_name(name), component)
                dependencies.append(component)

            for package in packages:
                source = package_components.get(
                    self._normalize_pypi_name(package.get('name', ''))
                )
                if not source:
                    continue
                for dependency_name in package.get('dependencies', {}):
                    target = package_components.get(
                        self._normalize_pypi_name(dependency_name)
                    )
                    if target:
                        self._dependency_relations.append((source, target))

            for direct_name in direct_names:
                target = package_components.get(direct_name)
                if target:
                    self._dependency_relations.append((None, target))
        except ImportError:
            pass
        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    def _poetry_direct_names(self, lock_path: str):
        pyproject_path = os.path.join(os.path.dirname(lock_path), 'pyproject.toml')
        if not os.path.exists(pyproject_path):
            return set()

        try:
            import toml
            pyproject = toml.load(pyproject_path)
            poetry_dependencies = (
                pyproject.get('tool', {}).get('poetry', {}).get('dependencies', {})
            )
            names = {
                self._normalize_pypi_name(name)
                for name in poetry_dependencies
                if name.lower() != 'python'
            }
            for dependency in pyproject.get('project', {}).get('dependencies', []):
                match = re.match(r'^([a-zA-Z0-9_.-]+)', dependency)
                if match:
                    names.add(self._normalize_pypi_name(match.group(1)))
            return names
        except Exception as e:
            logs.error(f"Error reading direct Poetry dependencies from {pyproject_path}: {e}")
            return set()

    def _include_poetry_package(self, package, direct_names):
        normalized_name = self._normalize_pypi_name(package.get('name', ''))
        if self.only_direct and direct_names:
            return normalized_name in direct_names
        if self.only_direct:
            groups = package.get('groups')
            if groups is not None:
                return 'main' in groups
            return package.get('category', 'main') == 'main'
        return True

    @staticmethod
    def _normalize_pypi_name(name: str) -> str:
        return re.sub(r'[-_.]+', '-', name).lower()

    def get_dependency_relations(self):
        return self._dependency_relations
