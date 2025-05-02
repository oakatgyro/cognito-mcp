import boto3
import logging
from typing import Any
from mcp import Tool
from mcp.types import TextContent
from mcp.server import Server
from mcp.server.stdio import stdio_server
from enum import Enum
from pydantic import BaseModel
from mypy_boto3_cognito_idp import CognitoIdentityProviderClient


DEFAULT_LIMIT = 60

class CognitoTools(str, Enum):
    LIST_USER_POOLS = "cognito_list_user_pools"
    LIST_IDENTITY_PROVIDERS = "cognito_list_identity_providers"
    LIST_USERS = "cognito_list_users"
    GET_USER = "cognito_get_user"


class CognitoListUserPools(BaseModel):
    pass


class CognitoListIdentityProviders(BaseModel):
    user_pool_id: str


class CognitoListUsers(BaseModel):
    filter_string: str
    pagination_token: str
    limit: int = DEFAULT_LIMIT


class CognitoGetUser(BaseModel):
    username: str


def list_user_pools(client) -> str:
    """List all user pools."""

    try:
        response = client.list_user_pools(MaxResults=60)
        return "\n".join([f"{pool['Id']}: {pool['Name']}" for pool in response.get("UserPools", [])])
    except Exception as e:
        return f"Error listing user pools: {str(e)}"


def list_identity_providers(client: CognitoIdentityProviderClient, user_pool_id: str) -> str:
    """List all identity providers for the user pool."""

    try:
        response = client.list_identity_providers(UserPoolId=user_pool_id)
        return "\n\n".join([f"'ProviderName': {provider['ProviderName']}, 'ProviderType': {provider['ProviderType']}" for provider in response.get("Providers", [])])
    except Exception as e:
        return f"Error listing identity providers: {str(e)}"


def get_user(client: CognitoIdentityProviderClient, user_pool_id: str, identifier: str) -> str:
    """Get user details by UUID or email."""

    try:
        # Try to get user by UUID first
        try:
            response = client.admin_get_user(UserPoolId=user_pool_id, Username=identifier)
            user_attributes = [f"{attribute['Name']}: {attribute['Value']}" for attribute in response.get("UserAttributes", [])]
            return f"""
Username: {response.get("Username")}
UserAttributes: {'\n'.join(user_attributes)}
UserCreateDate: {response.get("UserCreateDate")}
UserLastModifiedDate: {response.get("UserLastModifiedDate")}
Enabled: {response.get("Enabled")}
UserStatus: {response.get("UserStatus")}
"""
        except client.exceptions.UserNotFoundException:
            # If not found by UUID, try to find by email
            return "User not found"
        except client.exceptions.ResourceNotFoundException as e:
            return f"Error getting user: {str(e)}"
    except Exception as e:
        return f"Error getting user: {str(e)}"


def list_users(
    client: CognitoIdentityProviderClient,
    user_pool_id: str,
    filter_string: str,
    pagination_token: str,
) -> str:
    """List users with optional filtering."""

    try:
        params = {"UserPoolId": user_pool_id, "Limit": DEFAULT_LIMIT}

        if filter_string:
            params["Filter"] = filter_string

        if pagination_token:
            params["PaginationToken"] = pagination_token

        response = client.list_users(**params)
        users = response.get("Users", [])
        # TODO: Handle pagination

        res = ""
        for user in users:
            _id = user.get("Username")
            user_details = [f"{key}: {value}" for key, value in user.items() if key != "UserAttributes"]
            res += f"{_id}\n{'\n'.join(user_details)}\n\n"
        return res
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

    server: Server[Any] = Server("mcp-cognito")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List all tools."""
        return [
            Tool(
                name=CognitoTools.LIST_USER_POOLS.value,
                description="List all user pools",
                inputSchema=CognitoListUserPools.model_json_schema(),
            ),
            Tool(
                name=CognitoTools.LIST_IDENTITY_PROVIDERS.value,
                description="List all identity providers for the user pool",
                inputSchema=CognitoListIdentityProviders.model_json_schema(),
            ),
            Tool(
                name=CognitoTools.LIST_USERS.value,
                description="List all users in the user pool with optional filtering",
                inputSchema=CognitoListUsers.model_json_schema(),
            ),
            Tool(
                name=CognitoTools.GET_USER.value,
                description="Get user details by UUID or email",
                inputSchema=CognitoGetUser.model_json_schema(),
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name == CognitoTools.LIST_USER_POOLS.value:
            result = list_user_pools(cognito_client)
            return [TextContent(text=str(result), type="text")]
        elif name == CognitoTools.LIST_IDENTITY_PROVIDERS.value:
            result = list_identity_providers(cognito_client, arguments.get("user_pool_id", user_pool_id))
            return [TextContent(text=str(result), type="text")]
        elif name == CognitoTools.LIST_USERS.value:
            result = list_users(
                cognito_client,
                arguments.get("user_pool_id", user_pool_id),
                arguments.get("filter_string", ""),
                arguments.get("pagination_token", ""),
            )
            return [TextContent(text=str(result), type="text")]
        elif name == CognitoTools.GET_USER.value:
            for key in ["username", "sub", "email", "id"]:
                if arguments.get(key):
                    result = get_user(cognito_client, arguments.get("user_pool_id", user_pool_id), str(arguments.get(key)))
                    return [TextContent(text=str(result), type="text")]
            return [TextContent(text="No valid identifier provided", type="text")]
        
        # Default case - unknown tool
        return [TextContent(text=f"Unknown tool: {name}", type="text")]

    options = server.create_initialization_options()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
