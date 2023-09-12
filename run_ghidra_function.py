from pathlib import Path
import re

import matplotlib.pyplot as plt


import subprocess
import shutil
from alive_progress import alive_it
import json

import sys
#sys.path.append('/home/rest/binary_analysis/ripkit')
from ripkit.cargo_picky import (
  is_executable,
)

#
#
#from ripbin import (
#    get_registry, AnalysisType, ProgLang,
#    generate_minimal_unlabeled_features,
#    POLARS_generate_minimal_unlabeled_features,
#    )

def run_ghidra(bin_path: Path, 
               post_script: Path,
               script_path: Path = Path("~/ghidra_scripts/").expanduser(),
               analyzer: Path = Path("~/ghidra_10.3.3_PUBLIC/support/analyzeHeadless").expanduser().resolve(),):
    '''
    Run the analyze headless mode with ghidra
    '''
    
    cmd_str = [f"{analyzer.parent}/./{analyzer.name}", "/tmp", "tmp_proj",
               "-import", f"{bin_path}", "-scriptPath", f"{script_path}",
               "-postScript", f"{post_script.name}",
               ]
    try:
        paths_to_remove = ["tmp_proj.rep", "tmp_proj.gpr"]
        paths_to_remove = [Path("/tmp") / Path(x) for x in paths_to_remove]
        for path in paths_to_remove:
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()


        output = subprocess.run(cmd_str, text=True,
                                capture_output=True,
                                universal_newlines=True)
        return output
    except subprocess.CalledProcessError as e:
        print(f"COMMAND IS : {cmd_str}")
        print("Error running command:", e)
        return []
    finally:
        paths_to_remove = ["tmp_proj.rep", "tmp_proj.gpr"]
        paths_to_remove = [Path("/tmp") / Path(x) for x in paths_to_remove]
        for path in paths_to_remove:
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()


def parse_for_functions(inp):
    res = []
    in_list = False
    for line in inp.split("\n"):
        if "END FUNCTION LIST" in line:
            return res
        if in_list:
            # Clean the line:
            #  ('func_name', 0x555)
            res.append(line.strip().replace('(','').replace(')','').split(','))
        if "BEGIN FUNCTION LIST" in line:
            in_list = True


    return res


def function_list_comp(func_list1, func_list2):
    '''
    Helper function to get the unique functions 
    to each list, common functions
    '''


    unique_list1 = [x for x in func_list1 if x[1] not in [y[1] for y in func_list2]]
    unique_list2 = [x for x in func_list2 if x[1] not in [y[1] for y in func_list1]]

    return unique_list1, unique_list2

    
def ghidra_bench_functions(bin_path: Path, 
    post_script: Path = Path("~/ghidra_scripts/List_Function_and_Entry.py").expanduser(),
    script_path: Path = Path("~/ghidra_scripts/").expanduser(),
    analyzer: Path = 
    Path("~/ghidra_10.3.3_PUBLIC/support/analyzeHeadless").expanduser().resolve()
                           ):

    # Run ghidra on unstripped binary and get function list
    print(f"Running on binary {bin_path}")
    nonstrip_res = run_ghidra(bin_path , post_script, script_path, analyzer)
    nonstrip_funcs = parse_for_functions(nonstrip_res.stdout)


    # Copy the bin and strip it 
    strip_bin = bin_path.parent / Path(bin_path.name + "_STRIPPED")
    shutil.copy(bin_path, Path(strip_bin))

    try:
        output = subprocess.check_output(['strip',f'{strip_bin.resolve()}'])
    except subprocess.CalledProcessError as e:
        print("Error running command:", e)
        return []

    print(f"Running on {bin_path.name} stripped")
    # Run ghidra on stripped bin and get function list
    strip_res = run_ghidra(strip_bin , post_script, script_path, analyzer)
    strip_funcs = parse_for_functions(strip_res.stdout)

    # Delete the stripped binary
    strip_bin.unlink()

    # Get the number of unique functions to each
    unique_nonstrip, unique_strip = function_list_comp(nonstrip_funcs, 
                                                       strip_funcs)

    # Return a list of functions for each, and unqiue functions for each
    return [(nonstrip_funcs, unique_nonstrip), (strip_funcs, unique_strip)]


def open_and_read_log(log_path: Path = Path("GHIDRA_BENCH_RESULTS.json")):

    # Read json data 
    with open(log_path,'r') as f:
        data = json.load(f)

    # Totals 
    total_strip_unique = 0
    total_non_strip_unique = 0
    total_funcs = 0
    total_strip_non_unique  = 0
    for _, bin_data in data.items():
        # Unqiue functions in non-strip: Missed funcs 
        #                           -or- False Negative
        # Unqiue funciotns in strip: False Positive

        # Non-unique functions in strip: True Positive

        total_strip_unique += bin_data['strip_unique_funcs']
        total_non_strip_unique += bin_data['nonstrip_unique_funcs']
        total_strip_non_unique += bin_data['strip_funcs']
        total_funcs += bin_data['nonstrip_funcs']

    false_negative = total_non_strip_unique
    false_positive = total_strip_unique

    # Every thing that correctly labeled
    true_positive = total_strip_non_unique


    # Recall 
    recall = true_positive / (true_positive + false_negative)

    # Precision 
    precision = true_positive / (true_positive + false_positive)

    # F1
    f1 = 2 * precision * recall / (precision+recall)


    print("Stats:")
    print("==================")
    print(f"Number of functions: {total_funcs}")
    print(f"Funcs correctly identified: {true_positive}")
    print(f"False neg: {false_negative}")
    print(f"False pos: {false_positive}")
    print(f"strip unique: {total_strip_unique}")
    print(f"nonstrip unique: {total_non_strip_unique}")
    print(f"Number of files: {len(data.keys())}")
    print(f"Precision {precision}")
    print(f"Recall: {recall}")
    print(f"F1: {f1}")


    plt = create_dual_plots(1, recall, f1, true_positive, total_funcs,
                            ['Precision', 'Recall', 'F1'],
                            ['Found','Not Found'])

    plt.savefig("dual_plot")
    return 

def create_dual_plots(bar_value1, bar_value2, bar_value3, pie_found, pie_total, labels_bar, labels_pie):
    # Create a figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Bar chart
    values = [bar_value1, bar_value2, bar_value3]
    #labels = ['Value 1', 'Value 2', 'Value 3']
    labels = labels_bar
    ax1.bar(labels, values)
    ax1.set_xlabel('Metrics')
    ax1.set_ylabel('Score')
    ax1.set_title('Bar Chart')

    # Pie chart
    sizes = [pie_found, pie_total - pie_found]
    labels = labels_pie
    ax2.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
    ax2.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    ax2.set_title('Pie Chart')

    # Display the plots
    plt.tight_layout()
    return plt







if __name__ == "__main__":
    #open_and_read_log()
    #exit(1)

    rust_bins = []
    for parent in Path("/home/ryan/.ripbin/ripped_bins/").iterdir():
        info_file = parent / 'info.json'
        info = {}
        try:
            with open(info_file, 'r') as f:
                info = json.load(f)
        except FileNotFoundError:
            print(f"File not found: {info_file}")
            continue
        except json.JSONDecodeError as e:
            print(f"JSON decoding error: {e}")
            continue
        except Exception as e:
            print(f"An error occurred: {e}")
            continue

        if info['optimization'] == '3':
            npz_file = parent / "onehot_plus_func_labels.npz"
            bin = [x for x in parent.iterdir() 
                if ".npz" not in x.name and ".json" not in x.name][0]
            rust_bins.append(bin)

    # All binaries are in there pkg dir and are exe
    #rust_bins = [x for x in Path("/home/ryan/.ripbin/ripped_bins/").rglob('*') if (x.name!="info.json" and "npz" not in x.name and x.is_file())]

    # Only run on the last 30 files
    rust_bins = rust_bins[31:]

    total_results = []
    LOG_FILE = Path("GHIDRA_BENCH_RESULTS.json")
    LOG_FILE.touch()

    for bin_path in alive_it(rust_bins):
        if not bin_path.exists():
            continue

        print(f"Running ghidra on binary {bin_path.name}")
        res =  ghidra_bench_functions(bin_path)
        total_results.append(res)

        print(f"Results: {bin_path}")
        print("=========")
        print(f"Nonstrip | Functions: {len(res[0][0])} Unique {len(res[0][1])}")
        print(f"Strip | Functions: {len(res[1][0])} Unique {len(res[1][1])}")
        data = {
            'name': bin_path.name,
            'nonstrip_funcs': len(res[0][0]),
            'nonstrip_unique_funcs': len(res[0][1]),
            'strip_funcs': len(res[1][0]),
            'strip_unique_funcs': len(res[1][1]),
        }
        for k, v in data.items():
            print(f"{k} = {v}")

        try:
            with open(LOG_FILE,'r') as f:
                cur_data = json.load(f)
                cur_data[bin_path.name] = data
        except json.decoder.JSONDecodeError:
            cur_data = {}
            pass

        with open(LOG_FILE,'w') as f:
            json.dump(cur_data,f)

            #f.write(f"{bin_path}: \n")


