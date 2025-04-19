"""
Security utilities for PyProcessor.

This module provides security-related utilities for authentication, authorization,
encryption, and other security features.
"""

from pyprocessor.utils.security.auth_manager import (
    AuthManager, get_auth_manager, User, Role, Permission,
    authenticate, verify_password, hash_password, create_user,
    delete_user, update_user, get_user, list_users, assign_role,
    revoke_role, check_permission
)

from pyprocessor.utils.security.session_manager import (
    SessionManager, get_session_manager, Session, create_session,
    validate_session, invalidate_session, get_session, list_sessions
)

from pyprocessor.utils.security.api_key_manager import (
    ApiKeyManager, get_api_key_manager, ApiKey, create_api_key,
    validate_api_key, revoke_api_key, get_api_key, list_api_keys
)

from pyprocessor.utils.security.audit_logger import (
    AuditLogger, get_audit_logger, log_auth_event, log_access_event,
    log_admin_event, log_security_event
)

from pyprocessor.utils.security.password_policy import (
    PasswordPolicy, get_password_policy, validate_password,
    generate_password
)

from pyprocessor.utils.security.security_manager import (
    SecurityManager, get_security_manager
)

from pyprocessor.utils.security.encryption_manager import (
    EncryptionManager, get_encryption_manager, EncryptionKey
)

from pyprocessor.utils.security.process_sandbox import (
    ProcessSandbox, SandboxPolicy, SandboxedProcess, get_process_sandbox,
    create_sandbox_policy, get_sandbox_policy, get_default_sandbox_policy,
    run_sandboxed_process, wait_sandboxed_process, terminate_sandboxed_process,
    terminate_all_sandboxed_processes, get_sandboxed_process_count,
    get_sandboxed_process_list, cleanup_sandboxed_processes, shutdown_process_sandbox
)
