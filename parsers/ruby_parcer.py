import os
import re
from typing import List, Tuple

from .base_parser import Parser
from consts.dependency_files import DEPENDENCY_FILES
from helpers.log import logs

class RubyParser(Parser):

    def find_dependency_files(self) -> List[str]:

        dependency_files = []
        ruby_dep_files = DEPENDENCY_FILES['Ruby']

        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file in ruby_dep_files:
                    dependency_files.append(os.path.join(root, file))

        return dependency_files

    def parse_dependencies(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []
        filename = os.path.basename(file_path)

        if filename == "Gemfile":
            dependencies = self._parse_gemfile(file_path)
        elif filename == "Gemfile.lock":
            dependencies = self._parse_gemfile_lock(file_path)

        return dependencies

    def _parse_gemfile(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            with open(file_path, 'r') as file:
                content = file.read()

            gem_pattern = r'gem\s+[\'"]([^\'"]+)[\'"](?:\s*,\s*[\'"]([^\'"]+)[\'"])?'
            for match in re.finditer(gem_pattern, content):
                gem_name = match.group(1)
                version = match.group(2) if match.group(2) else 'latest'
                dependencies.append(('Ruby', gem_name, version))

            gem_version_pattern = r'gem\s+[\'"]([^\'"]+)[\'"](?:.*?:version\s*=>\s*[\'"]([^\'"]+)[\'"])?'
            for match in re.finditer(gem_version_pattern, content):
                gem_name = match.group(1)
                version = match.group(2) if match.group(2) else 'latest'
                dependencies.append(('Ruby', gem_name, version))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    def _parse_gemfile_lock(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            with open(file_path, 'r') as file:
                content = file.readlines()

            in_specs = False
            for line in content:
                line = line.strip()

                if line == "GEM":
                    in_specs = True
                    continue

                if in_specs and line.startswith("  "):
                    if re.match(r'    [a-zA-Z0-9_-]+\s+\(', line):
                        match = re.match(r'    ([a-zA-Z0-9_-]+)\s+\(([^)]+)\)', line)
                        if match:
                            gem_name = match.group(1)
                            version = match.group(2)
                            dependencies.append(('Ruby', gem_name, version))

                if in_specs and line and not line.startswith(" "):
                    in_specs = False

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies