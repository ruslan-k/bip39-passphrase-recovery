import sys
import os
import argparse
import itertools
import multiprocessing
from multiprocessing import Manager
from tqdm import tqdm

# Crypto Libraries
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
from solders.keypair import Keypair as SolKeypair
from bitcoinlib.keys import Key as BtcKey
from eth_keys.datatypes import PrivateKey as EthPrivateKey
from xrpl.wallet import Wallet as XrpWallet

# --- 💱 CRYPTO CONFIGURATION ---
def generate_solana_address(priv_key_bytes, path):
    yield str(SolKeypair.from_seed(priv_key_bytes).pubkey())
def generate_ethereum_address(priv_key_bytes, path):
    yield EthPrivateKey(priv_key_bytes).public_key.to_checksum_address()
def generate_bitcoin_address(priv_key_bytes, path):
    key = BtcKey(priv_key=priv_key_bytes)
    yield key.address('legacy'); yield key.address('segwit'); yield key.address('bech32')
def generate_bitcoin_cash_address(priv_key_bytes, path):
    key = BtcKey(priv_key=priv_key_bytes, network='bitcoincash')
    yield key.address('cash')
def generate_litecoin_address(priv_key_bytes, path):
    key = BtcKey(priv_key=priv_key_bytes, network='litecoin')
    yield key.address('legacy'); yield key.address('segwit'); yield key.address('bech32')
def generate_dogecoin_address(priv_key_bytes, path):
    key = BtcKey(priv_key=priv_key_bytes, network='dogecoin')
    yield key.address('legacy')
def generate_xrp_address(priv_key_bytes, path):
    wallet = XrpWallet(seed_hex=priv_key_bytes.hex())
    yield wallet.classic_address

CRYPTO_CONFIG = {
    'SOL': {'coin_type': Bip44Coins.SOLANA, 'paths': ["m/44'/501'/0'", "m/44'/501'/1'", "m/44'/501'/0'/0'"], 'address_generator': generate_solana_address},
    'ETH': {'coin_type': Bip44Coins.ETHEREUM, 'paths': ["m/44'/60'/0'/0/0"], 'address_generator': generate_ethereum_address},
    'BTC': {'coin_type': Bip44Coins.BITCOIN, 'paths': ["m/84'/0'/0'/0/0", "m/49'/0'/0'/0/0", "m/44'/0'/0'/0/0"], 'address_generator': generate_bitcoin_address},
    'BNB': {'coin_type': Bip44Coins.BINANCE_SMART_CHAIN, 'paths': ["m/44'/714'/0'/0/0"], 'address_generator': generate_ethereum_address},
    'DOGE': {'coin_type': Bip44Coins.DOGECOIN, 'paths': ["m/44'/3'/0'/0/0"], 'address_generator': generate_dogecoin_address},
    'LTC': {'coin_type': Bip44Coins.LITECOIN, 'paths': ["m/84'/2'/0'/0/0", "m/49'/2'/0'/0/0"], 'address_generator': generate_litecoin_address},
    'BCH': {'coin_type': Bip44Coins.BITCOIN_CASH, 'paths': ["m/44'/145'/0'/0/0"], 'address_generator': generate_bitcoin_cash_address},
    'XRP': {'coin_type': Bip44Coins.RIPPLE, 'paths': ["m/44'/144'/0'/0/0"], 'address_generator': generate_xrp_address},
}

# --- Helper Functions ---
def read_lines_to_set(filename: str) -> set[str]:
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            return {line.strip() for line in f if line.strip()}
    except FileNotFoundError: return set()

def get_first_line(filename: str) -> str | None:
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.strip(): return line.strip()
        return None
    except FileNotFoundError: return None

def read_lines_to_list(filename: str) -> list[str]:
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.rstrip('\n') for line in f]
    except FileNotFoundError:
        return []

# --- Typo Generation Logic (Unchanged) ---
class TypoGenerator:
    def __init__(self, args):
        self.max_typos = args.typos; self.typo_types = []
        if args.typos_capslock: self.typo_types.append('capslock')
        if args.typos_swap: self.typo_types.append('swap')
        if args.typos_repeat: self.typo_types.append('repeat')
        if args.typos_delete: self.typo_types.append('delete')
        if args.typos_case: self.typo_types.append('case')
        if args.typos_map: self.typo_types.append('map')
        self.typos_map = self._parse_typos_map(args.typos_map) if args.typos_map else {}
    def _parse_typos_map(self, filename):
        typos_map = {};
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parts = line.strip().split();
                    if len(parts) >= 2:
                        chars_to_replace = parts[0]; replacements = parts[1]
                        for char in chars_to_replace: typos_map[char] = replacements
        except FileNotFoundError: print(f"❌ Error: Typos map file '{filename}' not found."); sys.exit(1)
        return typos_map
    def generate(self, base_password):
        memo = set()
        yield from self._generate_recursive(base_password, self.max_typos, memo)
    def _generate_recursive(self, password, k, memo):
        if password in memo: return
        memo.add(password); yield password
        if k == 0: return
        if 'capslock' in self.typo_types: yield from self._generate_recursive(password.swapcase(), k - 1, memo)
        for i in range(len(password)):
            if 'delete' in self.typo_types: yield from self._generate_recursive(password[:i] + password[i+1:], k - 1, memo)
            if 'repeat' in self.typo_types: yield from self._generate_recursive(password[:i] + password[i] + password[i+1:], k - 1, memo)
            if 'swap' in self.typo_types and i < len(password) - 1: yield from self._generate_recursive(password[:i] + password[i+1] + password[i] + password[i+2:], k - 1, memo)
            if 'case' in self.typo_types:
                char = password[i]
                if char.islower(): yield from self._generate_recursive(password[:i] + char.upper() + password[i+1:], k - 1, memo)
                elif char.isupper(): yield from self._generate_recursive(password[:i] + char.lower() + password[i+1:], k - 1, memo)
            if 'map' in self.typo_types and password[i] in self.typos_map:
                for rep_char in self.typos_map[password[i]]: yield from self._generate_recursive(password[:i] + str(rep_char) + password[i+1:], k - 1, memo)


# --- Multiprocessing Functions ---
def listener(log_queue, log_filename):
    with open(log_filename, 'a', encoding='utf-8') as f:
        while True:
            message = log_queue.get()
            if message == 'KILL': break
            f.write(message + '\n'); f.flush()

def init_worker(mnemonic_arg, addresses_arg, typo_gen_arg, crypto_config_arg, log_q_arg):
    global static_mnemonic, addresses_to_find, typo_gen, crypto_config, log_queue
    static_mnemonic = mnemonic_arg; addresses_to_find = addresses_arg
    typo_gen = typo_gen_arg; crypto_config = crypto_config_arg
    log_queue = log_q_arg

def solana_worker(base_pass):
    """
    Dedicated worker for SOLANA using the explicit, known-good derivation method.
    """
    address_generator = crypto_config['address_generator']
    for final_pass in typo_gen.generate(base_pass):
        try:
            seed_bytes = Bip39SeedGenerator(static_mnemonic).Generate(final_pass)
            bip44_mst_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.SOLANA)

            # Path 1: m/44'/501'/0'
            path_str_0 = "m/44'/501'/0'"
            path_ctx_0 = bip44_mst_ctx.Purpose().Coin().Account(0)
            priv_key_0 = path_ctx_0.PrivateKey().Raw().ToBytes()
            for addr in address_generator(priv_key_0, path_str_0):
                if log_queue: log_queue.put(f"'{final_pass}'\t{path_str_0}\t{addr}")
                if addr in addresses_to_find: return (base_pass, final_pass, addr, path_str_0)

            # Path 2: m/44'/501'/1'
            path_str_1 = "m/44'/501'/1'"
            path_ctx_1 = bip44_mst_ctx.Purpose().Coin().Account(1)
            priv_key_1 = path_ctx_1.PrivateKey().Raw().ToBytes()
            for addr in address_generator(priv_key_1, path_str_1):
                if log_queue: log_queue.put(f"'{final_pass}'\t{path_str_1}\t{addr}")
                if addr in addresses_to_find: return (base_pass, final_pass, addr, path_str_1)

            # Path 3: m/44'/501'/0'/0'
            path_str_0_0 = "m/44'/501'/0'/0'"
            path_ctx_0_0 = bip44_mst_ctx.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT)
            priv_key_0_0 = path_ctx_0_0.PrivateKey().Raw().ToBytes()
            for addr in address_generator(priv_key_0_0, path_str_0_0):
                if log_queue: log_queue.put(f"'{final_pass}'\t{path_str_0_0}\t{addr}")
                if addr in addresses_to_find: return (base_pass, final_pass, addr, path_str_0_0)

        except Exception:
            continue
    return None

def generic_worker(base_pass):
    """
    Generic worker for all other cryptocurrencies using the flexible DerivePath method.
    """
    for final_pass in typo_gen.generate(base_pass):
        try:
            seed_bytes = Bip39SeedGenerator(static_mnemonic).Generate(final_pass)
            bip44_mst_ctx = Bip44.FromSeed(seed_bytes, crypto_config['coin_type'])
            
            for path in crypto_config['paths']:
                priv_key_bytes = seed_bytes if crypto_config['coin_type'] == Bip44Coins.RIPPLE else bip44_mst_ctx.DerivePath(path).PrivateKey().Raw().ToBytes()
                address_generator = crypto_config['address_generator']
                
                for derived_address in address_generator(priv_key_bytes, path):
                    if log_queue: log_queue.put(f"'{final_pass}'\t{path}\t{derived_address}")
                    if derived_address in addresses_to_find:
                        return (base_pass, final_pass, derived_address, path)
        except Exception:
            continue
    return None

# --- Main Execution Block ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="A multicurrency wallet recovery tool.")
    parser.add_argument('--coin', default='SOL', choices=CRYPTO_CONFIG.keys(), help='The ticker symbol of the cryptocurrency.')
    # Add all other arguments...
    parser.add_argument('--seed-file', default='seed_phrases.txt')
    parser.add_argument('--pass-file', default='passphrases.txt')
    parser.add_argument('--address-file', default='addresses_to_find.txt')
    parser.add_argument('--workers', type=int, default=multiprocessing.cpu_count())
    parser.add_argument('--typos', type=int, default=0)
    parser.add_argument('--typos-capslock', action='store_true')
    parser.add_argument('--typos-swap', action='store_true')
    parser.add_argument('--typos-repeat', action='store_true')
    parser.add_argument('--typos-delete', action='store_true')
    parser.add_argument('--typos-case', action='store_true')
    parser.add_argument('--typos-map', help='Path to a typos map file.')
    parser.add_argument('--log-attempts', action='store_true')
    parser.add_argument('--skip-no-passphrase', action='store_true')
    
    args = parser.parse_args()
    
    print(f"🔐 {args.coin} Wallet Finder")
    print("-" * 60)

    ATTEMPTS_LOG_FILENAME = 'attempts_log.txt'
    main_static_mnemonic = get_first_line(args.seed_file)
    if not main_static_mnemonic: sys.exit(f"❌ Error: No mnemonic found in '{args.seed_file}'.")
    
    main_addresses_to_find = read_lines_to_set(args.address_file)
    if not main_addresses_to_find: sys.exit(f"❌ Error: No target addresses found in '{args.address_file}'.")

    main_typo_gen = TypoGenerator(args)
    crypto_config = CRYPTO_CONFIG[args.coin.upper()]
    passphrases_to_check = read_lines_to_list(args.pass_file)
    seen = set(); passphrases_to_check_unique = []
    if not args.skip_no_passphrase:
        passphrases_to_check_unique.append(""); seen.add("")
    for p in passphrases_to_check:
        if p not in seen: passphrases_to_check_unique.append(p); seen.add(p)
    passphrases_to_check = passphrases_to_check_unique
    if not passphrases_to_check: sys.exit(f"❌ Error: No passphrases to check.")
    if "" in seen: print("INFO: Automatically checking for a 'no passphrase' case.")

    total_passphrases_to_check = len(passphrases_to_check)
    print(f"Mnemonic Loaded: '{' '.join(main_static_mnemonic.split()[:3])}...'")
    print(f"Base Passphrases to Check: {total_passphrases_to_check:,}")
    print(f"Using {args.workers} CPU cores...")
    
    # --- CHOOSE THE CORRECT WORKER FUNCTION ---
    target_worker = solana_worker if args.coin.upper() == 'SOL' else generic_worker

    found_match = None
    manager = Manager()
    log_queue = manager.Queue() if args.log_attempts else None
    logger_process = None
    if log_queue:
        print(f"📝 Logging all attempts to {ATTEMPTS_LOG_FILENAME}...")
        logger_process = multiprocessing.Process(target=listener, args=(log_queue, ATTEMPTS_LOG_FILENAME))
        logger_process.start()
        
    init_args = (main_static_mnemonic, main_addresses_to_find, main_typo_gen, crypto_config, log_queue)

    print("-" * 60)
    try:
        with multiprocessing.Pool(processes=args.workers, initializer=init_worker, initargs=init_args) as pool:
            results = pool.imap_unordered(target_worker, passphrases_to_check, chunksize=1)
            with tqdm(total=total_passphrases_to_check, desc="Processing Passphrases") as pbar:
                for result in results:
                    pbar.update(1)
                    if result:
                        found_match = result
                        pool.terminate()
                        break
    except KeyboardInterrupt:
        print("\n🛑 Search interrupted by user.")
    finally:
        if logger_process:
            for _ in range(args.workers): log_queue.put('KILL')
            logger_process.join()
    
    print("-" * 60)
    if found_match:
        base_p, final_p, address, path = found_match
        print("\n" + "🎉" * 20)
        print("🎉 MATCH FOUND! 🎉".center(40))
        print("🎉" * 20)
        print(f"🔑 Mnemonic : {' '.join(main_static_mnemonic.split()[:3])}...")
        print(f"🔒 Passphrase: '{final_p}' (derived from '{base_p}')")
        print(f"PATH       : {path}")
        print(f"📍 Address  : {address}")
        print("✅ Search complete. A matching passphrase was found!")
    else:
        print("❌ Search complete. No matching passphrase was found.")
