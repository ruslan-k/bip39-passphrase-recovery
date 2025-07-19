# Solana Address Recovery Tool

This is a high-performance Python script designed to help recover access to a Solana wallet by searching for a forgotten passphrase or correcting typos in a known passphrase.

It uses multiprocessing to leverage all available CPU cores, and includes an advanced typo generator to test thousands of variations of your passphrases, checking against multiple standard Ledger derivation paths to maximize the chances of a successful recovery.

-----

## Features

  * **High-Speed Search**: Utilizes all available CPU cores to check passphrases in parallel.
  * **Advanced Typo Generation**: Corrects common typing mistakes by checking variations of your passphrase (e.g., swapped/deleted characters, case changes, and more).
  * **Multi-Path Derivation**: Checks against the most common Ledger derivation paths for Solana (`m/44'/501'/0'`, `m/44'/501'/0'/0'`) for each attempt.
  * **"No Passphrase" Check**: Automatically includes a check for an empty passphrase, the most common scenario.
  * **Detailed Logging**: Optionally, you can log every single passphrase attempt to a file for debugging or analysis.

-----

## Setup

1.  **Install Python**: Ensure you have Python 3.10 or newer installed.

2.  **Install Dependencies**: This script requires a few external libraries. Install them using pip:

    ```bash
    pip install bip_utils solders tqdm
    ```

3.  **Create Input Files**: In the same directory as the script, create the following plain text files:

      * **`seed_phrases.txt`**
        This file must contain your 24-word seed phrase on the first line.

      * **`addresses_to_find.txt`**
        List all the Solana addresses you are searching for, one per line. The script will stop as soon as it finds a match for any address in this file.

      * **`passphrases.txt`**
        This is your list of base passphrases to try. Put one passphrase guess per line. If a passphrase is just a space or contains spaces, the script will handle it correctly.

-----

## Usage

Run the script from your terminal. The most basic usage is simply:

```bash
python recover.py
```

This will use the default filenames and check all passphrases in `passphrases.txt` without generating typos.

### Command-Line Arguments

You can control the script's behavior with the following flags:

| Flag | Description | Default |
| :--- | :--- | :--- |
| `--seed-file` | Path to your mnemonic file. | `seed_phrases.txt` |
| `--pass-file` | Path to your passphrase list. | `passphrases.txt` |
| `--address-file` | Path to your target addresses file. | `addresses_to_find.txt` |
| `--workers` | Number of CPU cores to use. | All available cores |
| `--log-attempts` | Log every single generated attempt to `attempts_log.txt`. | Disabled |
| `--skip-no-passphrase` | Disables the automatic check for an empty passphrase. | Disabled |

### Typo Generation

The typo features are powerful but can create a massive number of combinations. **It is highly recommended to start with `--typos 1` and only increase if necessary.**

| Flag | Description |
| :--- | :--- |
| `--typos <N>` | The maximum number of typos to apply (e.g., `--typos 2`). **Required to enable typos.** |
| `--typos-capslock` | Tries the whole passphrase with caps lock on. |
| `--typos-swap` | Swaps two adjacent characters. |
| `--typos-repeat` | Repeats (doubles) a character. |
| `--typos-delete` | Deletes a character. |
| `--typos-case` | Changes the case (upper/lower) of a single letter. |
| `--typos-map <file>` | Tries replacing characters based on rules in a map file. |

#### Typo Map File

A typo map file allows you to define custom replacement rules. For example, to check for common "leet speak" typos:

**`my_map.txt`**

```
a @
s $5
o 0
```

You would use it with the command: `--typos-map ./my_map.txt`

### Examples

**Example 1: Basic search with no typos**

```bash
python recover.py
```

**Example 2: Search with up to 2 typos, checking for deleted characters and case changes**

```bash
python recover.py --typos 2 --typos-delete --typos-case
```

**Example 3: A comprehensive search with 1 typo, all typo types, and full logging**

```bash
python recover.py --typos 1 --typos-capslock --typos-swap --typos-repeat --typos-delete --typos-case --log-attempts
```
