import os
import json
from typing import List, Tuple

from .base_parser import Parser
from consts.dependency_files import DEPENDENCY_FILES
from helpers.log import logs

class JavaScriptParser(Parser):

    def find_dependency_files(self) -> List[str]:
        dependency_files = []
        js_dep_files = DEPENDENCY_FILES['JavaScript']

        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file in js_dep_files:
                    dependency_files.append(os.path.join(root, file))

        return dependency_files

    def parse_dependencies(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []
        filename = os.path.basename(file_path)

        if filename == "package.json":
            dependencies = self._parse_package_json(file_path)
        elif filename == "package-lock.json":
            dependencies = self._parse_package_lock(file_path)
        elif filename == "yarn.lock":
            dependencies = self._parse_yarn_lock(file_path)

        return dependencies

    def _parse_package_json(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            with open(file_path, 'r') as file:
                data = json.load(file)

            if 'dependencies' in data:
                for package, version in data['dependencies'].items():
                    dependencies.append(('JavaScript', package, version))
            if 'devDependencies' in data:
                for package, version in data['devDependencies'].items():
                    dependencies.append(('JavaScript', package, version))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    def _parse_package_lock(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            with open(file_path, 'r') as file:
                data = json.load(file)

            if 'packages' in data:
                for package_path, info in data['packages'].items():
                    if package_path == '':  # Это сам проект
                        continue
                    package_name = package_path.split('node_modules/')[-1]
                    version = info.get('version', 'latest')
                    dependencies.append(('JavaScript', package_name, version))
            elif 'dependencies' in data:
                for package, info in data['dependencies'].items():
                    version = info.get('version', 'latest')
                    dependencies.append(('JavaScript', package, version))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    def _parse_yarn_lock(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            with open(file_path, 'r') as file:
                content = file.read()

            package_sections = content.split('\n\n')
            for section in package_sections:
                if not section.strip():
                    continue

                first_line = section.split('\n')[0].strip()
                if first_line.startswith('"') and '@' in first_line:
                    # Это запись о пакете
                    package_spec = first_line.strip('"')
                    package_name = package_spec.split('@')[0]

                    version_line = [line for line in section.split('\n') if '  version' in line]
                    if version_line:
                        version = version_line[0].split('"')[1]
                        dependencies.append(('JavaScript', package_name, version))
                    else:
                        dependencies.append(('JavaScript', package_name, 'unknown'))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies