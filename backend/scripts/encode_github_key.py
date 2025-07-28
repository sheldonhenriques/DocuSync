#!/usr/bin/env python3
"""
Helper script to encode GitHub App private key for use in environment variables.
This script reads a PEM file and outputs the base64 encoded version.
"""

import base64
import sys
import os
import argparse


def encode_private_key(pem_file_path: str) -> str:
    """Read PEM file and return base64 encoded string"""
    try:
        with open(pem_file_path, 'r') as f:
            pem_content = f.read()
        
        # Encode to base64
        encoded = base64.b64encode(pem_content.encode('utf-8')).decode('ascii')
        return encoded
        
    except FileNotFoundError:
        print(f"Error: File '{pem_file_path}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Encode GitHub App private key for environment variables"
    )
    parser.add_argument(
        'pem_file',
        help='Path to the GitHub App private key PEM file'
    )
    parser.add_argument(
        '--output-env',
        action='store_true',
        help='Output in .env file format'
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pem_file):
        print(f"Error: File '{args.pem_file}' does not exist")
        sys.exit(1)
    
    # Encode the private key
    encoded_key = encode_private_key(args.pem_file)
    
    if args.output_env:
        print(f"GITHUB_PRIVATE_KEY={encoded_key}")
    else:
        print("Base64 encoded GitHub private key:")
        print(encoded_key)
        print()
        print("Add this to your .env file as:")
        print(f"GITHUB_PRIVATE_KEY={encoded_key}")


if __name__ == "__main__":
    main()