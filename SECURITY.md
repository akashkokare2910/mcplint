# Security Policy

## Reporting a vulnerability

Please report security vulnerabilities privately via GitHub's
["Report a vulnerability"](https://github.com/akashkokare2910/mcplint/security/advisories/new)
flow rather than opening a public issue. We aim to acknowledge reports
within 5 business days.

## Threat model: MCP servers are untrusted code

**Running `mcplint inspect`, `snapshot`, `scan --server`, `benchmark`, or
`compare` against an MCP server executes that server's code on your
machine.** The `--server "python server.py"` (or any stdio command) is
spawned as a real subprocess with your user's privileges. MCPLint does not
sandbox, containerize, or otherwise restrict what that process can do. This
is the same as running `python server.py` directly yourself.

Only point MCPLint at MCP servers you trust, the same way you'd only run
`pip install` or `npm install` scripts you trust. In CI, this means: only
run `mcplint scan --server ...` against the server you're building in that
same pipeline, not against arbitrary third-party servers.

## HTTP transport (planned)

MCPLint's stdio transport is implemented; HTTP transport is not yet built.
When it is, it will:

- enforce a connection timeout,
- enforce a response-size limit,
- redact `Authorization`/`Cookie`/other auth-bearing headers from any logs,
- never persist secrets (API keys, tokens) to disk,
- not follow redirects to a different origin by default.

## Secrets

MCPLint never asks for or stores your MCP server's credentials. Benchmark
provider API keys (`ANTHROPIC_API_KEY`, etc.) are read from environment
variables by the underlying SDK (`anthropic`, `openai`) and are never logged,
written to snapshot/report files, or transmitted anywhere by MCPLint itself.

## Scope

MCPLint is a local CLI tool, not a hosted service. There is no MCPLint
server that executes arbitrary MCP server commands on anyone's behalf. If
you integrate MCPLint into your own hosted service, you are responsible for
sandboxing the MCP servers it inspects.

## Supported versions

Security fixes are made against the latest released version on PyPI. There
is no long-term-support branch at this stage of the project.
