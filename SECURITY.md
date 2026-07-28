# Security Policy

## Report privately

Do not open a public issue for exposed credentials, private personal information, unsafe command execution, arbitrary file writes, workflow compromise, or material crossing the repository's legal/private-data boundary.

Contact the repository owner through the email listed on the GitHub profile and include the affected path, impact, and reproduction steps.

## Public runtime guarantees

The fixture runtime uses the Python standard library, makes no network requests, executes no shell commands, writes only to an explicitly supplied output path, uses deterministic inputs, and emits a SHA-256 content receipt.

The hash is an integrity address, not an authenticity signature.

## Out of scope

The workspace runner composes external repositories and optional local services. Evaluate it as an integration environment, not as the isolated public fixture runtime.
