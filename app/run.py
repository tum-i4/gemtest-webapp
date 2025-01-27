import importlib.metadata
from pathlib import Path

import click

from app import create_app

default_dir = Path("gemtest_results")


@click.command(help="Run the gemtest-webapp app")
@click.option("--results-dir",
              type=click.Path(exists=True, dir_okay=True, path_type=Path),
              default=default_dir,
              help="The directory where gemtest-webapp loads results from.")
@click.version_option(version=importlib.metadata.version("gemtest-webapp"))
def main(results_dir: Path = default_dir) -> None:
    app = create_app(results_dir)

    app.run()


if __name__ == '__main__':
    main()
