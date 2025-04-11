import os
import re
from typing import List, Tuple
import pkg_resources
from helpers.log import logs
from .base_parser import Parser
from consts.dependency_files import DEPENDENCY_FILES


class PythonParser(Parser):

    def find_dependency_files(self) -> List[str]:
        dependency_files = []
        python_dep_files = DEPENDENCY_FILES['Python']

        for root, _, files in os.walk(self.repo_path):
            for file in files:
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

                match = re.match(r'^([\w\-\[\]]+)(?:===|==|>=|<=|~=|>|<)?([^;,\s]*)', line)
                if match:
                    package_name = match.group(1)
                    version = match.group(2)
                    dependencies.append(('Python', package_name, version))
                else:
                    dependencies.append(('Python', line, 'latest'))

        return dependencies

    def _parse_pyproject_toml(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []
        try:
            import tomli
            with open(file_path, 'rb') as file:
                pyproject = tomli.load(file)

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