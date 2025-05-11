# Content Encryption in PyProcessor

This document explains the content encryption feature in PyProcessor, including how it works, how to use it, and security considerations.

## Overview

PyProcessor provides AES-256 encryption for media files to protect sensitive content. The encryption system uses industry-standard cryptographic algorithms and practices to ensure the security of your media files.

## Features

- **AES-256 Encryption**: Uses the Advanced Encryption Standard with 256-bit keys for strong encryption
- **Key Management**: Secure generation, storage, and rotation of encryption keys
- **Password-Based Encryption**: Derive encryption keys from passwords for secure key exchange
- **Metadata Preservation**: Preserves metadata about the original files for proper decryption
- **Transparent Integration**: Seamlessly integrates with the processing pipeline

## How to Use

### Command Line Interface

To enable encryption when processing videos from the command line:

```bash
python -m pyprocessor --input /path/to/input --output /path/to/output --enable-encryption --encrypt-output
```

To use a specific encryption key:

```bash
python -m pyprocessor --input /path/to/input --output /path/to/output --enable-encryption --encrypt-output --encryption-key KEY_ID
```

### Configuration

You can also enable encryption in the configuration file:

```json
{
  "security": {
    "encryption": {
      "enabled": true,
      "encrypt_output": true,
      "key_rotation_interval_days": 90,
      "pbkdf2_iterations": 100000
    }
  }
}
```

## How It Works

1. **Key Generation**: When encryption is enabled, PyProcessor generates a secure random 256-bit key for AES encryption.
2. **Encryption Process**: During the encoding process, output files are encrypted using AES-256 in CBC mode with a random initialization vector (IV).
3. **Metadata Storage**: Encryption metadata (key ID, IV, algorithm) is stored alongside the encrypted files to enable decryption.
4. **Decryption**: When encrypted files are accessed, PyProcessor automatically decrypts them using the stored metadata.

## Security Considerations

- **Key Storage**: Encryption keys are stored in a secure location on disk. Protect this location with appropriate file system permissions.
- **Key Rotation**: Regularly rotate encryption keys to limit the impact of key compromise.
- **Password Strength**: When using password-based encryption, use strong, unique passwords.
- **Metadata Security**: The encryption metadata file contains information needed for decryption. Protect this file with appropriate permissions.

## Technical Details

### Encryption Algorithm

- **Algorithm**: AES-256-CBC (Advanced Encryption Standard with 256-bit keys in Cipher Block Chaining mode)
- **Key Derivation**: PBKDF2-HMAC-SHA256 with 100,000 iterations (for password-based encryption)
- **Padding**: PKCS#7 padding

### File Format

Encrypted files have the following structure:

1. **Metadata Header**: Contains the encryption metadata (key ID, IV, algorithm, etc.)
2. **Encrypted Content**: The encrypted file content

### Key Management

Encryption keys are stored in the `security/keys` directory within the PyProcessor data directory. Each key has:

- **Unique ID**: A UUID that identifies the key
- **Key Data**: The actual encryption key (256 bits)
- **Creation Time**: When the key was created
- **Expiration Time**: When the key expires (if applicable)
- **Description**: A human-readable description of the key
- **Metadata**: Additional information about the key

## Limitations

- Content encryption adds processing overhead, which may impact performance.
- Encrypted files are slightly larger than unencrypted files due to the metadata header.
- Encryption does not protect against all threats. Use additional security measures as needed.

## Best Practices

- Enable encryption only when necessary to minimize performance impact.
- Regularly back up encryption keys to prevent data loss.
- Implement additional security measures (access controls, network security, etc.) for comprehensive protection.
- Consider using a hardware security module (HSM) for key storage in high-security environments.
