#!/usr/bin/env python3

import sys

import click
from loguru import logger

from consts.file_extensions import LANGUAGE_EXTENSIONS
from helpers.cyclonedx_converter import save_cyclonedx
from helpers.log import logs
from helpers.scanner import RepositoryScanner
from metadata import __version__, __license__, __title__, __description__, __copyrights__, __bmw__


@click.group(help=f"{__title__} - {__description__}")
def cli():
    """Repository Scanner command line interface."""
    pass


@cli.command(help="Scan repository for CycloneDX BOM")
@click.argument('repo_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('-o', '--output', 'output_path',
              type=click.Path(),
              help='Path to output file')
def scan(repo_path, output_path):
    logs.info(f"{__title__} START ENGINE")
    logs.info("WROOM WROOM")
    logs.info(__bmw__)

    scanner = RepositoryScanner(repo_path)

    logs.info("Determining languages...")
    languages = scanner.scan_languages()
    logs.info(f"Found languages: {languages}")

    logs.info("Scanning dependencies...")
    scanner.scan_dependencies()

    logs.info("Convert to cyclonedx...")
    try:
        save_cyclonedx(scanner.get_results(), repo_path, output_path)

        logs.success(f"CycloneDX BOM saved to {output_path}")
    except Exception as e:
        logger.error(f"Error exporting results: {e}")
        return 1

    return 0


@cli.command(help="List supported languages")
def languages():
    click.echo("Supported languages:")
    for language in sorted(LANGUAGE_EXTENSIONS.keys()):
        click.echo(f"  - {language}")


@cli.command(help="Show version information")
def version():
    click.echo(f"{__title__} v{__version__}")
    click.echo(__copyrights__)
    click.echo(__license__)


if __name__ == "__main__":
    sys.exit(cli())
