import re
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class TestResult:
    file_path: str
    start_idx: int = 0
    end_idx: int = 0
    
    # Métadonnées
    idx: int = -1
    onnx_model: str = ""
    vnnlib_spec: str = ""
    
    # Verdicts
    verified_status: str = "Unknown"
    verified_success: bool = False
    violations: int = 0
    test_type: str = "Unknown"  # "CE", "BaB", "AC"
    
    # Performances générales
    total_time: float = 0.0
    attack_time: float = 0.0

    # --- Spécifique aux Contre-Exemples (CE) ---
    cex_saved: bool = False            
    margins: List[float] = field(default_factory=list)  
    attack_succeeded: bool = False     

    # --- Commun à BaB et AC (Bornes et optimisations initiales) ---
    initial_crown_bound: float = 0.0   # Borne globale initiale de CROWN
    alpha_crown_time: float = 0.0      # Temps d'optimisation alpha/beta initial
    best_l_after_optimization: float = 0.0 # Meilleure borne inférieure après optimisation

    # --- Spécifique au Branch-and-Bound (BaB) ---
    unstable_neurons: int = 0          # Nombre de neurones instables
    bab_rounds: int = 0                # Nombre d'itérations BaB effectuées
    visited_domains: int = 0           # Nombre total de domaines explorés

    # --- Spécifique à All-Clear (AC) ---
    verified_with_init_bound: bool = False # Certifié directement avec la borne initiale


def parser(file_path: str) -> Dict[int, TestResult]:
    tests = {}
    current_test = TestResult(file_path=file_path)
    
    idx_pattern = re.compile(r"idx:\s*(\d+)")
    result_pattern = re.compile(r"Result:")
    
    with open(file_path, mode='rb') as f:
        while True:
            start_pos = f.tell()
            line_bytes = f.readline()
            if not line_bytes:
                break
                
            line = line_bytes.decode('utf-8', errors='ignore')
            
            idx_match = idx_pattern.search(line)
            if idx_match:
                test_id = int(idx_match.group(1))
                current_test.idx = test_id
                current_test.start_idx = start_pos
                tests[test_id] = current_test

            result_match = result_pattern.search(line)
            if result_match:
                current_test.end_idx = f.tell()
                current_test = TestResult(file_path=file_path)
                
    return tests


def check_type(text: str, violations: int) -> str:
    """Détermine le type de test (CE, BaB ou AC)."""
    if violations > 0:
        return "CE"
    
    # Si des étapes de division de domaine (BaB) ont commencé
    if "BaB round" in text or "splitting decisions" in text:
        return "BaB"
        
    return "AC"


def get_test_summary(tests_dict: Dict[int, TestResult], test_id: int) -> TestResult:
    if test_id not in tests_dict:
        raise KeyError(f"Le test avec l'ID {test_id} n'existe pas.")
        
    test = tests_dict[test_id] 
    bytes_to_read = test.end_idx - test.start_idx
    
    if bytes_to_read <= 0:
        return test

    with open(test.file_path, mode='rb') as f:
        f.seek(test.start_idx)
        text_bytes = f.read(bytes_to_read)
        text = text_bytes.decode('utf-8', errors='ignore')
    
    # --- EXTRACTION DES DONNÉES GÉNÉRALES ---
    onnx_match = re.search(r"Using onnx\s+(.*)", text)
    if onnx_match:
        test.onnx_model = onnx_match.group(1).strip()
        
    vnnlib_match = re.search(r"Using vnnlib\s+(.*)", text)
    if vnnlib_match:
        test.vnnlib_spec = vnnlib_match.group(1).strip()
        
    violation_matches = re.findall(r"Total number of violation:\s*(\d+)", text)
    if violation_matches:
        test.violations = int(violation_matches[-1])
        
    status_match = re.search(r"verified_status\s+(\S+)", text)
    if status_match:
        test.verified_status = status_match.group(1).strip()
        
    success_match = re.search(r"verified_success\s+(\S+)", text)
    if success_match:
        test.verified_success = success_match.group(1).strip().lower() == "true"
        
    attack_match = re.search(r"Attack finished in\s+([\d.]+)\s+seconds", text)
    if attack_match:
        test.attack_time = float(attack_match.group(1))
        
    total_time_match = re.search(r"Result:\s*\S+\s+in\s+([\d.]+)\s+seconds", text)
    if total_time_match:
        test.total_time = float(total_time_match.group(1))

    # Détermination du type de test
    test.test_type = check_type(text, test.violations)

    # --- TRAITEMENTS SPÉCIFIQUES ---
    
    # 1. Extraction des métriques communes d'optimisation (si disponibles dans le log)
    initial_lb_match = re.search(r"Global lower bound:\s*([-\d.eE]+)", text)
    if initial_lb_match:
        test.initial_crown_bound = float(initial_lb_match.group(1))

    alpha_time_match = re.search(r"alpha/beta optimization time:\s*([\d.eE]+)", text)
    if alpha_time_match:
        test.alpha_crown_time = float(alpha_time_match.group(1))

    best_l_match = re.search(r"best_l after optimization:\s*([-\d.eE]+)", text)
    if best_l_match:
        test.best_l_after_optimization = float(best_l_match.group(1))

    # 2. Branchements par types
    if test.test_type == "CE":
        tensor_pattern = re.compile(r"tensor\(\[\[([\s\S]*?)\]\]", re.MULTILINE)
        tensor_matches = tensor_pattern.findall(text)
        
        if tensor_matches:
            last_tensor_raw = tensor_matches[-1]
            clean_str = re.sub(r"\s+", " ", last_tensor_raw).replace(",", " ").strip()
            try:
                test.margins = [float(x) for x in clean_str.split() if x]
            except ValueError:
                test.margins = []

        if "Saving Counterexample" in text or "save_cex" in text:
            test.cex_saved = True

        if "PGD attack succeeded!" in text:
            test.attack_succeeded = True

    elif test.test_type == "BaB":
        unstable_match = re.search(r"#\s*of\s*unstable\s*neurons:\s*(\d+)", text)
        if unstable_match:
            test.unstable_neurons = int(unstable_match.group(1))

        rounds = [int(r) for r in re.findall(r"BaB round\s*(\d+)", text)]
        if rounds:
            test.bab_rounds = max(rounds)

        domains_match = re.findall(r"(\d+)\s+domains?\s+visited", text)
        if domains_match:
            test.visited_domains = int(domains_match[-1])

    elif test.test_type == "AC":
        # On valide si l'outil confirme explicitement la réussite directe
        if "verified with init bound!" in text:
            test.verified_with_init_bound = True

    return test