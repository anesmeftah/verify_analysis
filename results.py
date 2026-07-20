import csv
import sys
import argparse
import re
import os
from parser import parser

def get_root_path(file_path):
    with open(file_path, 'r', errors='ignore') as f:
        for line in f:
            match = re.search(r'root_path:\s*(.*)', line)
            if match:
                path = match.group(1).strip().strip("'").strip('"')
                if path:
                    return path
            # Stop searching after the experiments start
            if 'Experiments at' in line or 'idx: 0' in line:
                break
    return ""

def format_path(path):
    # Make path start with ./benchmarks/ if benchmarks is in path
    if 'benchmarks/' in path:
        idx = path.find('benchmarks/')
        return './' + path[idx:]
    return path

def get_benchmark_name(onnx_path):
    match = re.search(r'benchmarks/([^/]+)', onnx_path)
    if match:
        return match.group(1)
    
    parts = onnx_path.replace('\\', '/').split('/')
    if len(parts) > 1:
        if parts[0] in ['.', '']:
            if len(parts) > 2:
                return parts[1]
        else:
            return parts[0]
    return "unknown"

def map_status(status):
    status_lower = status.lower()
    if 'unsafe' in status_lower:
        return 'SAT'
    elif 'safe' in status_lower:
        return 'UNSAT'
    elif 'timeout' in status_lower:
        return 'timeout'
    elif status_lower == 'sat':
        return 'SAT'
    elif status_lower == 'unsat':
        return 'UNSAT'
    else:
        return status # fallback

def main():
    arg_parser = argparse.ArgumentParser(description="Summarize benchmark output to a CSV.")
    arg_parser.add_argument("input_file", help="The output log file to parse.")
    arg_parser.add_argument("output_file", nargs='?', default='output.csv', help="The CSV file to save results to.")
    args = arg_parser.parse_args()

    # Get root path if it exists
    root_path = get_root_path(args.input_file)

    tests = parser(args.input_file)
    
    with open(args.output_file, mode='w', newline='') as f:
        # Use tab as delimiter since the user's example looks like tab-separated values
        # although they called it csv, TSV is a type of CSV and it matches exactly.
        writer = csv.writer(f, delimiter='\t') 
        for test_id, test in tests.items():
            
            # Combine root_path and model path if model path is relative
            onnx_raw = test.onnx_model
            if not os.path.isabs(onnx_raw) and root_path:
                onnx_raw = os.path.join(root_path, onnx_raw)
            onnx_path = format_path(onnx_raw)
            
            vnnlib_raw = test.vnnlib_spec
            if not os.path.isabs(vnnlib_raw) and root_path:
                vnnlib_raw = os.path.join(root_path, vnnlib_raw)
            vnnlib_path = format_path(vnnlib_raw)
            
            benchmark = get_benchmark_name(onnx_path)
            status = map_status(test.verified_status)
            
            attack_time_str = f"{test.attack_time:.9f}" if isinstance(test.attack_time, float) else test.attack_time
            total_time_str = f"{test.total_time:.9f}" if isinstance(test.total_time, float) else test.total_time
            
            row = [
                benchmark,
                onnx_path,
                vnnlib_path,
                attack_time_str,
                status,
                total_time_str
            ]
            writer.writerow(row)

if __name__ == "__main__":
    main()
