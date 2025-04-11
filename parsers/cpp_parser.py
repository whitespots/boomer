import os
import re
import json
from typing import List, Tuple

from .base_parser import Parser
from consts.dependency_files import DEPENDENCY_FILES
from helpers.log import logs


class CppParser(Parser):

    def find_dependency_files(self) -> List[str]:

        dependency_files = []
        cpp_dep_files = DEPENDENCY_FILES['C++']

        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file in cpp_dep_files:
                    dependency_files.append(os.path.join(root, file))

        return dependency_files

    def parse_dependencies(self, file_path: str) -> List[Tuple[str, str, str]]:

        dependencies = []
        filename = os.path.basename(file_path)

        if filename == "CMakeLists.txt":
            dependencies = self._parse_cmake(file_path)
        elif filename == "conanfile.txt":
            dependencies = self._parse_conan(file_path)
        elif filename == "vcpkg.json":
            dependencies = self._parse_vcpkg(file_path)

        return dependencies

    def _parse_cmake(self, file_path: str) -> List[Tuple[str, str, str]]:

        dependencies = []

        try:
            with open(file_path, 'r') as file:
                content = file.read()

            find_packages = re.finditer(r'find_package\s*\(\s*([^\s]+)(?:\s+([^\s\)]+))?', content, re.IGNORECASE)
            for match in find_packages:
                package = match.group(1)
                version = match.group(2) if match.group(2) else 'latest'

                if package.lower() not in ['cmake', 'packages', 'components']:
                    dependencies.append(('C++', package, version))

            external_projects = re.finditer(r'ExternalProject_Add\s*\(\s*([^\s]+)', content, re.IGNORECASE)
            for match in external_projects:
                package = match.group(1)
                version_match = re.search(rf'ExternalProject_Add\s*\(\s*{re.escape(package)}.*?VERSION\s+([^\s\)]+)',
                                          content, re.DOTALL | re.IGNORECASE)
                version = version_match.group(1) if version_match else 'latest'
                dependencies.append(('C++', package, version))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    def _parse_conan(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            with open(file_path, 'r') as file:
                content = file.read()

            requires_section = re.search(r'\[requires\](.*?)(?=\[|\Z)', content, re.DOTALL)
            if requires_section:
                requires_content = requires_section.group(1)

                for line in requires_content.strip().split('\n'):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    parts = line.split('/')
                    if len(parts) >= 2:
                        package = parts[0]
                        version = parts[1]
                        dependencies.append(('C++', package, version))
                    else:
                        dependencies.append(('C++', line, 'latest'))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    def _parse_vcpkg(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            with open(file_path, 'r') as file:
                data = json.load(file)

            if 'dependencies' in data:
                for dep in data['dependencies']:
                    if isinstance(dep, str):
                        dependencies.append(('C++', dep, 'latest'))
                    elif isinstance(dep, dict) and 'name' in dep:
                        package = dep['name']
                        version = dep.get('version-string', dep.get('version', 'latest'))
                        dependencies.append(('C++', package, version))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies