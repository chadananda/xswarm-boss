# Security Policy

## Reporting Security Vulnerabilities

**Do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: security@xswarm.dev

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Response Timeline

- **Initial response**: Within 48 hours
- **Status update**: Within 7 days
- **Fix timeline**: Depends on severity

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |

## Security Features

xSwarm-boss implements multiple security layers:

- **Secret Detection** - Pattern-based detection of API keys, tokens, passwords
- **Memory Purging** - Automatic scrubbing of sensitive data
- **MCP Isolation** - Secrets stored in isolated process
- **mTLS** - Encrypted communication between machines
- **Audit Logging** - Tamper-proof security event logs

See [docs/planning/SECURITY.md](docs/planning/SECURITY.md) for complete security documentation.

## Security Best Practices

When using xSwarm-boss:

1. Never commit `.env` files
2. Use the secret detection features
3. Enable memory purging (default: every 60s)
4. Review audit logs regularly
5. Keep xSwarm updated
6. Use mTLS for vassal communication

## Responsible Disclosure

We follow responsible disclosure practices:

1. Report received and acknowledged
2. Issue verified and assessed
3. Fix developed and tested
4. Security advisory published
5. Fix released to users

Thank you for helping keep xSwarm-boss secure!
