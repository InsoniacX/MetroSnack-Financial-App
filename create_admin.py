from database.db import initialize_database, execute, hash_password, query_one

def create_superadmin():
    initialize_database()

    username = input("Enter superadmin username: ").strip()
    full_name = input("Enter superadmin full name: ").strip()
    password = input("Enter superadmin password: ").strip()

    existing_user = query_one("SELECT * FROM users WHERE username = ?", (username,))
    if existing_user:
        print(f"User '{username}' already exists. Please choose a different username.")
        return

    password_hash, password_salt = hash_password(password)

    execute(
        """
        INSERT INTO users (username, full_name, password_hash, password_salt, role)
        VALUES (?, ?, ?, ?, 'superadmin')
        """,
        (username, full_name, password_hash, password_salt),
    )
    print(f"Superadmin '{username}' created successfully.")


if __name__ == "__main__":
    create_superadmin()