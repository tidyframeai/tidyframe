#!/usr/bin/env python3
"""
Secure Password Hasher for TidyFrame Site Password

This utility provides secure bcrypt password hashing for the SITE_PASSWORD
environment variable used in pre-launch site protection.
"""

import bcrypt
import base64
import getpass
import secrets
import argparse
import sys


def hash_password(password: str, rounds: int = 12) -> str:
    """
    Hash a password using bcrypt with base64 encoding.
    
    Args:
        password: Plain text password to hash
        rounds: bcrypt rounds (cost factor) - higher is more secure but slower
        
    Returns:
        Base64-encoded bcrypt hash suitable for environment variables
    """
    # Convert password to bytes
    password_bytes = password.encode('utf-8')
    
    # Generate salt and hash
    salt = bcrypt.gensalt(rounds=rounds)
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Base64 encode for storage in environment variables
    b64_hash = base64.b64encode(hashed).decode('utf-8')
    
    return b64_hash


def verify_password(password: str, b64_hash: str) -> bool:
    """
    Verify a password against a base64-encoded bcrypt hash.
    
    Args:
        password: Plain text password to verify
        b64_hash: Base64-encoded bcrypt hash
        
    Returns:
        True if password matches hash
    """
    try:
        # Decode the base64 hash
        hashed = base64.b64decode(b64_hash.encode('utf-8'))
        password_bytes = password.encode('utf-8')
        
        # Verify using bcrypt
        return bcrypt.checkpw(password_bytes, hashed)
    except Exception:
        return False


def generate_secure_password(length: int = 16) -> str:
    """
    Generate a cryptographically secure password.
    
    Args:
        length: Desired password length
        
    Returns:
        Secure random password
    """
    # Character sets for password generation
    uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    lowercase = 'abcdefghijklmnopqrstuvwxyz'
    digits = '0123456789'
    special = '!@#$%^&*()_+-=[]{}|;:,.<>?'
    
    # Ensure password contains at least one character from each set
    password = [
        secrets.choice(uppercase),
        secrets.choice(lowercase),
        secrets.choice(digits),
        secrets.choice(special)
    ]
    
    # Fill remaining positions with random characters from all sets
    all_chars = uppercase + lowercase + digits + special
    for _ in range(length - 4):
        password.append(secrets.choice(all_chars))
    
    # Shuffle the password list
    secrets.SystemRandom().shuffle(password)
    
    return ''.join(password)


def main():
    """CLI interface for password hashing."""
    parser = argparse.ArgumentParser(
        description='TidyFrame Secure Password Hasher',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Hash a password interactively
  python password_hasher.py hash
  
  # Hash a specific password
  python password_hasher.py hash --password "MySecurePassword123!"
  
  # Generate and hash a secure password
  python password_hasher.py generate --length 20
  
  # Verify a password against a hash
  python password_hasher.py verify --hash "JDJiJDEyJG81L21ic0ZPMWtUbk9oU1VrRXZ4SnVWb1VjMUYwbGlWZmFGeklYdVRNZ2xyRUlKL2Y4T0RT"
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Hash command
    hash_parser = subparsers.add_parser('hash', help='Hash a password')
    hash_parser.add_argument('--password', help='Password to hash (will prompt if not provided)')
    hash_parser.add_argument('--rounds', type=int, default=12, 
                           help='bcrypt rounds (default: 12, higher = more secure but slower)')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate and hash a secure password')
    gen_parser.add_argument('--length', type=int, default=16, help='Password length (default: 16)')
    gen_parser.add_argument('--rounds', type=int, default=12, help='bcrypt rounds (default: 12)')
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify a password against a hash')
    verify_parser.add_argument('--password', help='Password to verify (will prompt if not provided)')
    verify_parser.add_argument('--hash', required=True, help='Base64-encoded bcrypt hash')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'hash':
            # Get password
            if args.password:
                password = args.password
            else:
                password = getpass.getpass("Enter password to hash: ")
                
            if not password:\n                print("❌ Password cannot be empty")\n                sys.exit(1)\n                \n            # Hash the password\n            b64_hash = hash_password(password, args.rounds)\n            \n            print(f"\\n✅ Password hashed successfully!")\n            print(f\"Rounds: {args.rounds}\")\n            print(f\"Hash: {b64_hash}\")\n            print(f\"\\nAdd this to your .env file:\")\n            print(f\"SITE_PASSWORD_HASH={b64_hash}\")\n            \n        elif args.command == 'generate':\n            # Generate secure password\n            password = generate_secure_password(args.length)\n            b64_hash = hash_password(password, args.rounds)\n            \n            print(f\"\\n✅ Secure password generated!\")\n            print(f\"Password: {password}\")\n            print(f\"Length: {len(password)}\")\n            print(f\"Rounds: {args.rounds}\")\n            print(f\"Hash: {b64_hash}\")\n            print(f\"\\n🔒 IMPORTANT: Save the password securely!\")\n            print(f\"\\nAdd this to your .env file:\")\n            print(f\"SITE_PASSWORD_HASH={b64_hash}\")\n            \n        elif args.command == 'verify':\n            # Get password\n            if args.password:\n                password = args.password\n            else:\n                password = getpass.getpass(\"Enter password to verify: \")\n                \n            # Verify password\n            is_valid = verify_password(password, args.hash)\n            \n            if is_valid:\n                print(\"✅ Password verification successful!\")\n                sys.exit(0)\n            else:\n                print(\"❌ Password verification failed!\")\n                sys.exit(1)\n                \n    except KeyboardInterrupt:\n        print(\"\\n\\n👋 Cancelled by user\")\n        sys.exit(0)\n    except Exception as e:\n        print(f\"\\n💥 Error: {str(e)}\")\n        sys.exit(1)\n\n\nif __name__ == '__main__':\n    main()"