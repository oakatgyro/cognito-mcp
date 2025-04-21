import boto3
import logging
from typing import Any, Literal
from mcp import Tool, TextContent
from mcp.server import Server
from mcp.server.stdio import stdio_server
from enum import Enum
from pydantic import BaseModel


class CognitoTools(str, Enum):
    LIST_USER_POOLS = "cognito_list_user_pools"
    LIST_IDENTITY_PROVIDERS = "cognito_list_identity_providers"
    LIST_USERS = "cognito_list_users"
    GET_USER = "cognito_get_user"


class CognitoListUserPools(BaseModel):
    limit: int = 60


class CognitoListIdentityProviders(BaseModel):
    limit: int = 60


class CognitoListUsers(BaseModel):
    attribute_name: (
        Literal["username", "email", "phone_number", "cognito:user_status", "status", "sub"] | None
    ) = None
    filter_type: Literal["=", "^="] | None = None
    pagination_token: str | None = None
    limit: int = 60


class CognitoGetUser(BaseModel):
    username: str | None = None


def list_user_pools(client, limit: int = 60) -> list[dict] | str:
    """List all user pools."""

    try:
        response = client.list_user_pools(MaxResults=limit)
        return response.get("UserPools", [])
    except Exception as e:
        return f"Error listing user pools: {str(e)}"


def list_identity_providers(client, user_pool_id: str, limit: int = 60) -> list[dict] | str:
    """List all identity providers for the user pool."""

    try:
        response = client.list_identity_providers(UserPoolId=user_pool_id, Limit=limit)
        return response.get("Providers", [])
    except Exception as e:
        return f"Error listing identity providers: {str(e)}"


def get_user(client, user_pool_id: str, identifier: str) -> dict[str, Any] | str:
    """Get user details by UUID or email."""

    try:
        # Try to get user by UUID first
        try:
            response = client.admin_get_user(UserPoolId=user_pool_id, Username=identifier)
            return response
        except client.exceptions.UserNotFoundException:
            # If not found by UUID, try to find by email
            return "User not found"
        except client.exceptions.ResourceNotFoundException as e:
            return f"Error getting user: {str(e)}"
    except Exception as e:
        return f"Error getting user: {str(e)}"


def list_users(
    client,
    user_pool_id: str,
    filter_type: Literal["=", "^="] | None = None,
    attribute_name: Literal[
        "username", "email", "phone_number", "cognito:user_status", "status", "sub"
    ]
    | None = None,
    pagination_token: str | None = None,
    limit: int | None = 60,
) -> list[dict[str, Any]] | str:
    """List users with optional filtering."""

    try:
        params = {"UserPoolId": user_pool_id, "Limit": limit}

        if filter_type and attribute_name:
            params["Filter"] = f"{filter_type} {attribute_name}"

        if pagination_token:
            params["PaginationToken"] = pagination_token

        response = client.list_users(**params)
        return response.get("Users", [])
    except Exception as e:
        return f"Error listing users: {str(e)}"


async def serve(
    user_pool_id: str,
    profile: str | None = "default",
    region: str | None = "us-east-1",
) -> None:
    logger = logging.getLogger(__name__)
    logger.info("Starting MCP server")

    if not profile:
        profile = "default"
    if not region:
        region = "us-east-1"
    if not user_pool_id:
        logger.error("User pool ID is required")
        return

    cognito_client = boto3.Session(profile_name=profile).client("cognito-idp", region_name=region)

    server = Server("mcp-cognito")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List all tools."""
        return [
            Tool(
                name=CognitoTools.LIST_USER_POOLS.value,
                description="List all user pools",
                input_schema=CognitoListUserPools.model_json_schema(),
            ),
            Tool(
                name=CognitoTools.LIST_IDENTITY_PROVIDERS.value,
                description="List all identity providers for the user pool",
                input_schema=CognitoListIdentityProviders.model_json_schema(),
            ),
            Tool(
                name=CognitoTools.LIST_USERS.value,
                description="List all users in the user pool with optional filtering",
                input_schema=CognitoListUsers.model_json_schema(),
            ),
            Tool(
                name=CognitoTools.GET_USER.value,
                description="Get user details by UUID or email",
                input_schema=CognitoGetUser.model_json_schema(),
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == CognitoTools.LIST_USER_POOLS.value:
            return list_user_pools(cognito_client, arguments)
        elif name == CognitoTools.LIST_IDENTITY_PROVIDERS.value:
            return list_identity_providers(cognito_client, user_pool_id, arguments.get("limit"))
        elif name == CognitoTools.LIST_USERS.value:
            return list_users(
                cognito_client,
                user_pool_id,
                arguments.get("filter_type"),
                arguments.get("attribute_name"),
                arguments.get("pagination_token"),
                arguments.get("limit"),
            )
        elif name == CognitoTools.GET_USER.value:
            for key in ["username", "sub", "email", "id"]:
                if arguments.get(key):
                    return get_user(cognito_client, user_pool_id, arguments.get(key))
            return TextContent(text="No valid identifier provided")

    options = server.create_initialization_options()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
