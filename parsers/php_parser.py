import os
import json
from typing import List, Tuple

from .base_parser import Parser
from consts.dependency_files import DEPENDENCY_FILES
from helpers.log import logs

class PhpParser(Parser):

    def find_dependency_files(self) -> List[str]:

        dependency_files = []
        php_dep_files = DEPENDENCY_FILES['PHP']

        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file in php_dep_files:
                    dependency_files.append(os.path.join(root, file))

        return dependency_files

    def parse_dependencies(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []
        filename = os.path.basename(file_path)

        if filename == "composer.json":
            dependencies = self._parse_composer_json(file_path)
        elif filename == "composer.lock":
            dependencies = self._parse_composer_lock(file_path)

        return dependencies

    def _parse_composer_json(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            with open(file_path, 'r') as file:
                data = json.load(file)

            if 'require' in data:
                for package, version in data['require'].items():
                    if package != 'php':
                        dependencies.append(('PHP', package, version))

            if 'require-dev' in data:
                for package, version in data['require-dev'].items():
                    dependencies.append(('PHP', package, version))

            if 'replace' in data:
                for package, version in data['replace'].items():
                    dependencies.append(('PHP', package, version))

            if 'provide' in data:
                for package, version in data['provide'].items():
                    dependencies.append(('PHP', package, version))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    def _parse_composer_lock(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            with open(file_path, 'r') as file:
                data = json.load(file)

            if 'packages' in data:
                for package in data['packages']:
                    if 'name' in package and 'version' in package:
                        name = package['name']
                        version = package['version']
                        dependencies.append(('PHP', name, version))

            if 'packages-dev' in data:
                for package in data['packages-dev']:
                    if 'name' in package and 'version' in package:
                        name = package['name']
                        version = package['version']
                        dependencies.append(('PHP', name, version))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies