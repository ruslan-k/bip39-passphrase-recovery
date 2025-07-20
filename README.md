# Multicurrency Wallet Recovery Tool 🔐

This is a high-performance Python script designed to help recover access to a cryptocurrency wallet by searching for a forgotten passphrase or correcting typos in a known passphrase.

It is a modular, multicurrency tool that supports many of the most popular cryptocurrencies. It uses multiprocessing to leverage all available CPU cores and includes an advanced typo generator to maximize the chances of a successful recovery.

-----

## Features

  * **Multicurrency Support**: Natively supports 8 of the most common cryptocurrencies.
  * **High-Speed Search**: Utilizes all available CPU cores to check passphrases in parallel.
  * **Advanced Typo Generation**: Corrects common typing mistakes by checking variations of your passphrase.
  * **Standard Derivation Paths**: Automatically checks the most common derivation paths for the selected cryptocurrency.
  * **Detailed Logging**: Optionally, log every single passphrase attempt to a file for debugging and analysis.
  * **"No Passphrase" Check**: Automatically includes a check for an empty passphrase, the most common scenario.

-----

## Supported Cryptocurrencies

  * **Solana** (SOL)
  * **Bitcoin** (BTC) - *Checks Legacy, SegWit, and Native SegWit addresses.*
  * **Ethereum** (ETH) - *Also works for ERC-20 tokens like USDT, USDC, etc.*
  * **BNB Smart Chain** (BNB)
  * **XRP** (XRP)
  * **Dogecoin** (DOGE)
  * **Litecoin** (LTC)
  * **Bitcoin Cash** (BCH)

-----

## Setup

1.  **Install Python**: Ensure you have Python 3.10 or newer installed.

2.  **Install Dependencies**: This script requires several libraries for different cryptocurrencies. Install them all with a single command:

    ```bash
    pip install bip_utils solders tqdm bitcoinlib eth-keys xrpl-py
    ```

3.  **Create Input Files**: In the same directory as the script (`recover.py`), create the following plain text files:

      * **`seed_phrases.txt`**
        This file must contain your 12 or 24-word seed phrase on the first line.

      * **`addresses_to_find.txt`**
        List all the cryptocurrency addresses you are searching for, one per line. The script will stop as soon as it finds a match.

      * **`passphrases.txt`**
        This is your list of base passphrase guesses. Put one passphrase per line. Passphrases that are just a space or contain leading/trailing spaces will be tested correctly.

-----

## Usage

Run the script from your terminal, **specifying which coin you are searching for** with the `--coin` flag.

### Command-Line Arguments

| Flag | Description | Default |
| :--- | :--- | :--- |
| **`--coin`** | **(Required)** The ticker symbol of the crypto to search for (e.g., `BTC`, `ETH`, `SOL`). | `SOL` |
| `--seed-file` | Path to your mnemonic file. | `seed_phrases.txt` |
| `--pass-file` | Path to your passphrase list. | `passphrases.txt` |
| `--address-file` | Path to your target addresses file. | `addresses_to_find.txt` |
| `--workers` | Number of CPU cores to use. | All available cores |
| `--log-attempts` | Log every single generated attempt to `attempts_log.txt`. | Disabled |
| `--skip-no-passphrase`| Disables the automatic check for an empty passphrase. | Disabled |

### Typo Generation

The typo features are powerful but create a massive number of combinations. **It is highly recommended to start with `--typos 1` and only increase to 2 if necessary. A value of 3 or more is often computationally infeasible.**

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

**Example 1: Search for an Ethereum address with no typos**

```bash
python recover.py --coin ETH
```

**Example 2: Search for a Bitcoin address with up to 1 typo (swap or delete)**

```bash
python recover.py --coin BTC --typos 1 --typos-swap --typos-delete
```

**Example 3: Search for a Solana address with a comprehensive 2-typo search, logging all attempts**

```bash
python recover.py --coin SOL --typos 2 --typos-capslock --typos-swap --typos-repeat --typos-delete --typos-case --log-attempts
```

-----

## Adapting to Other Cryptocurrencies

The script was designed to be modular. You can add support for other BIP44-compatible cryptocurrencies by following these three steps.

### 1\. Find the BIP44 Coin Type

Each cryptocurrency has a unique number. Find the coin type for your desired crypto from an authoritative source like the [SLIP-0044 registry](https://www.google.com/search?q=https://github.com/satoshilabs/slips/blob/master/slip-0044.md).

  * Example: TRON (TRX) is coin type `195`.

### 2\. Create an Address Generator Function

You need a Python function that takes a 32-byte private key and generates a public address. This usually requires finding a suitable Python library for that specific coin.

  * **Example for TRON (TRX):**
    1.  Install the necessary library: `pip install tronpy`
    2.  Add a new generator function to the script:
        ```python
        from tronpy.keys import PrivateKey as TronPrivateKey

        def generate_tron_address(priv_key_bytes, path):
            """Generates a TRON address."""
            private_key = TronPrivateKey(priv_key_bytes)
            yield private_key.public_key.to_base58check_address()
        ```

### 3\. Update the `CRYPTO_CONFIG` Dictionary

Finally, add a new entry to the `CRYPTO_CONFIG` dictionary at the top of the script. This tells the program how to handle the new coin.

  * **Example for TRON (TRX):**
    ```python
    CRYPTO_CONFIG = {
        'SOL': { ... }, # Existing coins
        'ETH': { ... },
        # Add your new coin here
        'TRX': {
            'coin_type': Bip44Coins.TRON, # Or Bip44.FromCoinType(195) if not in library
            'paths': ["m/44'/195'/0'/0/0"], # Standard path for TRON
            'address_generator': generate_tron_address,
        },
        # ... other existing coins
    }
    ```

After making these changes, you can run the script with `--coin TRX` to start searching for TRON addresses.
