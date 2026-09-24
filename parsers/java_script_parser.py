import os
import json
import re
from typing import List, Tuple

from .base_parser import Parser
from consts.dependency_files import DEPENDENCY_FILES
from helpers.log import logs

class JavaScriptParser(Parser):

    def __init__(self, repo_path: str, only_direct=False, prefer_locks=False):
        super().__init__(repo_path, only_direct, prefer_locks)
        self._dependency_relations = []

    def find_dependency_files(self) -> List[str]:
        dependency_files = []
        for root, _, files in os.walk(self.repo_path):
            if "node_modules" in root:
                continue
            files = set(files)
            if self.prefer_locks:
                selected_file = next(
                    (file for file in ('package-lock.json', 'yarn.lock') if file in files),
                    None,
                )
            else:
                selected_file = next(
                    (file for file in ('package.json', 'package-lock.json', 'yarn.lock') if file in files),
                    None,
                )

            if selected_file:
                dependency_files.append(os.path.join(root, selected_file))

        return dependency_files

    def parse_dependencies(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []
        filename = os.path.basename(file_path)

        if filename == "package-lock.json":
            dependencies = self._parse_package_lock(file_path)
        elif filename == "package.json":
            dependencies = self._parse_package_json(file_path)
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
                self._dependency_relations = self._build_package_lock_relations(data['packages'])
                for package_path, info in data['packages'].items():
                    if package_path == '':  # Это сам проект
                        continue
                    package_name = package_path.split('node_modules/')[-1]
                    version = info.get('version', 'latest')
                    dependencies.append((
                        'JavaScript',
                        package_name,
                        version,
                        (
                            ('license', info.get('license')),
                            ('resolved', info.get('resolved')),
                        ),
                    ))
            elif 'dependencies' in data:
                for package, info in data['dependencies'].items():
                    version = info.get('version', 'latest')
                    dependencies.append((
                        'JavaScript',
                        package,
                        version,
                        (
                            ('license', info.get('license')),
                            ('resolved', info.get('resolved')),
                        ),
                    ))
                    self._dependency_relations.append(
                        (None, ('JavaScript', package, version))
                    )

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    def _build_package_lock_relations(self, packages):
        package_components = {}
        for package_path, info in packages.items():
            if not package_path:
                continue
            package_name = package_path.split('node_modules/')[-1]
            package_components[package_path] = (
                'JavaScript',
                package_name,
                info.get('version', 'latest'),
            )

        relations = []
        for package_path, info in packages.items():
            source = package_components.get(package_path)
            for dependency_name in info.get('dependencies', {}):
                dependency_path = self._resolve_dependency_path(
                    package_path,
                    dependency_name,
                    package_components,
                )
                if dependency_path:
                    relations.append((source, package_components[dependency_path]))

        return relations

    def _resolve_dependency_path(self, package_path, dependency_name, package_components):
        current_path = package_path
        while True:
            prefix = f"{current_path}/" if current_path else ""
            candidate = f"{prefix}node_modules/{dependency_name}"
            if candidate in package_components:
                return candidate

            if not current_path:
                return None

            parent_marker = current_path.rfind('/node_modules/')
            current_path = current_path[:parent_marker] if parent_marker >= 0 else ''

    def _parse_yarn_lock(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            with open(file_path, 'r') as file:
                content = file.read()

            package_entries = []
            for section in content.split('\n\n'):
                lines = [line for line in section.splitlines() if line.strip()]
                if not lines or lines[0].lstrip().startswith('#'):
                    continue

                selectors = [selector.strip().strip('"') for selector in lines[0].rstrip(':').split(',')]
                package_names = {
                    self._yarn_package_name(selector)
                    for selector in selectors
                    if '@' in selector
                }
                version = self._yarn_lock_value(lines, 'version')
                if not package_names or not version:
                    continue

                resolved = self._yarn_lock_value(lines, 'resolved')
                package_name = sorted(package_names)[0]
                component = ('JavaScript', package_name, version)
                package_entries.append((selectors, component, self._yarn_dependencies(lines)))
                dependencies.append((
                    *component,
                    (('resolved', resolved),),
                ))

            components_by_selector = {}
            components_by_name = {}
            for selectors, component, _ in package_entries:
                for selector in selectors:
                    components_by_selector[selector] = component
                components_by_name.setdefault(component[1], component)

            for _, source, child_dependencies in package_entries:
                for dependency_name, dependency_range in child_dependencies:
                    target = components_by_selector.get(
                        f'{dependency_name}@{dependency_range}'
                    ) or components_by_name.get(dependency_name)
                    if target:
                        self._dependency_relations.append((source, target))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    @staticmethod
    def _yarn_package_name(selector):
        return selector.rsplit('@', 1)[0]

    @staticmethod
    def _yarn_lock_value(lines, key):
        for line in lines[1:]:
            match = re.match(rf'^\s+{key}\s+"([^"]+)"', line)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _yarn_dependencies(lines):
        dependencies = []
        in_dependencies = False
        for line in lines[1:]:
            if line.strip() == 'dependencies:':
                in_dependencies = True
                continue
            if in_dependencies and line.startswith('    '):
                name, _, version = line.strip().partition(' ')
                dependencies.append((name, version.strip('"')))
            elif in_dependencies:
                in_dependencies = False
        return dependencies

    def get_dependency_relations(self):
        return self._dependency_relations
