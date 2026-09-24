import datetime
import json
import os
import uuid

from metadata import __title__, __vendor__, __version__


def save_cyclonedx(results, repo_path, output_path):
    purl_types = {
        "Python": "pypi",
        "JavaScript": "npm",
        "Java": "maven",
        "C#": "nuget",
        "Go": "golang",
        "Rust": "cargo",
        "PHP": "composer",
        "Ruby": "gem",
    }

    def purl_for(lang, lib, ver, source_file=None):
        if lang == "C++":
            purl_type = "conan" if source_file == "conanfile.txt" else "generic"
        else:
            purl_type = purl_types.get(lang, "generic")
        return f"pkg:{purl_type}/{lib}@{ver}"

    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.datetime.now().isoformat(),
            "tools": [
                {
                    "vendor": __title__,
                    "name": __vendor__,
                    "version": __version__
                }
            ]
        },
        "components": []
    }

    source_property_names = {
        "Python": "cdx:pypi:source:file",
        "JavaScript": "cdx:npm:source:file",
        "Go": "cdx:golang:source:file",
    }

    for dependency in results['dependencies']:
        lang, lib, ver, *source = dependency
        purl = purl_for(lang, lib, ver, source[0] if source else None)
        package_metadata = dict(source[1]) if len(source) > 1 else {}
        # component_uuid = str(uuid.uuid4())

        component = {
            "type": "library",
            "bom-ref": purl,
            "name": lib,
            "version": ver,
            "purl": purl,
            "properties": [
                {
                    "name": "language",
                    "value": lang
                }
            ]
        }

        if source and lang in source_property_names:
            component["properties"].append({
                "name": source_property_names[lang],
                "value": source[0],
            })

        license_name = package_metadata.get("license")
        if license_name:
            component["licenses"] = [{"license": {"name": license_name}}]

        resolved = package_metadata.get("resolved")
        if resolved:
            component["properties"].append({
                "name": "cdx:npm:package:resolved",
                "value": resolved,
            })

        extras = package_metadata.get("extras")
        if extras:
            component["properties"].append({
                "name": "cdx:pypi:package:extras",
                "value": extras,
            })

        bom["components"].append(component)

    project_component = {
        "type": "application",
        "bom-ref": "project",
        "name": os.path.basename(repo_path) if repo_path.rstrip('/') else "unknown-project",
        "properties": []
    }

    for language, count in results['languages'].items():
        project_component["properties"].append({
            "name": f"files.language.{language.lower()}",
            "value": str(count)
        })

    bom["components"].insert(0, project_component)

    dependency_graph = {"project": set()}
    for component in bom["components"][1:]:
        dependency_graph[component["bom-ref"]] = set()

    for source, target in results.get('dependency_relations', []):
        source_ref = "project" if source is None else purl_for(*source)
        target_ref = purl_for(*target)
        if source_ref in dependency_graph and target_ref in dependency_graph:
            dependency_graph[source_ref].add(target_ref)
    # if dependency_graph:
    bom["dependencies"] = [
        {"ref": ref, "dependsOn": sorted(depends_on)}
        for ref, depends_on in dependency_graph.items() if depends_on
    ]

    with open(output_path, 'w') as f:
        json.dump(bom, f, indent=2)
