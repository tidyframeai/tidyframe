#!/usr/bin/env python3
"""
Secure Password Generator for TidyFrame
Generates cryptographically secure passwords that meet security requirements
"""

import secrets
import string
import re
import argparse
import sys


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Validate password meets security requirements
    Returns (is_valid, list_of_issues)
    """
    issues = []
    
    if len(password) < 12:
        issues.append("Password must be at least 12 characters long")
    
    if not re.search(r'[A-Z]', password):
        issues.append("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        issues.append("Password must contain at least one lowercase letter")
    
    if not re.search(r'[0-9]', password):
        issues.append("Password must contain at least one number")
    
    if not re.search(r'[!@#$%^&*(),.?\":{}|<>]', password):
        issues.append("Password must contain at least one special character")
    
    return len(issues) == 0, issues


def generate_secure_password(length: int = 16, exclude_ambiguous: bool = True) -> str:
    """
    Generate a cryptographically secure password
    
    Args:
        length: Password length (minimum 12)
        exclude_ambiguous: Whether to exclude ambiguous characters (0, O, l, I, etc.)
    """
    if length < 12:
        raise ValueError("Password length must be at least 12 characters")
    
    # Define character sets
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    special = '!@#$%^&*(),.?\":{}|<>'
    
    if exclude_ambiguous:
        # Remove ambiguous characters
        uppercase = uppercase.replace('O', '').replace('I', '')
        lowercase = lowercase.replace('l', '').replace('o', '')
        digits = digits.replace('0', '').replace('1', '')
    
    # Ensure password contains at least one character from each required set
    password_chars = [
        secrets.choice(uppercase),
        secrets.choice(lowercase),
        secrets.choice(digits),
        secrets.choice(special)
    ]
    
    # Fill the rest with random characters from all sets
    all_chars = uppercase + lowercase + digits + special
    for _ in range(length - 4):
        password_chars.append(secrets.choice(all_chars))
    
    # Shuffle the characters to avoid predictable patterns
    secrets.SystemRandom().shuffle(password_chars)
    
    password = ''.join(password_chars)
    
    # Validate the generated password
    is_valid, issues = validate_password_strength(password)
    if not is_valid:
        # Recursively try again if validation fails (rare case)
        return generate_secure_password(length, exclude_ambiguous)
    
    return password


def generate_multiple_passwords(count: int = 3, length: int = 16) -> list[str]:
    """Generate multiple secure passwords for selection"""
    passwords = []
    for _ in range(count):
        passwords.append(generate_secure_password(length))
    return passwords


def main():
    parser = argparse.ArgumentParser(
        description='Generate secure passwords for TidyFrame',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Generate 3 passwords with default length (16)
  %(prog)s --length 20              # Generate longer passwords
  %(prog)s --count 5                # Generate 5 password options
  %(prog)s --validate "MyPassword"  # Validate an existing password
  
Security Requirements:
  - Minimum 12 characters
  - At least one uppercase letter
  - At least one lowercase letter  
  - At least one number
  - At least one special character
        """
    )
    
    parser.add_argument('--length', type=int, default=16,
                       help='Password length (minimum 12, default: 16)')
    parser.add_argument('--count', type=int, default=3,
                       help='Number of passwords to generate (default: 3)')
    parser.add_argument('--validate', type=str,
                       help='Validate an existing password instead of generating new ones')
    parser.add_argument('--no-exclude-ambiguous', action='store_true',
                       help='Include ambiguous characters (0, O, l, I, etc.)')
    
    args = parser.parse_args()
    
    if args.validate:
        # Validate existing password
        is_valid, issues = validate_password_strength(args.validate)
        if is_valid:
            print("✅ Password meets all security requirements")
            sys.exit(0)
        else:
            print("❌ Password does not meet security requirements:")
            for issue in issues:
                print(f"   • {issue}")
            sys.exit(1)
    
    if args.length < 12:
        print("❌ Error: Password length must be at least 12 characters")
        sys.exit(1)
    
    try:
        print(f"🔐 Generating {args.count} secure password(s) ({args.length} characters):")
        print()
        
        passwords = generate_multiple_passwords(
            count=args.count,
            length=args.length
        )
        
        for i, password in enumerate(passwords, 1):
            print(f"Option {i}: {password}")
        
        print()
        print("💡 Tips:")
        print("   • Store passwords securely (password manager recommended)")
        print("   • Never share passwords via unsecured channels")
        print("   • Use different passwords for different services")
        print("   • Consider using the generated passwords in your .env file")
        
    except Exception as e:
        print(f"❌ Error generating passwords: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()