import click
import logging
import sys
from .server import serve


@click.command()
@click.option("--profile", "-p", type=str, help="AWS profile")
@click.option("--region", "-r", type=str, help="AWS region", default="us-east-1")
@click.option("--user-pool-id", "-u", required=True, type=str, help="Cognito user pool id")
@click.option("-v", "--verbose", count=True)
def main(profile: str | None, region: str | None, user_pool_id: str, verbose: bool) -> None:
    """MCP Cognito Server - Cognito functionality for MCP"""
    import asyncio

    logging_level = logging.WARN
    if verbose == 1:
        logging_level = logging.INFO
    elif verbose >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(level=logging_level, stream=sys.stderr)
    asyncio.run(serve(user_pool_id=user_pool_id, profile=profile, region=region))


if __name__ == "__main__":
    main()
