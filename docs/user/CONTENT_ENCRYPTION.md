# Content Encryption in PyProcessor

PyProcessor includes robust content encryption capabilities to protect sensitive media files. This document explains how to use these features to secure your video content.

## Overview

Content encryption in PyProcessor uses industry-standard AES-256 encryption to protect video files. The encryption system includes:

- **File Encryption**: Encrypt individual video files
- **Key Management**: Secure generation, storage, and rotation of encryption keys
- **Password-Based Encryption**: Protect content with passwords
- **Metadata Protection**: Secure video metadata

## When to Use Encryption

Content encryption is useful in several scenarios:

- **Sensitive Content**: Videos containing confidential or private information
- **Intellectual Property**: Protecting valuable video assets
- **Compliance Requirements**: Meeting regulatory requirements for data protection
- **Distribution Control**: Limiting access to authorized users

## Encryption Features

### AES-256 Encryption

PyProcessor uses the Advanced Encryption Standard (AES) with 256-bit keys, which provides:

- **Strong Security**: Military-grade encryption
- **Performance**: Efficient encryption and decryption
- **Compatibility**: Widely supported standard

### Key Management

The key management system provides:

- **Secure Key Generation**: Cryptographically secure random key generation
- **Key Storage**: Encrypted storage of keys
- **Key Rotation**: Scheduled rotation of encryption keys
- **Key Backup**: Secure backup and recovery of keys

### Password-Based Encryption

For simpler use cases, PyProcessor supports password-based encryption:

- **Password Derivation**: Secure key derivation from passwords
- **Salt Generation**: Unique salt for each encrypted file
- **Iteration Count**: Configurable iteration count for key derivation

## Using Content Encryption

### Command-Line Interface

```bash
# Enable encryption for output files
pyprocessor --input /path/to/videos --output /path/to/output --enable-encryption --encrypt-output

# Use a specific encryption key
pyprocessor --input /path/to/videos --output /path/to/output --enable-encryption --encrypt-output --encryption-key KEY_ID

# Use password-based encryption
pyprocessor --input /path/to/videos --output /path/to/output --enable-encryption --encrypt-output --encryption-password "your-secure-password"
```

### Configuration File

You can also configure encryption in your configuration file or profile:

```json
{
  "security": {
    "encryption": {
      "enabled": true,
      "encrypt_output": true,
      "key_id": "default",
      "password_based": false,
      "password": null,
      "key_rotation_days": 90
    }
  }
}
```

## Key Management

### Generating Keys

PyProcessor automatically generates encryption keys when needed. You can also generate keys manually:

```bash
pyprocessor --generate-encryption-key --key-id "production-key"
```

### Listing Keys

To list available encryption keys:

```bash
pyprocessor --list-encryption-keys
```

### Rotating Keys

To rotate encryption keys:

```bash
pyprocessor --rotate-encryption-key --key-id "production-key"
```

### Backing Up Keys

To back up encryption keys:

```bash
pyprocessor --backup-encryption-keys --output /path/to/backup
```

### Restoring Keys

To restore encryption keys from a backup:

```bash
pyprocessor --restore-encryption-keys --input /path/to/backup
```

## Password-Based Encryption

For simpler use cases, you can use password-based encryption:

```bash
pyprocessor --input /path/to/videos --output /path/to/output --enable-encryption --encrypt-output --encryption-password "your-secure-password"
```

This will:

1. Derive an encryption key from the password
2. Use a unique salt for each file
3. Encrypt the file with the derived key
4. Store the salt with the encrypted file

To decrypt, the same password must be provided.

## Decrypting Content

To decrypt previously encrypted content:

```bash
pyprocessor --decrypt --input /path/to/encrypted --output /path/to/decrypted --encryption-key KEY_ID
```

Or with a password:

```bash
pyprocessor --decrypt --input /path/to/encrypted --output /path/to/decrypted --encryption-password "your-secure-password"
```

## Security Considerations

### Key Storage

Encryption keys are stored in the `pyprocessor/security/keys/` directory. This directory is protected with:

- **File System Permissions**: Restricted to the current user
- **Key Encryption**: Keys are themselves encrypted
- **Master Key**: Protected by system-specific security mechanisms

### Password Security

When using password-based encryption:

- **Use Strong Passwords**: At least 12 characters with a mix of character types
- **Unique Passwords**: Use different passwords for different content
- **Secure Transmission**: Never transmit passwords in plain text
- **Password Rotation**: Change passwords periodically

### System Security

The overall security of your encrypted content depends on:

- **System Security**: Keep your operating system and PyProcessor updated
- **Physical Security**: Protect physical access to your system
- **User Account Security**: Use strong passwords and multi-factor authentication
- **Network Security**: Use secure connections (HTTPS, SSH, etc.)

## Advanced Configuration

### Encryption Algorithm Configuration

Advanced users can configure encryption parameters:

```json
{
  "security": {
    "encryption": {
      "algorithm": "AES",
      "key_size": 256,
      "mode": "GCM",
      "kdf_algorithm": "PBKDF2",
      "kdf_iterations": 100000,
      "kdf_hash": "SHA-256"
    }
  }
}
```

### Custom Key Storage

You can configure a custom location for key storage:

```json
{
  "security": {
    "encryption": {
      "key_storage_path": "/path/to/secure/storage"
    }
  }
}
```

### Integration with Hardware Security Modules (HSMs)

For enterprise users, PyProcessor can integrate with Hardware Security Modules:

```json
{
  "security": {
    "encryption": {
      "use_hsm": true,
      "hsm_provider": "pkcs11",
      "hsm_library_path": "/path/to/hsm/library.so",
      "hsm_slot_id": 0,
      "hsm_pin": "PIN"
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Key Not Found**: Ensure the specified key ID exists
2. **Permission Denied**: Check file system permissions
3. **Incorrect Password**: Verify the password is correct
4. **Corrupted File**: The encrypted file may be corrupted
5. **Memory Error**: Encryption of large files may require more memory

### Diagnostic Commands

```bash
# Check encryption system status
pyprocessor --check-encryption-system

# Verify a specific key
pyprocessor --verify-encryption-key --key-id "production-key"

# Test encryption and decryption
pyprocessor --test-encryption --key-id "production-key"
```

## Best Practices

1. **Regular Key Rotation**: Rotate encryption keys regularly
2. **Backup Keys**: Maintain secure backups of encryption keys
3. **Strong Passwords**: Use strong, unique passwords
4. **Limit Access**: Restrict access to encryption keys and passwords
5. **Test Recovery**: Regularly test decryption to ensure recovery is possible
6. **Document Procedures**: Document encryption and key management procedures
7. **Audit Usage**: Monitor and audit encryption key usage

## Further Reading

- [AES Encryption Standard](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.197.pdf)
- [NIST Recommendations for Key Management](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-57pt1r5.pdf)
- [Password-Based Cryptography](https://tools.ietf.org/html/rfc8018)
- [Galois/Counter Mode (GCM)](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf)
