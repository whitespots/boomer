import os
import json
from typing import List, Tuple

from .base_parser import Parser
from consts.dependency_files import DEPENDENCY_FILES
from helpers.log import logs

class PhpParser(Parser):

    def __init__(self, repo_path: str, only_direct=False, prefer_locks=False):
        super().__init__(repo_path, only_direct, prefer_locks)
        self._dependency_relations = []

    def find_dependency_files(self) -> List[str]:
        dependency_files = []

        for root, _, files in os.walk(self.repo_path):
            files = set(files)
            if self.prefer_locks:
                selected_file = 'composer.lock' if 'composer.lock' in files else None
            else:
                selected_file = next(
                    (file for file in ('composer.json', 'composer.lock') if file in files),
                    None,
                )

            if selected_file:
                dependency_files.append(os.path.join(root, selected_file))

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

            packages = data.get('packages', []) + data.get('packages-dev', [])
            package_components = {
                package['name']: ('PHP', package['name'], package['version'])
                for package in packages
                if 'name' in package and 'version' in package
            }
            dependencies.extend(package_components.values())

            for package in packages:
                source = package_components.get(package.get('name'))
                if not source:
                    continue
                for dependency_name in package.get('require', {}):
                    target = package_components.get(dependency_name)
                    if target:
                        self._dependency_relations.append((source, target))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    def get_dependency_relations(self):
        return self._dependency_relations
