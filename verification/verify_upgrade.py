import os
import sys
import shutil
import textwrap

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.python_analyser import execute

def verify_upgrade():
    workspace_dir = os.path.abspath("test_workspace_upgrade")
    output_dir = os.path.join(workspace_dir, "output")
    
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir)
    os.makedirs(output_dir)

    print(f"--- Verification: Docker Environment Upgrade ---")
    
    # Test Case: SVG to PNG using cairosvg (requires system libraries)
    print("\n[Test] SVG to PNG with cairosvg and APT packages...")
    
    url = "https://cdn.search.brave.com/serp/v3/_app/immutable/assets/brave-logo-dark.5D16vJCY.svg"
    
    code = textwrap.dedent(f"""
        import requests
        import os
        import cairosvg
        
        url = "{url}"
        svg_path = "/workspace/brave-logo.svg"
        png_path = "/workspace/output/brave-logo.png"
        
        try:
            print("Downloading SVG...")
            response = requests.get(url)
            response.raise_for_status()
            with open(svg_path, 'wb') as f:
                f.write(response.content)
            
            print("Converting SVG to PNG...")
            cairosvg.svg2png(url=svg_path, write_to=png_path)
            print(f"Success! PNG created at {{png_path}}")
        except Exception as e:
            print(f"Error: {{e}}")
    """)
    
    params = {
        "code": code,
        "packages": ["requests", "cairosvg"],
        "system_packages": ["libcairo2", "libpango-1.0-0", "libpangocairo-1.0-0"],
        "_workspace": workspace_dir
    }
    
    result = execute(params)
    print(result)
    
    # Check if output file exists
    output_file = os.path.join(output_dir, "brave-logo.png")
    if os.path.exists(output_file):
        print(f"Verification Successful: Output file found at {output_file}")
        print(f"File Size: {os.path.getsize(output_file)} bytes")
    else:
        print("Verification Failed: Output file not found!")

if __name__ == "__main__":
    verify_upgrade()
