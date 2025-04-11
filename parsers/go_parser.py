import os
import re
from typing import List, Tuple

from .base_parser import Parser
from consts.dependency_files import DEPENDENCY_FILES
from helpers.log import logs

class GoParser(Parser):

    def find_dependency_files(self) -> List[str]:
        dependency_files = []
        go_dep_files = DEPENDENCY_FILES['Go']

        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file in go_dep_files:
                    dependency_files.append(os.path.join(root, file))

        return dependency_files

    def parse_dependencies(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []
        filename = os.path.basename(file_path)

        if filename == "go.mod":
            dependencies = self._parse_go_mod(file_path)
        elif filename == "go.sum":
            dependencies = self._parse_go_sum(file_path)
        elif filename in ["Gopkg.toml", "Gopkg.lock"]:
            dependencies = self._parse_gopkg(file_path)

        return dependencies

    def _parse_go_mod(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            with open(file_path, 'r') as file:
                content = file.read()

            require_lines = re.finditer(r'require\s+([^\s]+)\s+([^\s]+)', content)
            for match in require_lines:
                package = match.group(1)
                version = match.group(2)
                dependencies.append(('Go', package, version))

            require_block = re.search(r'require\s+\((.*?)\)', content, re.DOTALL)
            if require_block:
                block_content = require_block.group(1)
                for line in block_content.strip().split('\n'):
                    line = line.strip()
                    if not line or line.startswith('//'):
                        continue

                    parts = line.split()
                    if len(parts) >= 2:
                        package = parts[0]
                        version = parts[1]
                        dependencies.append(('Go', package, version))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    def _parse_go_sum(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []
        seen_packages = set()

        try:
            with open(file_path, 'r') as file:
                for line in file:
                    line = line.strip()
                    if not line:
                        continue

                    parts = line.split()
                    if len(parts) >= 2:
                        package = parts[0]
                        if package.endswith('/go.mod'):
                            package = package[:-7]

                        version = parts[1]

                        package_version = (package, version)
                        if package_version not in seen_packages:
                            seen_packages.add(package_version)
                            dependencies.append(('Go', package, version))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    def _parse_gopkg(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            with open(file_path, 'r') as file:
                content = file.read()

            if file_path.endswith('Gopkg.toml'):
                constraints = re.finditer(r'\[\[constraint\]\]\s+name\s*=\s*"([^"]+)"(?:.*?version\s*=\s*"([^"]+)")?',
                                          content, re.DOTALL)
                for match in constraints:
                    package = match.group(1)
                    version = match.group(2) if match.group(2) else 'latest'
                    dependencies.append(('Go', package, version))

                overrides = re.finditer(r'\[\[override\]\]\s+name\s*=\s*"([^"]+)"(?:.*?version\s*=\s*"([^"]+)")?',
                                        content, re.DOTALL)
                for match in overrides:
                    package = match.group(1)
                    version = match.group(2) if match.group(2) else 'latest'
                    dependencies.append(('Go', package, version))

            else:
                projects = re.finditer(r'\[\[projects\]\]\s+name\s*=\s*"([^"]+)"(?:.*?version\s*=\s*"([^"]+)")?',
                                       content, re.DOTALL)
                for match in projects:
                    package = match.group(1)
                    version = match.group(2) if match.group(2) else 'latest'
                    dependencies.append(('Go', package, version))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies