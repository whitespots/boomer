import os
import re
import xml.etree.ElementTree as ET
from typing import List, Tuple

from .base_parser import Parser
from helpers.log import logs

class CSharpParser(Parser):

    def find_dependency_files(self) -> List[str]:
        dependency_files = []

        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith('.csproj'):
                    dependency_files.append(os.path.join(root, file))
                elif file == 'packages.config':
                    dependency_files.append(os.path.join(root, file))
                elif file.endswith('.sln'):
                    dependency_files.append(os.path.join(root, file))

        return dependency_files

    def parse_dependencies(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        if file_path.endswith('.csproj'):
            dependencies = self._parse_csproj(file_path)
        elif os.path.basename(file_path) == 'packages.config':
            dependencies = self._parse_packages_config(file_path)
        elif file_path.endswith('.sln'):
            dependencies = self._parse_sln(file_path)

        return dependencies

    def _parse_csproj(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            namespace = root.tag.split('}')[0] + '}' if '}' in root.tag else ''

            package_refs = root.findall(f".//{namespace}PackageReference")
            for pkg_ref in package_refs:
                package = pkg_ref.get('Include')
                version = pkg_ref.get('Version')
                if not version:
                    version_elem = pkg_ref.find(f'.//{namespace}Version')
                    version = version_elem.text if version_elem is not None else 'latest'

                if package:
                    dependencies.append(('C#', package, version or 'latest'))

            hint_paths = root.findall(f".//{namespace}Reference/{namespace}HintPath")
            for hint_path in hint_paths:
                path = hint_path.text
                if path and 'packages' in path:
                    parts = path.split('\\')
                    for i, part in enumerate(parts):
                        if part == 'packages' and i + 1 < len(parts):
                            package_info = parts[i + 1].split('.')
                            if len(package_info) >= 2:
                                version = package_info[-1]
                                package = '.'.join(package_info[:-1])
                                dependencies.append(('C#', package, version))
                                break

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    def _parse_packages_config(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            for package in root.findall(".//package"):
                package_id = package.get('id')
                version = package.get('version')

                if package_id:
                    dependencies.append(('C#', package_id, version or 'latest'))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    def _parse_sln(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as file:
                content = file.read()

            nuget_section = re.search(r'GlobalSection\(NuGetPackageImports\)(.*?)EndGlobalSection', content, re.DOTALL)
            if nuget_section:
                nuget_content = nuget_section.group(1)

                package_refs = re.finditer(r'([a-zA-Z0-9_.-]+)\.(\d+\.\d+\.\d+(?:\.\d+)?)', nuget_content)
                for match in package_refs:
                    package = match.group(1)
                    version = match.group(2)
                    dependencies.append(('C#', package, version))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies