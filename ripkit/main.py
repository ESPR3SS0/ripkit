import typer
import math
import json
import pandas as pd
from typing_extensions import Annotated
from alive_progress import alive_bar, alive_it
from pathlib import Path


app = typer.Typer()

from ripkit.cargo_picky import (
    gen_cargo_build_cmd,
    get_target_productions,
    is_executable,
    init_crates_io,
    crates_io_df,
    clone_crate,
    is_remote_crate_exe,
    LocalCratesIO,
    build_crate,
    RustcStripFlags,
    RustcOptimization,
    RustcTarget
)

from ripkit.ripbin import (
    get_functions,
    save_analysis,
    calculate_md5,
    RustFileBundle,
    generate_minimal_labeled_features,
    DB_PATH,
    AnalysisType,
    FileType,
    Compiler,
    ProgLang,
    RustcOptimization,
)


def build_analyze_crate(crate, opt, target, filetype,
                        strip = RustcStripFlags.NOSTRIP,
                        use_cargo=True):
    '''
    Helper function to build then analyze the crate
    '''


    # Build the crate 
    build_crate(crate, opt, target, strip,
                        use_cargo=use_cargo)

    # Need this to get the build command 
    crate_path = Path(LocalCratesIO.CRATES_DIR.value).resolve().joinpath(crate)

    # Need the build command for the bundle info 
    build_cmd = gen_cargo_build_cmd(crate_path, target, strip, opt)


    # Get files of interest from the crate at the target <target>
    files_of_interest = [x for x in get_target_productions(crate, target) 
                            if is_executable(x)]

    if files_of_interest == []:
        print(f"Crate {crate} had no build executable productions")
        # TODO: in the crates_io cache which cloned pkgs don't build any 
        #       files of interest so they are not rebuilt
        return 99

    # The only file in the list should be the binary
    binary = files_of_interest[0]

    # Create the file info
    binHash = calculate_md5(binary)

    # Create the file info
    info = RustFileBundle(binary.name,
                          binHash,
                          target.value,
                          filetype,
                          opt.value,
                          binary.name,
                          "",
                          build_cmd)


    # Generate analysis
    data = generate_minimal_labeled_features(binary)

    # TODO: Anlysis not being saved with target or ELF vs PE?

    try:
        # Save analyiss
        save_analysis(binary,
                        data,
                        AnalysisType.ONEHOT_PLUS_FUNC_LABELS,
                        info,
                        overwrite_existing=False)
    except Exception as e:
        print(f"Exception {e} in crate {crate}")

    return 0

@app.command()
def list_functions(
        binary: Annotated[str, typer.Argument()],
        count: Annotated[bool, typer.Option()] = False,
    ):
    '''
    Print the list of function that lief detects
    '''

    path = Path(binary)
    functions = get_functions(path)
    func_start_addrs = {x.addr : (x.name, x.size) for x in functions}

    # Fancy line to get the longest addr and round it up to 2 bytes 
    max_len = math.ceil(max(len(str(x)) for x in func_start_addrs.keys()) / 2) * 2

    for addr, info in func_start_addrs.items():
        #print(f"0x{str(int(hex(addr),16)).zfill(max_len)}: {info[0]}")
        #print(f"{str(hex(addr)).zfill(max_len)}: {info[0]}")
        print(f"{hex(addr)}: {info[0]}")
    if count:
        print(f"{len(func_start_addrs.keys())} functions")

    return
    

@app.command()
def init():
    '''
    Initialize ripkit with rust data base,
    and register files
    '''
    init_crates_io()
    return

@app.command()
def is_crate_exe(
        crate: Annotated[str, typer.Argument()]):

    print(is_remote_crate_exe(crate))
    return


@app.command()
def cargo_clone(
        crate: Annotated[str, typer.Argument()]):

    clone_crate(crate)

    return

@app.command()
def show_cratesio(
    column: 
        Annotated[str, typer.Option()] = '',
    ):
    '''
    Show the head of cratesw io dataframe
    '''

    # Get the df
    crates_df = crates_io_df()


    if column == '':
        print(crates_df.head())
    else:
        print(crates_df[column])
    print(crates_df.columns)


@app.command()
def clone_many_exe(
    number: Annotated[int,typer.Argument()],
    verbose: Annotated[bool,typer.Option()] = False):
    '''
    Clone many new executable rust crates.
    '''

    # Get the remote crate reg
    reg = crates_io_df()

    # List of crate current installed
    installed_crates = [x.name for x in Path(LocalCratesIO.CRATES_DIR.value).iterdir() if x.is_dir()
    ]

    # List of crate names
    crate_names = [x for x in reg['name'].tolist() if x not in installed_crates]
    print("Finding uninstalled registry...")

    # With progress bar, enumerate over the registry 
    cloned_count = 0
    with alive_bar(number) as bar:
        for i, crate in enumerate(crate_names):
            if i % 100 == 0:
                print(f"Searching... {i} crates so far")
            # See if the crate is exe before cloning
            if is_remote_crate_exe(crate):
                print(f"Cloning crate {crate}")
                try:
                    if verbose:
                        clone_crate(crate, debug=True)
                    else:
                        clone_crate(crate)

                    cloned_count+=1
                    bar()
                except Exception as e:
                    print(e)
                    bar(skipped=True)
                bar(skipped=True)
            # Break out of the loop if enough have cloned
            if cloned_count >= number:
                break


@app.command()
def build(
    crate: Annotated[str, typer.Argument(help="crate name")],
    opt_lvl: Annotated[str, typer.Argument(help="O0, O1, O2, O3, Oz, Os")],
    bit: Annotated[str, typer.Argument(help="32 or 64")],
    filetype: Annotated[str, typer.Argument(help="pe or elf")],
    strip: Annotated[bool, typer.Option()] = False,
    ):
    '''
    Build a crate for a specific target
    '''

    #TODO: For simpilicity I prompt for only
    # 64 vs 32 bit and pe vs elf. Really I 
    # should prompt for the whole target arch
    # b/c theres many different ways to get
    # a 64bit pe  or 32bit elf 

    if opt_lvl == "O0":
        opt = RustcOptimization.O0
    elif opt_lvl == "O1":
        opt = RustcOptimization.O1
    elif opt_lvl == "O2":
        opt = RustcOptimization.O2
    elif opt_lvl == "O3":
        opt = RustcOptimization.O3
    elif opt_lvl == "Oz":
        opt = RustcOptimization.OZ
    elif opt_lvl == "Os":
        opt = RustcOptimization.OS
    else:
        print("UNknown opt")
        return

    if bit == "64":
        if filetype == "elf":
            target = RustcTarget.X86_64_UNKNOWN_LINUX_GNU
        elif filetype == "pe":
            target = RustcTarget.X86_64_PC_WINDOWS_GNU 
        else:
            print("UNknown filetype")
            return
    elif bit == "32":
        if filetype == "elf":
            target = RustcTarget.I686_UNKNOWN_LINUX_GNU
        elif filetype == "pe":
            target = RustcTarget.I686_PC_WINDOWS_GNU 
        else:
            print("UNknown filetype")
            return
    else:
        print("UNknown bit")
        return

    if not strip:
        strip_lvl = RustcStripFlags.NOSTRIP
    else:
        # SYM_TABLE is the all the symbols
        strip_lvl = RustcStripFlags.SYM_TABLE


    if target == RustcTarget.X86_64_UNKNOWN_LINUX_GNU:
        build_crate(crate, opt, target, strip_lvl,
                    use_cargo=True, debug=True)
    else:
        build_crate(crate, opt, target, strip_lvl,debug=True)

    print(f"Crate {crate} built")
    return


@app.command()
def build_all(
    opt_lvl: Annotated[str, typer.Argument(help="O0, O1, O2, O3, Oz, Os")],
    bit: Annotated[str, typer.Argument(help="32 or 64")],
    filetype: Annotated[str, typer.Argument(help="pe or elf")],
    strip: Annotated[bool, typer.Option()] = False,
    ):
    '''
    Build all the installed crates
    '''

    #TODO: For simpilicity I prompt for only
    # 64 vs 32 bit and pe vs elf. Really I 
    # should prompt for the whole target arch
    # b/c theres many different ways to get
    # a 64bit pe  or 32bit elf 

    if opt_lvl == "O0":
        opt = RustcOptimization.O0
    elif opt_lvl == "O1":
        opt = RustcOptimization.O1
    elif opt_lvl == "O2":
        opt = RustcOptimization.O2
    elif opt_lvl == "O3":
        opt = RustcOptimization.O3
    elif opt_lvl == "Oz":
        opt = RustcOptimization.OZ
    elif opt_lvl == "Os":
        opt = RustcOptimization.OS
    else:
        return

    if bit == "64":
        if filetype == "elf":
            target = RustcTarget.X86_64_UNKNOWN_LINUX_GNU
        elif filetype == "pe":
            target = RustcTarget.X86_64_PC_WINDOWS_GNU 
        else:
            return
    elif bit == "32":
        if filetype == "elf":
            target = RustcTarget.I686_UNKNOWN_LINUX_GNU
        elif filetype == "pe":
            target = RustcTarget.I686_PC_WINDOWS_GNU 
        else:
            return
    else:
        return

    if not strip:
        strip_lvl = RustcStripFlags.NOSTRIP
    else:
        # SYM_TABLE is the all the symbols
        strip_lvl = RustcStripFlags.SYM_TABLE








    # List of crate current installed
    installed_crates = [x.name for x in Path(LocalCratesIO.CRATES_DIR.value).iterdir() if x.is_dir()
    ]

    for crate in alive_it(installed_crates):

        if target == RustcTarget.X86_64_UNKNOWN_LINUX_GNU:
            build_crate(crate, opt, target, strip_lvl,
                        use_cargo=True, debug=True)
        else:
            build_crate(crate, opt, target, strip_lvl)



@app.command()
def list_cloned():
    '''
    List the cloned crates
    '''

    # List of crate current installed
    installed_crates = [x.name for x in Path(LocalCratesIO.CRATES_DIR.value).iterdir() if x.is_dir()]

    for crate in installed_crates:
        print(crate)
    print(f"Thats {len(installed_crates)} crates")
                        


@app.command()
def analyze(bin_path: Annotated[str, typer.Argument()],
            language: Annotated[str, typer.Argument()],
            opt_lvl: Annotated[str, typer.Argument(help="O0, O1, O2, O3, Oz, Os")],
            bit: Annotated[str, typer.Argument(help="32 or 64")],
            filetype: Annotated[str, typer.Argument(help="pe or elf")],
            save: Annotated[bool, typer.Option()] = True,
            ):
    '''
    Analyze binary file 
    '''

    binary = Path(bin_path).resolve()
    if not binary.exists():
        print(f"Binary {binary} doesn't exist")
        return

    # Generate analysis
    print("Generating Tensors...")
    data = generate_minimal_labeled_features(binary)
    print("Tensors generated")


    # Create the file info
    print("Calculating bin hash...")
    binHash = calculate_md5(binary)
    print("bin hash calculated...")


    # TODO: Anlysis not being saved with target or ELF vs PE?


    # Create the file info
    info = RustFileBundle(binary.name,
                          binHash,
                          "",
                          filetype,
                          opt_lvl,
                          binary.name,
                          "",
                          "")

    print("Saving Tensor and binary")
    # Save analyiss
    save_analysis(binary,
                    data,
                    AnalysisType.ONEHOT_PLUS_FUNC_LABELS,
                    info,
                    overwrite_existing=False)
    print("Done!")


@app.command()
def stats():
    '''
    Print stats about the rippe binaries
    '''

    stats = {
        'total':0,
        'num_opt0': 0,
        'num_opt1': 0,
        'num_opt2': 0,
        'num_opt3': 0,
        'num_optz': 0,
        'num_opts': 0,
    }

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

        if '0' in info['optimization']:
            stats['num_opt0']+=1
        if '1' in info['optimization']:
            stats['num_opt1']+=1
        if '2' in info['optimization']:
            stats['num_opt2']+=1
        if '3' in info['optimization']:
            stats['num_opt3']+=1
        if 'z' in info['optimization']:
            stats['num_optz']+=1
        if 's' in info['optimization']:
            stats['num_opts']+=1

        stats['total'] +=1

    for key, value in stats.items():
        print(f"{key} = {value}")

    return

@app.command()
def build_analyze_all(
    opt_lvl: Annotated[str, typer.Argument()],
    bit: Annotated[int, typer.Argument()],
    filetype: Annotated[str, typer.Argument()],
    stop_on_fail: Annotated[bool,typer.Option()]=False,
    force_build_all: Annotated[bool,typer.Option()]=False,
    ):
    '''
    Build and analyze pkgs
    '''
    if opt_lvl == "O0":
        opt = RustcOptimization.O0
    elif opt_lvl == "O1":
        opt = RustcOptimization.O1
    elif opt_lvl == "O2":
        opt = RustcOptimization.O2
    elif opt_lvl == "O3":
        opt = RustcOptimization.O3
    elif opt_lvl == "Oz":
        opt = RustcOptimization.OZ
    elif opt_lvl == "Os":
        opt = RustcOptimization.OS
    else:
        print("Invalid opt lvl")
        return

    if bit == 64:
        if filetype == "elf":
            target = RustcTarget.X86_64_UNKNOWN_LINUX_GNU
        elif filetype == "pe":
            target = RustcTarget.X86_64_PC_WINDOWS_GNU 
        else:
            print("Invlaid filetype")
            return
    elif bit == 32:
        if filetype == "elf":
            target = RustcTarget.I686_UNKNOWN_LINUX_GNU
        elif filetype == "pe":
            target = RustcTarget.I686_PC_WINDOWS_GNU 
        else:
            print("Invlaid filetype")
            return
    else:
        print(f"Invlaid bit lvl {bit}")
        return

    # List of crate current installed
    installed_crates = [x.name for x in Path(LocalCratesIO.CRATES_DIR.value).iterdir() if x.is_dir()
    ]


    if not force_build_all:
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

            if info['optimization'].upper() in opt_lvl:
                # Remove this file from the installed crates list 
                if (x:=info['binary_name']) in installed_crates:
                    installed_crates.remove(x)

    # Any crates that are already built with the same target don't rebuild or analyze

    # Need to get all the analysis for the given optimization and target... 
    # TODO: Assuming all targets are 64bit elf right now 

    crates_with_no_interest = Path(f"~/.crates_io/uninteresting_crates_cache_{target.value}").expanduser()

    boring_crates = []
    # If the file doesn't exist throw in the empty list
    if not crates_with_no_interest.exists():
        crates_with_no_interest.touch()
        with open(crates_with_no_interest, 'w') as f:
            json.dump({'names' : boring_crates},f)

    if not force_build_all:
        # If the file does exist read it, ex
        with open(crates_with_no_interest, 'r') as f:
            boring_crates.extend(json.load(f)['names'])

    for x in boring_crates:
        installed_crates.remove(x)


    # Build and analyze each crate
    for crate in alive_it(installed_crates):
        #TODO: the following conditional is here because when building for 
        #       x86_64 linux I know that cargo will work, and I know 
        #       cargo's toolchain version 
        res = 0
        if target == RustcTarget.X86_64_UNKNOWN_LINUX_GNU:
            res = build_analyze_crate(crate, opt, target, filetype,
                            RustcStripFlags.NOSTRIP,
                            use_cargo=True)
        else:
            res = build_analyze_crate(crate, opt, target, filetype,
                            RustcStripFlags.NOSTRIP)
        if res == 99:
            boring_crates.append(crate)
            print(f"Adding crate {crate} to boring crates")
            with open(crates_with_no_interest, 'w') as f:
                json.dump({'names' : boring_crates}, f)


    # Build the crate, add the binary to a list of binaries
    #bins = []
    #crates_with_no_files_of_interest = []
    #for crate in alive_it(installed_crates):

    #    if target == RustcTarget.X86_64_UNKNOWN_LINUX_GNU:
    #        build_crate(crate, opt, target, RustcStripFlags.NOSTRIP,
    #                    use_cargo=True, debug=True)
    #    else:
    #        build_crate(crate, opt, target, RustcStripFlags.NOSTRIP)

    #    # Get files of interest from the crate at the target <target>
    #    files_of_interest = [x for x in get_target_productions(crate, target) if is_executable(x)]

    #    if files_of_interest != []:
    #        bins.append(files_of_interest[0])
    #    else:
    #        print(f"Crate {crate} had no build executable productions")
    #        crates_with_no_files_of_interest.append(crate)
    #    # TODO: in the crates_io cache which cloned pkgs don't build any 
    #    #       files of interest so they are not rebuilt


    #boring_crates = []
    #if crates_with_no_interest.exists():
    #    with open(crates_with_no_interest, 'r') as f:
    #        boring_crates.extend(json.load(f)['names'])
    #if boring_crates != []
    #    with open(crates_with_no_interest, 'w') as f:
    #        json.dump({'names': boring_crates},f)

    #for binary in alive_it(bins):
    #    try:

    #        # TODO: Don't use an analyze function from here, 
    #        #       use a function from ripbin

    #        # Analyze the file
    #        #analyze(binary,
    #        #        'rust',
    #        #        opt.value,
    #        #        str(bit),
    #        #        str(filetype),
    #        #        )

    #        #binary = Path(bin_path).resolve()
    #        if not binary.exists():
    #            print(f"Binary {binary} doesn't exist")
    #            return

    #        # Generate analysis
    #        print("Generating Tensors...")
    #        data = generate_minimal_labeled_features(binary)
    #        print("Tensors generated")


    #        # Create the file info
    #        print("Calculating bin hash...")
    #        binHash = calculate_md5(binary)
    #        print("bin hash calculated...")


    #        # TODO: Anlysis not being saved with target or ELF vs PE?


    #        # Create the file info
    #        info = RustFileBundle(binary.name,
    #                              binHash,
    #                              "",
    #                              filetype,
    #                              opt_lvl,
    #                              binary.name,
    #                              "",
    #                              "")

    #        print("Saving Tensor and binary")
    #        # Save analyiss
    #        save_analysis(binary,
    #                        data,
    #                        AnalysisType.ONEHOT_PLUS_FUNC_LABELS,
    #                        info,
    #                        overwrite_existing=False)
    #        print("Done!")
    #    except Exception:
    #        print(f"Error for file {binary}")
    #        if stop_on_fail:
    #            return
    #        pass


if __name__ == "__main__":
    app()
