import sys
import os
import argparse
import multiprocessing
from multiprocessing import Manager
from tqdm import tqdm

from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
from solders.keypair import Keypair

# --- List of Derivation Paths to Check ---
LEDGER_DERIVATION_PATHS = [
    "m/44'/501'/0'",
    "m/44'/501'/0'/0'"
]

# --- Helper Functions (Unchanged)---
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

# --- REWRITTEN Typo Generation Logic ---
class TypoGenerator:
    def __init__(self, args):
        self.max_typos = args.typos
        self.typo_types = []
        if args.typos_capslock: self.typo_types.append('capslock')
        if args.typos_swap: self.typo_types.append('swap')
        if args.typos_repeat: self.typo_types.append('repeat')
        if args.typos_delete: self.typo_types.append('delete')
        if args.typos_case: self.typo_types.append('case')
        if args.typos_map: self.typo_types.append('map')
        self.typos_map = self._parse_typos_map(args.typos_map) if args.typos_map else {}

    def _parse_typos_map(self, filename):
        typos_map = {}
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        chars_to_replace = parts[0]
                        replacements = parts[1]
                        for char in chars_to_replace:
                            typos_map[char] = replacements
        except FileNotFoundError:
            print(f"❌ Error: Typos map file '{filename}' not found.")
            sys.exit(1)
        return typos_map

    def generate(self, base_password):
        """Public method to start the typo generation."""
        memo = set()  # Use a memoization set to avoid duplicate work/yields
        yield from self._generate_recursive(base_password, self.max_typos, memo)

    def _generate_recursive(self, password, k, memo):
        """Recursively generates password variations."""
        if password in memo:
            return
        
        memo.add(password)
        yield password

        if k == 0:
            return

        # --- Generate variations for the next level of recursion ---

        # Capslock (a single typo that affects the whole string)
        if 'capslock' in self.typo_types:
            yield from self._generate_recursive(password.swapcase(), k - 1, memo)

        # Character-by-character typos
        for i in range(len(password)):
            # Delete
            if 'delete' in self.typo_types:
                new_pass = password[:i] + password[i+1:]
                yield from self._generate_recursive(new_pass, k - 1, memo)
            # Repeat
            if 'repeat' in self.typo_types:
                new_pass = password[:i] + password[i] + password[i+1:]
                yield from self._generate_recursive(new_pass, k - 1, memo)
            # Swap
            if 'swap' in self.typo_types and i < len(password) - 1:
                new_pass = password[:i] + password[i+1] + password[i] + password[i+2:]
                yield from self._generate_recursive(new_pass, k - 1, memo)
            # Case
            if 'case' in self.typo_types:
                char = password[i]
                if char.islower():
                    new_pass = password[:i] + char.upper() + password[i+1:]
                    yield from self._generate_recursive(new_pass, k - 1, memo)
                elif char.isupper():
                    new_pass = password[:i] + char.lower() + password[i+1:]
                    yield from self._generate_recursive(new_pass, k - 1, memo)
            # Map
            if 'map' in self.typo_types:
                if password[i] in self.typos_map:
                    for rep_char in self.typos_map[password[i]]:
                        new_pass = password[:i] + str(rep_char) + password[i+1:]
                        yield from self._generate_recursive(new_pass, k - 1, memo)

# --- Multiprocessing Functions ---
def listener(log_queue, log_filename):
    with open(log_filename, 'a', encoding='utf-8') as f:
        while True:
            message = log_queue.get()
            if message == 'KILL': break
            f.write(message + '\n')
            f.flush()

def init_worker(mnemonic_arg, addresses_arg, typo_gen_arg, paths_arg, log_q_arg):
    global static_mnemonic, addresses_to_find, typo_gen, derivation_paths, log_queue
    static_mnemonic = mnemonic_arg; addresses_to_find = addresses_arg
    typo_gen = typo_gen_arg; derivation_paths = paths_arg
    log_queue = log_q_arg

def worker(base_pass):
    # This worker logic is now correct because the generator is fixed
    for final_pass in typo_gen.generate(base_pass):
        if log_queue:
            log_queue.put(f"'{final_pass}'\t(Base: '{base_pass}')")
        try:
            seed_bytes = Bip39SeedGenerator(static_mnemonic).Generate(final_pass)
            bip44_mst_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.SOLANA)
            # ... (derivation logic as in the working version)
            path_ctx_0 = bip44_mst_ctx.Purpose().Coin().Account(0)
            addr_0 = str(Keypair.from_seed(path_ctx_0.PrivateKey().Raw().ToBytes()).pubkey())
            if addr_0 in addresses_to_find: return (base_pass, final_pass, addr_0, "m/44'/501'/0'")
            path_ctx_1 = bip44_mst_ctx.Purpose().Coin().Account(1)
            addr_1 = str(Keypair.from_seed(path_ctx_1.PrivateKey().Raw().ToBytes()).pubkey())
            if addr_1 in addresses_to_find: return (base_pass, final_pass, addr_1, "m/44'/501'/1'")
            path_ctx_0_0 = bip44_mst_ctx.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT)
            addr_0_0 = str(Keypair.from_seed(path_ctx_0_0.PrivateKey().Raw().ToBytes()).pubkey())
            if addr_0_0 in addresses_to_find: return (base_pass, final_pass, addr_0_0, "m/44'/501'/0'/0'")
        except Exception:
            continue
    return None

# --- Main Execution Block ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Solana address recovery tool.")
    # (Arguments are unchanged and omitted for brevity)
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
    parser.add_argument('--log-attempts', action='store_true', help='Log every generated attempt to attempts_log.txt.')
    parser.add_argument('--skip-no-passphrase', action='store_true', help='Do not automatically check for an empty passphrase.')
    
    args = parser.parse_args()

    print("🔐 Solana Address Finder")
    print("-" * 60)

    ATTEMPTS_LOG_FILENAME = 'attempts_log.txt'
    main_static_mnemonic = get_first_line(args.seed_file)
    if not main_static_mnemonic: sys.exit(f"❌ Error: No mnemonic found in '{args.seed_file}'.")
    
    main_addresses_to_find = read_lines_to_set(args.address_file)
    if not main_addresses_to_find: sys.exit(f"❌ Error: No target addresses found in '{args.address_file}'.")

    main_typo_gen = TypoGenerator(args)
    passphrases_to_check = read_lines_to_list(args.pass_file)
    seen = set()
    passphrases_to_check_unique = []
    if not args.skip_no_passphrase:
        passphrases_to_check_unique.append("")
        seen.add("")

    for p in passphrases_to_check:
        if p not in seen:
            passphrases_to_check_unique.append(p)
            seen.add(p)
    
    passphrases_to_check = passphrases_to_check_unique

    if not passphrases_to_check:
        sys.exit(f"❌ Error: The passphrase file '{args.pass_file}' is empty and the 'no passphrase' check was skipped.")

    if "" in seen:
        print("INFO: Automatically checking for a 'no passphrase' case.")

    total_passphrases_to_check = len(passphrases_to_check)
    print(f"Mnemonic Loaded: '{' '.join(main_static_mnemonic.split()[:3])}...'")
    print(f"Base Passphrases to Check: {total_passphrases_to_check:,}")
    print(f"Using {args.workers} CPU cores...")
    
    found_match = None
    manager = Manager()
    log_queue = manager.Queue() if args.log_attempts else None
    logger_process = None

    if log_queue:
        print(f"📝 Logging all attempts to {ATTEMPTS_LOG_FILENAME}...")
        logger_process = multiprocessing.Process(target=listener, args=(log_queue, ATTEMPTS_LOG_FILENAME))
        logger_process.start()
        
    init_args = (main_static_mnemonic, main_addresses_to_find, main_typo_gen, LEDGER_DERIVATION_PATHS, log_queue)

    print("-" * 60)
    try:
        with multiprocessing.Pool(processes=args.workers, initializer=init_worker, initargs=init_args) as pool:
            results = pool.imap_unordered(worker, passphrases_to_check, chunksize=1)
            
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
