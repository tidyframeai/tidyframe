"""
Environment Variable Validation Module for TidyFrame

This module provides comprehensive validation for all environment variables
to ensure secure and proper configuration before application startup.
"""

import os
import re
import sys
import base64
import bcrypt
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse
import structlog

logger = structlog.get_logger()


class EnvironmentValidationError(Exception):
    """Custom exception for environment validation errors."""
    pass


class EnvironmentValidator:
    """
    Comprehensive environment variable validator for TidyFrame.
    
    Validates:
    - Required variables are present
    - Secrets meet security requirements  
    - URLs are properly formatted
    - Database connections are valid
    - API keys have correct format
    - Security settings are appropriate for environment
    """
    
    def __init__(self, environment: str = None):
        """
        Initialize the validator.
        
        Args:
            environment: The target environment (development, staging, production)
        """
        self.environment = environment or os.getenv('ENVIRONMENT', 'development')
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.is_production = self.environment == 'production'
        
    def validate_all(self) -> Dict[str, Any]:
        """
        Run all validation checks.
        
        Returns:
            Dict containing validation results
            
        Raises:
            EnvironmentValidationError: If critical validation errors are found
        """
        logger.info("Starting environment validation", environment=self.environment)
        
        # Core validation checks
        self._validate_core_config()
        self._validate_secrets()
        self._validate_database_config()
        self._validate_redis_config()
        self._validate_external_apis()
        self._validate_security_settings()
        self._validate_file_settings()
        self._validate_urls()
        self._validate_production_requirements()
        
        # Compile results
        results = {
            'environment': self.environment,
            'valid': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'checks_passed': self._count_checks_passed(),
            'security_score': self._calculate_security_score()
        }
        
        # Log results
        if self.errors:
            logger.error(
                "Environment validation failed",
                environment=self.environment,
                errors=len(self.errors),
                warnings=len(self.warnings)
            )
            if self.is_production:
                raise EnvironmentValidationError(
                    f"Production environment validation failed with {len(self.errors)} errors"
                )
        else:
            logger.info(
                "Environment validation passed",
                environment=self.environment,
                warnings=len(self.warnings),
                security_score=results['security_score']
            )
            
        return results
    
    def _validate_core_config(self):
        """Validate core application configuration."""
        required_vars = [
            'ENVIRONMENT',
            'PROJECT_NAME', 
            'SECRET_KEY',
            'JWT_SECRET_KEY',
            'JWT_REFRESH_SECRET_KEY'
        ]
        
        for var in required_vars:
            if not self._check_required(var):
                self.errors.append(f"Missing required variable: {var}")
                
        # Validate environment value
        valid_environments = ['development', 'staging', 'production']
        env = os.getenv('ENVIRONMENT', '').lower()
        if env not in valid_environments:
            self.errors.append(f"ENVIRONMENT must be one of: {', '.join(valid_environments)}")
            
        # Validate JWT algorithm
        jwt_algorithm = os.getenv('JWT_ALGORITHM', 'HS256')
        if jwt_algorithm not in ['HS256', 'HS384', 'HS512']:
            self.errors.append(f"JWT_ALGORITHM must be HS256, HS384, or HS512, got: {jwt_algorithm}")
    
    def _validate_secrets(self):
        """Validate cryptographic secrets and their strength."""
        secrets_to_check = {
            'SECRET_KEY': {'min_length': 32, 'critical': True},
            'JWT_SECRET_KEY': {'min_length': 32, 'critical': True},
            'JWT_REFRESH_SECRET_KEY': {'min_length': 32, 'critical': True},
            'POSTGRES_PASSWORD': {'min_length': 16, 'critical': True},
            'REDIS_PASSWORD': {'min_length': 16, 'critical': True},
        }
        
        for secret_name, config in secrets_to_check.items():
            secret_value = os.getenv(secret_name)
            
            if not secret_value:
                if config['critical']:
                    self.errors.append(f"Missing critical secret: {secret_name}")
                continue
                
            # Check for default/weak values
            if self._is_default_value(secret_value):
                if self.is_production:
                    self.errors.append(f"{secret_name} uses default/weak value - must be changed for production")
                else:
                    self.warnings.append(f"{secret_name} uses default value - change for production")
                    
            # Check minimum length
            if len(secret_value) < config['min_length']:
                self.errors.append(f"{secret_name} must be at least {config['min_length']} characters long")
                
            # Check entropy/randomness
            if not self._has_sufficient_entropy(secret_value):
                self.warnings.append(f"{secret_name} has low entropy - consider using a cryptographically secure generator")
    
    def _validate_database_config(self):
        """Validate database configuration."""
        database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            self.errors.append("Missing DATABASE_URL")
            return
            
        try:
            parsed = urlparse(database_url)
            
            # Check scheme
            if parsed.scheme not in ['postgresql', 'postgresql+asyncpg']:
                self.errors.append(f"DATABASE_URL must use postgresql:// or postgresql+asyncpg:// scheme")
                
            # Check for password in URL
            if not parsed.password:
                self.errors.append("DATABASE_URL must contain password")
            elif self._is_default_value(parsed.password):
                if self.is_production:
                    self.errors.append("DATABASE_URL contains default password - must be changed for production")
                else:
                    self.warnings.append("DATABASE_URL contains default password")
                    
            # Check host
            if not parsed.hostname:
                self.errors.append("DATABASE_URL must specify hostname")
                
        except Exception as e:
            self.errors.append(f"Invalid DATABASE_URL format: {str(e)}")
            
        # Validate connection pool settings
        pool_size = self._get_int_env('DB_POOL_SIZE', 10)
        max_overflow = self._get_int_env('DB_MAX_OVERFLOW', 20)
        
        if pool_size < 1:
            self.errors.append("DB_POOL_SIZE must be at least 1")
        if max_overflow < 0:
            self.errors.append("DB_MAX_OVERFLOW must be non-negative")
            
        if self.is_production and pool_size < 10:
            self.warnings.append("DB_POOL_SIZE should be at least 10 for production")
    
    def _validate_redis_config(self):
        """Validate Redis configuration."""
        redis_url = os.getenv('REDIS_URL')
        
        if not redis_url:
            self.errors.append("Missing REDIS_URL")
            return
            
        try:
            parsed = urlparse(redis_url)
            
            if parsed.scheme != 'redis':
                self.errors.append("REDIS_URL must use redis:// scheme")
                
            # Check for password
            if not parsed.password:
                if self.is_production:
                    self.errors.append("REDIS_URL must contain password for production")
                else:
                    self.warnings.append("REDIS_URL should contain password")
            elif self._is_default_value(parsed.password):
                if self.is_production:
                    self.errors.append("REDIS_URL contains default password - must be changed for production")
                    
        except Exception as e:
            self.errors.append(f"Invalid REDIS_URL format: {str(e)}")
    
    def _validate_external_apis(self):
        """Validate external API configurations."""
        # Gemini API
        gemini_key = os.getenv('GEMINI_API_KEY')
        if not gemini_key or gemini_key.startswith('REPLACE_'):
            if self.is_production:
                self.errors.append("GEMINI_API_KEY must be set for production")
            else:
                self.warnings.append("GEMINI_API_KEY not configured")
                
        # Stripe API
        stripe_secret = os.getenv('STRIPE_SECRET_KEY')
        if stripe_secret:
            if self.is_production and not stripe_secret.startswith('sk_live_'):
                self.errors.append("STRIPE_SECRET_KEY must use live key (sk_live_) for production")
            elif not self.is_production and not stripe_secret.startswith(('sk_test_', 'sk_live_')):
                self.warnings.append("STRIPE_SECRET_KEY should start with sk_test_ or sk_live_")
        elif self.is_production:
            self.errors.append("STRIPE_SECRET_KEY required for production")
            
        # Google OAuth
        google_client_id = os.getenv('GOOGLE_CLIENT_ID')
        google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        
        if google_client_id and not google_client_id.endswith('.googleusercontent.com'):
            self.warnings.append("GOOGLE_CLIENT_ID should end with .googleusercontent.com")
            
        if google_client_id and not google_client_secret:
            self.errors.append("GOOGLE_CLIENT_SECRET required when GOOGLE_CLIENT_ID is set")
    
    def _validate_security_settings(self):
        """Validate security-related settings."""
        # Password requirements
        min_length = self._get_int_env('PASSWORD_MIN_LENGTH', 8)
        if min_length < 8:
            self.warnings.append("PASSWORD_MIN_LENGTH should be at least 8")
        if self.is_production and min_length < 12:
            self.warnings.append("PASSWORD_MIN_LENGTH should be at least 12 for production")
            
        # Session security
        if self.is_production:
            if not self._get_bool_env('SESSION_COOKIE_SECURE', False):
                self.errors.append("SESSION_COOKIE_SECURE must be true for production")
            if not self._get_bool_env('SESSION_COOKIE_HTTPONLY', True):
                self.errors.append("SESSION_COOKIE_HTTPONLY must be true for production")
            if not self._get_bool_env('CSRF_COOKIE_SECURE', False):
                self.errors.append("CSRF_COOKIE_SECURE must be true for production")
                
        # Rate limiting
        if not self._get_bool_env('ENABLE_RATE_LIMITING', True) and self.is_production:
            self.warnings.append("Rate limiting should be enabled for production")
            
        # Site password
        if self._get_bool_env('ENABLE_SITE_PASSWORD', False):
            site_password_hash = os.getenv('SITE_PASSWORD_HASH')
            if not site_password_hash:
                self.errors.append("SITE_PASSWORD_HASH required when ENABLE_SITE_PASSWORD is true")
            else:
                # Validate bcrypt hash format
                try:
                    # Decode base64 and check if it's a valid bcrypt hash
                    decoded = base64.b64decode(site_password_hash)
                    if not decoded.startswith(b'$2b$'):
                        self.errors.append("SITE_PASSWORD_HASH must be a bcrypt hash")
                except Exception:
                    self.errors.append("SITE_PASSWORD_HASH must be base64-encoded bcrypt hash")
    
    def _validate_file_settings(self):
        """Validate file processing settings."""
        max_file_size = self._get_int_env('MAX_FILE_SIZE_MB', 200)
        if max_file_size < 1:
            self.errors.append("MAX_FILE_SIZE_MB must be at least 1")
        if max_file_size > 1000:
            self.warnings.append("MAX_FILE_SIZE_MB is very large - consider security implications")
            
        # Check upload directories exist or can be created
        upload_dir = os.getenv('UPLOAD_DIR', '/app/backend/uploads')
        results_dir = os.getenv('RESULTS_DIR', '/app/backend/results')
        
        for dir_path, dir_name in [(upload_dir, 'UPLOAD_DIR'), (results_dir, 'RESULTS_DIR')]:
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    self.warnings.append(f"Created missing directory: {dir_path}")
                except Exception as e:
                    self.errors.append(f"Cannot create {dir_name} ({dir_path}): {str(e)}")
    
    def _validate_urls(self):
        """Validate URL configurations."""
        urls_to_check = {
            'API_URL': True,
            'FRONTEND_URL': True,
            'GOOGLE_OAUTH_REDIRECT_URI': False
        }
        
        for url_var, required in urls_to_check.items():
            url = os.getenv(url_var)
            
            if not url and required:
                self.errors.append(f"Missing required URL: {url_var}")
                continue
                
            if url:
                try:
                    parsed = urlparse(url)
                    if not parsed.scheme or not parsed.netloc:
                        self.errors.append(f"Invalid URL format for {url_var}: {url}")
                    elif self.is_production and parsed.scheme != 'https':
                        self.errors.append(f"{url_var} must use HTTPS for production: {url}")
                except Exception as e:
                    self.errors.append(f"Invalid URL for {url_var}: {str(e)}")
    
    def _validate_production_requirements(self):
        """Validate production-specific requirements."""
        if not self.is_production:
            return
            
        # SSL/TLS requirements
        ssl_cert_path = os.getenv('SSL_CERT_PATH')
        ssl_key_path = os.getenv('SSL_KEY_PATH')
        
        if ssl_cert_path and not os.path.exists(ssl_cert_path):
            self.errors.append(f"SSL certificate not found: {ssl_cert_path}")
        if ssl_key_path and not os.path.exists(ssl_key_path):
            self.errors.append(f"SSL key not found: {ssl_key_path}")
            
        # Production-only settings
        if os.getenv('DEBUG', '').lower() == 'true':
            self.errors.append("DEBUG must be false for production")
            
        # Monitoring requirements
        if not os.getenv('SENTRY_DSN'):
            self.warnings.append("SENTRY_DSN not configured - error tracking recommended for production")
            
        # Backup configuration
        if not os.getenv('AWS_ACCESS_KEY_ID') or not os.getenv('BACKUP_S3_BUCKET'):
            self.warnings.append("Backup configuration incomplete - AWS S3 backup recommended for production")
    
    def _check_required(self, var_name: str) -> bool:
        """Check if a required variable is present and non-empty."""
        value = os.getenv(var_name)
        return bool(value and value.strip())
    
    def _is_default_value(self, value: str) -> bool:
        """Check if a value appears to be a default/placeholder value."""
        default_indicators = [
            'replace_with',
            'change_me',
            'your_',
            'secret',
            'password',
            'key',
            'placeholder',
            'development',
            'test',
            'default'
        ]
        
        value_lower = value.lower()
        return any(indicator in value_lower for indicator in default_indicators)
    
    def _has_sufficient_entropy(self, value: str) -> bool:
        """Check if a value has sufficient entropy/randomness."""
        if len(value) < 16:
            return False
            
        # Check for repeated patterns
        if len(set(value)) < len(value) * 0.7:
            return False
            
        # Check for dictionary words
        common_words = ['password', 'secret', 'key', 'admin', 'user', 'test']
        if any(word in value.lower() for word in common_words):
            return False
            
        return True
    
    def _get_int_env(self, var_name: str, default: int) -> int:
        """Get integer environment variable with default."""
        try:
            return int(os.getenv(var_name, str(default)))
        except (ValueError, TypeError):
            return default
    
    def _get_bool_env(self, var_name: str, default: bool) -> bool:
        """Get boolean environment variable with default."""
        value = os.getenv(var_name, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def _count_checks_passed(self) -> int:
        """Count the number of validation checks that passed."""
        # This is a simplified count - in practice, you'd track individual checks
        return max(0, 50 - len(self.errors) - len(self.warnings))
    
    def _calculate_security_score(self) -> int:
        """Calculate a security score based on validation results."""
        base_score = 100
        
        # Deduct points for errors and warnings
        score = base_score - (len(self.errors) * 10) - (len(self.warnings) * 2)
        
        # Bonus points for production-ready configuration
        if self.is_production and len(self.errors) == 0:
            score += 10
            
        return max(0, min(100, score))


def validate_environment(environment: str = None) -> Dict[str, Any]:
    """
    Validate environment configuration.
    
    Args:
        environment: Target environment (development, staging, production)
        
    Returns:
        Validation results dictionary
        
    Raises:
        EnvironmentValidationError: If validation fails for production
    """
    validator = EnvironmentValidator(environment)
    return validator.validate_all()


def main():
    """CLI entry point for environment validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate TidyFrame environment configuration')
    parser.add_argument('--env', choices=['development', 'staging', 'production'], 
                       help='Target environment')
    parser.add_argument('--strict', action='store_true', 
                       help='Treat warnings as errors')
    
    args = parser.parse_args()
    
    try:
        results = validate_environment(args.env)
        
        print(f"\n🔍 Environment Validation Results")
        print(f"Environment: {results['environment']}")
        print(f"Security Score: {results['security_score']}/100")
        
        if results['errors']:
            print(f"\n❌ Errors ({len(results['errors'])}):")
            for error in results['errors']:
                print(f"  • {error}")
                
        if results['warnings']:
            print(f"\n⚠️  Warnings ({len(results['warnings'])}):")
            for warning in results['warnings']:
                print(f"  • {warning}")
                
        if results['valid'] and not (args.strict and results['warnings']):
            print(f"\n✅ Environment validation passed!")
            sys.exit(0)
        else:
            print(f"\n❌ Environment validation failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Validation error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()