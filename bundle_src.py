import os

def bundle_files(root_dir, output_prefix):
    all_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            file_path = os.path.join(root, file)
            all_files.append(file_path)
    
    all_files.sort()
    
    total_files = len(all_files)
    num_parts = 20
    files_per_part = (total_files + num_parts - 1) // num_parts
    
    for i in range(num_parts):
        start_idx = i * files_per_part
        end_idx = min((i + 1) * files_per_part, total_files)
        files_subset = all_files[start_idx:end_idx]
        output_file = f"{output_prefix}_part{i+1}.txt"
        
        if not files_subset:
            continue

        with open(output_file, 'w', encoding='utf-8') as outfile:
            for file_path in files_subset:
                rel_path = os.path.relpath(file_path, start=os.getcwd())
                
                # Header for each file
                outfile.write(f"\n{'='*80}\n")
                outfile.write(f"FILE: {rel_path}\n")
                outfile.write(f"{'='*80}\n\n")
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        outfile.write(infile.read())
                except Exception as e:
                    outfile.write(f"Error reading file {file_path}: {e}\n")
                
                outfile.write("\n")
        print(f"Created {output_file} with {len(files_subset)} files.")

if __name__ == "__main__":
    src_dir = "admin_ui/src"
    output_prefix = "old_admin_ui_src_bundle"
    print(f"Bundling {src_dir}...")
    bundle_files(src_dir, output_prefix)
    print("Done!")
