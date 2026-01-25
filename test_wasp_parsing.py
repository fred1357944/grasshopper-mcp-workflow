import sys
import os
from grasshopper_mcp.ghx_parser import parse_ghx

def test_wasp_parsing():
    file_path = "gh_learning/ghx_samples/0.Basics/0_01_Basic_Aggregation.ghx"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print(f"Parsing {file_path}...")
    doc = parse_ghx(file_path)
    
    print(f"Found {len(doc.components)} components.")
    for c in doc.components.values():
        print(f"  - {c.name} ({c.nickname})")
    
    wasp_components = [c for c in doc.components.values() if "Wasp" in c.name or "Wasp" in c.nickname]
    print(f"Found {len(wasp_components)} WASP components.")
    
    for comp in wasp_components:
        print(f"\nComponent: {comp.name} ({comp.nickname})")
        print(f"  Inputs: {len(comp.inputs)}")
        for inp in comp.inputs:
            print(f"    - {inp.name} ({inp.data_type})")
        print(f"  Outputs: {len(comp.outputs)}")
        for outp in comp.outputs:
            print(f"    - {outp.name} ({outp.data_type})")
            
        if len(comp.inputs) == 0 and len(comp.outputs) == 0:
            print("  [FAIL] No parameters found!")

if __name__ == "__main__":
    test_wasp_parsing()
