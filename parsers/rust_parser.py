import os
import re
import toml
from typing import List, Tuple

from .base_parser import Parser
from consts.dependency_files import DEPENDENCY_FILES
from helpers.log import logs

class RustParser(Parser):
    def find_dependency_files(self) -> List[str]:
        dependency_files = []
        rust_dep_files = DEPENDENCY_FILES['Rust']

        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file in rust_dep_files:
                    dependency_files.append(os.path.join(root, file))

        return dependency_files

    def parse_dependencies(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []
        filename = os.path.basename(file_path)

        if filename == "Cargo.toml":
            dependencies = self._parse_cargo_toml(file_path)
        elif filename == "Cargo.lock":
            dependencies = self._parse_cargo_lock(file_path)

        return dependencies

    def _parse_cargo_toml(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []

        try:
            data = toml.load(file_path)

            if 'dependencies' in data:
                for package, config in data['dependencies'].items():
                    version = 'latest'

                    if isinstance(config, str):
                        version = config
                    elif isinstance(config, dict):
                        if 'version' in config:
                            version = config['version']

                    dependencies.append(('Rust', package, version))

            if 'dev-dependencies' in data:
                for package, config in data['dev-dependencies'].items():
                    version = 'latest'

                    if isinstance(config, str):
                        version = config
                    elif isinstance(config, dict) and 'version' in config:
                        version = config['version']

                    dependencies.append(('Rust', package, version))

            if 'build-dependencies' in data:
                for package, config in data['build-dependencies'].items():
                    version = 'latest'

                    if isinstance(config, str):
                        version = config
                    elif isinstance(config, dict) and 'version' in config:
                        version = config['version']

                    dependencies.append(('Rust', package, version))

            if 'target' in data:
                for _, target_config in data['target'].items():
                    if 'dependencies' in target_config:
                        for package, config in target_config['dependencies'].items():
                            version = 'latest'

                            if isinstance(config, str):
                                version = config
                            elif isinstance(config, dict) and 'version' in config:
                                version = config['version']

                            dependencies.append(('Rust', package, version))

        except Exception as e:
            logs.error(f"Error parsing {file_path}: {e}")

        return dependencies

    def _parse_cargo_lock(self, file_path: str) -> List[Tuple[str, str, str]]:
        dependencies = []
        seen_packages = set()

        try:
            data = toml.load(file_path)

            if 'package' in data:
                for package in data['package']:
                    if 'name' in package and 'version' in package:
                        name = package['name']
                        version = package['version']

                        if name not in seen_packages:
                            seen_packages.add(name)
                            dependencies.append(('Rust', name, version))

            elif 'dependencies' in data:
                for dep in data['dependencies']:
                    if isinstance(dep, dict) and 'name' in dep and 'version' in dep:
                        name = dep['name']
                        version = dep['version']

                        if name not in seen_packages:
                            seen_packages.add(name)
                            dependencies.append(('Rust', name, version))

        except Exception as e:
            try:
                with open(file_path, 'r') as file:
                    content = file.read()

                packages = re.finditer(r'\[\[package\]\]\s+name\s*=\s*"([^"]+)"\s+version\s*=\s*"([^"]+)"', content,
                                       re.DOTALL)
                for match in packages:
                    name = match.group(1)
                    version = match.group(2)

                    if name not in seen_packages:
                        seen_packages.add(name)
                        dependencies.append(('Rust', name, version))

            except Exception as inner_e:
                logs.error(f"Error parsing {file_path}: {e} -> {inner_e}")

        return dependencies