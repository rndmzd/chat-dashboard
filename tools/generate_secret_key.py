import secrets

def generate_secret_key(key_size=32):
    # Generate a 32-byte (256-bit) secure random key
    return secrets.token_hex(key_size)

if __name__ == '__main__':
    key = generate_secret_key(32)
    with open('secret_key', 'w') as f:
        f.write(key)