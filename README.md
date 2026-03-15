# 🔐 SecureVault

A **fully offline, production-ready desktop secret manager** built with Python 3.12+ and PySide6.

Store API keys, passwords, SSH tokens, and any other secrets with **double encryption** (AES-256 Fernet + ChaCha20-Poly1305) — nothing unencrypted ever touches disk or logs.

---

## Features

| Feature | Details |
|---|---|
| **Double encryption** | AES-256 Fernet (PBKDF2-derived key) + ChaCha20-Poly1305 (per-secret nonce/salt) |
| **Master password** | PBKDF2-HMAC-SHA256 key derivation (600 000 iterations) |
| **Animated startup** | Smooth fade-in splash with loading progress bar |
| **Secure clipboard** | Auto-clears after 12 seconds |
| **View popup** | Auto-closes after 30 seconds |
| **Random key generator** | Configurable length and character classes |
| **Encrypted backup** | Export/import the SQLite database |
| **Search & sort** | Real-time filter; sort by date or alphabetically |
| **Categories/tags** | Organise secrets by type |
| **Zero AI** | No AI, ML, or cloud components anywhere |
| **Fully offline** | Zero network connections |

---

## Requirements

- Python 3.12 or newer
- PySide6
- cryptography
- pyperclip

---

## Installation

```bash
# 1. Clone or download the repository
git clone https://github.com/gurusamsara-dev/Voicecashapp.git
cd Voicecashapp

# 2. Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch SecureVault
python -m securevault.main
```

---

## Usage

### First launch
1. The splash screen appears while the database is initialised.
2. You are prompted to **create a master password** (minimum 8 characters).
3. The main vault window opens.

### Subsequent launches
1. Enter your master password to unlock the vault.
2. Three failed attempts will close the application.

### Adding a secret
- Click **➕ Add Key**.
- Fill in the **Description**, choose a **Category**, and enter or generate the **Secret**.
- Click **💾 Save**.

### Viewing a secret
- Select a row and click **👁 View Key** (or double-click the row).
- The decrypted secret is shown in a popup that **auto-closes after 30 seconds**.

### Copying a secret
- Select a row and click **📋 Copy Key**.
- The secret is copied to the clipboard and **auto-cleared after 12 seconds**.

### Deleting a secret
- Select a row and click **🗑 Delete Key**.
- Confirm the prompt.

### Random key generator
- Click **Tools → Random Key Generator** or use the **🎲 Generate** button inside *Add Key*.
- Configure length and character classes, then click **⚡ Generate**.

### Backup
- **File → Export Encrypted Backup…** saves a copy of the database.
- **File → Import Encrypted Backup…** restores from a backup (replaces the current vault).

---

## Security Architecture

```
Master Password
      │
      ▼  PBKDF2-HMAC-SHA256 (600 000 iterations)
  Fernet Key (AES-256-CBC + HMAC-SHA256)  ←── per-vault fernet_salt
      │
      ▼  Fernet.encrypt(secret)
  Fernet Token
      │
      ▼  ChaCha20-Poly1305.encrypt(fernet_token)  ←── per-secret nonce + salt
  Encrypted Blob  ──► stored in SQLite
```

- All values in the database are **opaque blobs** — no plaintext anywhere.
- The master password is **never stored**; only its SHA-256 hash is kept for verification.
- Each secret has its own **random nonce and salt** (ChaCha20) and a **random salt** (Fernet), preventing correlation attacks.

---

## File Structure

```
securevault/
├── __init__.py     # Package marker
├── main.py         # PySide6 GUI — animation, auth, CRUD
├── encryption.py   # Double encryption (Fernet + ChaCha20-Poly1305)
├── database.py     # SQLite CRUD operations
├── clipboard.py    # Secure clipboard with auto-clear timer
└── utils.py        # Key generator, validators, helpers
requirements.txt
README.md
```

---

## Database Location

By default the SQLite database is stored at:

| OS | Path |
|---|---|
| Linux / macOS | `~/.securevault/vault.db` |
| Windows | `%USERPROFILE%\.securevault\vault.db` |

Override with the `SECUREVAULT_DB` environment variable:

```bash
SECUREVAULT_DB=/path/to/my/vault.db python -m securevault.main
```

---

## License

MIT — see [LICENSE](LICENSE) for details.
