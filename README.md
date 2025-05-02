# mcp-server-cognito: A Cognito MCP server

## Overview

A Model Context Protocol server for AWS Cognito interaction and automation. This server provides tools to list and get AWS Cognito identity providers, users and user pools via Large Language Models.

Please note that mcp-server-cognito is currently in early development. The functionality and available tools are subject to change and expansion as we continue to develop and improve the server.

### Tools

1. `cognito_list_user_pools`
   - Lists all user pools
   - Input:
     - None required
   - Returns: List of user pools with IDs and names

2. `cognito_list_identity_providers`
   - Lists all identity providers for the user pool
   - Input:
     - `user_pool_id` (string): ID of the user pool
   - Returns: List of identity providers with names and types

3. `cognito_list_users`
   - Lists all users in the user pool with optional filtering
   - Inputs:
     - `filter_string` (string): Filter expression for users
     - `pagination_token` (string): Token for pagination
     - `limit` (integer, optional): Maximum number of users to return (default: 60)
   - Returns: List of users with details

4. `cognito_get_user`
   - Gets user details by UUID or email
   - Input:
     - `username` (string): Username, UUID, email or other identifier for the user
   - Returns: Detailed user information

## Installation

### Using uv (recommended)

When using [`uv`](https://docs.astral.sh/uv/) no specific installation is needed. We will
use [`uvx`](https://docs.astral.sh/uv/guides/tools/) to directly run *mcp-server-cognito*.


After installation, you can run it as a script using:

```
python -m mcp_server_cognito
```

## Configuration

### Usage with Claude Desktop

Add this to your `claude_desktop_config.json`:


<details>
<summary>Using docker</summary>

* Note: replace '/Users/username' with the a path that you want to be accessible by this tool

```json
"mcpServers": {
  "cognito": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v",
        "/Users/username/.aws:/root/.aws",
        "mcp/cognito",
        "--profile",
        "your-profile-name",
        "--region",
        "your-region",
        "--user-pool-id",
        "your-user-pool-id"
      ]
    }   
}
```
</details>


## Build

Docker build:

```bash
cd src/cognito
docker build -t mcp/cognito .
```
